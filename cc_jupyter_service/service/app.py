import os
from flask import Flask, render_template, request, jsonify
from requests import HTTPError
from werkzeug.exceptions import BadRequest, Unauthorized
from werkzeug.security import check_password_hash
import jsonschema
import nbformat

from cc_jupyter_service.service.db import DatabaseAPI
import cc_jupyter_service.service.db as database_module
from cc_jupyter_service.common.execution import exec_notebook
from cc_jupyter_service.common.notebook_database import NotebookDatabase
from cc_jupyter_service.common.schema.request import request_schema
from cc_jupyter_service.common.conf import Conf

DESCRIPTION = 'CC-Jupyter-Service.'


conf = Conf.from_system()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=conf.flask_secret_key,
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite')
    )

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    notebook_database = NotebookDatabase(conf.notebook_directory)

    def validate_request(request_data):
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
    def get_root():
        return render_template('index.html')

    @app.route('/executeNotebook', methods=['POST'])
    def execute_notebook():
        """
        This endpoint is used by the frontend to start the execution of a jupyter notebook.
        """
        if not request.json:
            raise BadRequest('Did not send data as json')

        request_data = request.json
        validate_request(request_data)

        if conf.prevent_localhost and ('localhost' in request.url_root or '127.0.0.1' in request.url_root):
            raise BadRequest(
                'Cant retrieve public endpoint of this jupyter service. '
                'Make sure this jupyter service runs not on localhost'
            )

        experiment_ids = []

        for jupyter_notebook in request_data['jupyterNotebooks']:
            try:
                experiment_id = exec_notebook(
                    jupyter_notebook['data'],
                    agency_url=request_data['agencyUrl'],
                    agency_username=request_data['agencyUsername'],
                    agency_password=request_data['agencyPassword'],
                    notebook_database=notebook_database,
                    url_root=request.url_root
                )
            except HTTPError as e:
                raise BadRequest('Could not execute {}. {}'.format(jupyter_notebook['filename'], str(e)))
            experiment_ids.append(experiment_id)

        return jsonify({'experimentIds': experiment_ids})

    def _validate_user(notebook_id, database_api):
        """
        Validates the current request for the given notebook_id. Does the following checks.

        1. Checks if the given notebook_id can be found in the database.
             If not raises BadRequest.
        2. Checks whether the notebook_token in the db matches the request authorization password.
            If not raises Unauthorized.
        3. Checks whether the agency_username in the db matches the request authorization username.
            If not raises Unauthorized.

        :param notebook_id: The notebook id to check the request for
        :type notebook_id: str
        :param database_api: The database api to use
        :type database_api: DatabaseAPI

        :raise BadRequest: If the notebook could not be found
        :raise Unauthorized: If the username does not match OR the password does not match the notebook_token
        """
        try:
            notebook_token, agency_username, agency_url = database_api.get_notebook(notebook_id)
        except database_module.DatabaseError as e:
            raise BadRequest(str(e))

        if agency_username != request.authorization['username']:
            raise Unauthorized('The request username does not match the agency username')
        if not check_password_hash(notebook_token, request.authorization['password']):
            raise Unauthorized('The request password does not match the notebook token')

    @app.route('/notebook/<notebook_id>', methods=['GET'])
    def notebook(notebook_id):
        """
        Returns the requested notebook.

        :param notebook_id: The id of the notebook
        :type notebook_id: str
        """
        database_api = DatabaseAPI.create()
        _validate_user(notebook_id, database_api)
        notebook_data = notebook_database.get_notebook(notebook_id)

        return jsonify(notebook_data)

    @app.route('/result/<notebook_id>', methods=['POST'])
    def post_result(notebook_id):
        """
        Endpoint to post the result of the execution

        :param notebook_id: The id of the executed notebook
        :type notebook_id: str
        """
        database_api = DatabaseAPI.create()
        _validate_user(notebook_id, database_api)
        notebook_database.save_notebook(request.json, notebook_id, is_result=True)

        return 'notebook submitted'

    database_module.init_app(app)

    return app
