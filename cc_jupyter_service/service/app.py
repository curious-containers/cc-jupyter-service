import os

import requests
from flask import Flask, render_template, request, jsonify, g, Response
from requests import HTTPError
from werkzeug.exceptions import BadRequest, NotFound, Unauthorized
import jsonschema
import nbformat
from werkzeug.security import check_password_hash
from werkzeug.urls import url_join

from cc_jupyter_service.common.helper import normalize_url, AUTHORIZATION_COOKIE_KEY
from cc_jupyter_service.service.db import DatabaseAPI
import cc_jupyter_service.service.auth as auth
import cc_jupyter_service.service.db as database_module
from cc_jupyter_service.common.execution import exec_notebook
from cc_jupyter_service.common.notebook_database import NotebookDatabase
from cc_jupyter_service.common.schema.request import request_schema
from cc_jupyter_service.common.conf import Conf

DESCRIPTION = 'CC-Jupyter-Service.'
UPDATE_NOTEBOOK_BATCH_LIMIT = 1000


conf = Conf.from_system()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=conf.flask_secret_key,
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite')
    )

    app.register_blueprint(auth.bp)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    notebook_database = NotebookDatabase(conf.notebook_directory)

    def validate_execution_data(request_data):
        """
        This function validates the given request data.

        :param request_data: The request data to validate

        :raise BadRequest: If the request data is invalid
        """
        try:
            jsonschema.validate(request_data, request_schema)
        except jsonschema.ValidationError as e:
            raise BadRequest('Failed to validate request data. {}'.format(str(e)))

        for jupyter_notebook in request_data['jupyterNotebooks']:
            try:
                nbformat.validate(jupyter_notebook['data'])
            except nbformat.ValidationError as e:
                raise BadRequest('Failed to validate notebook "{}.\n{}"'.format(jupyter_notebook['filename'], str(e)))

    @app.route('/', methods=['GET'])
    @auth.login_required
    def root():
        return render_template('index.html')

    @app.route('/executeNotebook', methods=['POST'])
    @auth.login_required
    def execute_notebook():
        """
        This endpoint is used by the frontend to start the execution of a jupyter notebook.
        """
        if not request.json:
            raise BadRequest('Did not send data as json')

        request_data = request.json
        validate_execution_data(request_data)

        if conf.prevent_localhost and ('localhost' in request.url_root or '127.0.0.1' in request.url_root):
            raise BadRequest(
                'Cant retrieve public endpoint of this jupyter service. '
                'Make sure this jupyter service runs not on localhost'
            )

        experiment_ids = []

        user = g.user

        database_api = DatabaseAPI.create()
        agency_authorization_cookie = database_api.get_cookies(user.user_id)[0]  # TODO: choose cookie

        for jupyter_notebook in request_data['jupyterNotebooks']:
            try:
                experiment_id = exec_notebook(
                    jupyter_notebook['data'],
                    agency_url=user.agency_url,
                    agency_username=user.agency_username,
                    agency_authorization_cookie=agency_authorization_cookie.cookie_text,
                    notebook_database=notebook_database,
                    url_root=request.url_root,
                    dependencies=request_data['dependencies']
                )
            except HTTPError as e:
                raise BadRequest('Could not execute {}. {}'.format(jupyter_notebook['filename'], str(e)))
            experiment_ids.append(experiment_id)

        return jsonify({'experimentIds': experiment_ids})

    @app.route('/notebook/<notebook_id>', methods=['GET'])
    def get_notebook(notebook_id):
        """
        Returns the requested notebook.

        :param notebook_id: The id of the notebook
        :type notebook_id: str
        """
        validate_notebook_id(notebook_id)
        notebook_data = notebook_database.get_notebook(notebook_id)

        return jsonify(notebook_data)

    @app.route('/result/<notebook_id>', methods=['POST'])
    def post_result(notebook_id):
        """
        Endpoint to post the result of the execution

        :param notebook_id: The id of the executed notebook
        :type notebook_id: str
        """
        validate_notebook_id(notebook_id)
        notebook_database.save_notebook(request.json, notebook_id, is_result=True)
        database_api = DatabaseAPI.create()
        database_api.update_notebook_status(notebook_id, DatabaseAPI.NotebookStatus.SUCCESS)

        return 'notebook submitted'

    @app.route('/result/<notebook_id>', methods=['GET'])
    @auth.login_required
    def get_result(notebook_id):
        """
        Gets the result of the given notebook id.
        """
        if notebook_database.check_notebook(notebook_id, True):

            # check right user
            database_api = DatabaseAPI.create()
            notebook = database_api.get_notebook(notebook_id)
            if notebook.user_id != g.user.user_id:
                raise Unauthorized('Only the owner of a notebook can request the results')

            def generate():
                with notebook_database.open_notebook_file(notebook_id, is_result=True) as notebook_file:
                    while True:
                        block = notebook_file.read(1024*1024)
                        if not block:
                            break
                        yield block
            response = Response(generate(), mimetype='application/json')
            response.headers["Content-Disposition"] = "attachment; filename=result.ipynb"
            response.headers["Content-Length"] = os.path.getsize(
                notebook_database.notebook_id_to_path(notebook_id, is_result=True)
            )
            return response
        else:
            raise NotFound()

    @app.route('/list_results')
    @auth.login_required
    def list_results():
        """
        Endpoint that produces a json list, that lists all experiments for the current user.
        Every entry has a Notebook id and a process status

        :return: A json list, describing the experiments
        """
        database_api = DatabaseAPI.create()

        _update_notebook_status(g.user)

        entries = []
        for notebook in database_api.get_notebooks(g.user.user_id):
            entries.append({
                'notebook_id': notebook.notebook_id,
                'process_status': str(notebook.status)
            })
        return jsonify(entries)

    database_module.init_app(app)

    return app


def _update_notebook_status(user):
    """
    Updates the database status for every notebook of the given user. Therefor a request to the agency is made.

    :param user: The user to fetch the notebook status for
    :type user: DatabaseAPI.User
    """
    database_api = DatabaseAPI.create()
    cookies = database_api.get_cookies(user.user_id)
    if len(cookies) == 0:
        return
    authorization_cookie = cookies[0].cookie_text  # TODO: choose cookie
    agency_url = normalize_url(user.agency_url)

    r = requests.get(
        url_join(agency_url, 'batches'),
        cookies={AUTHORIZATION_COOKIE_KEY: authorization_cookie},
        params={'limit': UPDATE_NOTEBOOK_BATCH_LIMIT, 'username': user.agency_username}
    )
    r.raise_for_status()

    batches = r.json()
    notebooks = database_api.get_notebooks(user_id=user.user_id, status=DatabaseAPI.NotebookStatus.PROCESSING)

    experiment_states = {}
    for batch in batches:
        experiment_states[batch['experimentId']] = batch['state']

    for notebook in notebooks:
        experiment_state = experiment_states[notebook.experiment_id]
        if experiment_state in ('succeeded', 'failed', 'cancelled'):
            notebook_state = DatabaseAPI.NotebookStatus.from_experiment_state(experiment_state)
            database_api.update_notebook_status(notebook.notebook_id, notebook_state)


def validate_notebook_id(notebook_id):
    """
    Validates the current request for the given notebook_id. Does the following checks.

    1. Checks if the given notebook_id can be found in the database.
         If not raises NotFound.
    2. Checks whether the agency_username in the db matches the request authorization username.
        If not raises Unauthorized.
    3. Checks whether the notebook_token in the db matches the request authorization password.
        If not raises Unauthorized.

    :param notebook_id: The notebook id to check the request for
    :type notebook_id: str

    :raise NotFound: If the notebook could not be found
    :raise Unauthorized: If the username does not match OR the password does not match the notebook_token
    """
    database_api = DatabaseAPI.create()
    try:
        notebook = database_api.get_notebook(notebook_id)
        user = database_api.get_user(notebook.user_id)
    except database_module.DatabaseError as e:
        raise NotFound(str(e))

    if user.agency_username != request.authorization['username']:
        raise Unauthorized('The request username does not match the agency username')
    if not check_password_hash(notebook.notebook_token, request.authorization['password']):
        raise Unauthorized('The request password does not match the notebook token')
