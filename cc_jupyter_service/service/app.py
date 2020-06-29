import os
import sys

import requests
from flask import Flask, render_template, request, jsonify, g, Response
from requests import HTTPError
from werkzeug.exceptions import BadRequest, NotFound, Unauthorized
import jsonschema
import nbformat
from werkzeug.security import check_password_hash
from werkzeug.urls import url_join

from cc_jupyter_service.common.helper import normalize_url, AUTHORIZATION_COOKIE_KEY, AgencyError
from cc_jupyter_service.service.db import DatabaseAPI
import cc_jupyter_service.service.auth as auth
import cc_jupyter_service.service.db as database_module
from cc_jupyter_service.common.execution import exec_notebook, cancel_batch
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
        SESSION_COOKIE_NAME=conf.flask_session_cookie,
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

    def create_gpu_requirements(request_requirements):
        """
        Transforms a list of integers interpreted as gpu vram requirements into a red compatible object for gpu
        requirements. The vram is given in megabytes.

        :param request_requirements: A list of minimum vram dependencies
        :type request_requirements: list[integer]
        :return: An object with the keys 'vendor' and 'devices'. The value of the vendor key is always 'nvidia' and
                 'devices' is a list of objects with the key 'vramMin'. If no gpus are required None is returned.
        :rtype: object or None
        """
        if not request_requirements:
            return None

        devices = list(map(lambda req: {'vramMin': req}, request_requirements))
        return {
            'vendor': 'nvidia',
            'devices': devices
        }

    def dependencies_to_docker_image(dependencies):
        """
        Chooses a docker image from the given dependencies.

        :param dependencies:
        :return: The docker image tag

        :raise ValueError: If the given predefined image could not be found
        """
        if dependencies['custom']:
            return dependencies['customImage']

        image_name = dependencies['predefinedImage']
        for predefined_docker_image in conf.predefined_docker_images:
            if predefined_docker_image.name == image_name:
                return predefined_docker_image.tag
        raise ValueError('Could not find docker image with name "{}"'.format(image_name))

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
        agency_authorization_cookie = database_api.get_newest_cookie(user.user_id)

        if agency_authorization_cookie is None:
            raise Unauthorized('Could not find an authorization cookie')

        try:
            docker_image = dependencies_to_docker_image(request_data['dependencies'])
        except ValueError as e:
            raise BadRequest(str(e))

        gpu_requirements = create_gpu_requirements(request_data['gpuRequirements'])

        external_data = request_data['externalData']

        for jupyter_notebook in request_data['jupyterNotebooks']:
            try:
                experiment_id = exec_notebook(
                    jupyter_notebook['data'],
                    agency_url=user.agency_url,
                    agency_username=user.agency_username,
                    agency_authorization_cookie=agency_authorization_cookie.cookie_text,
                    notebook_database=notebook_database,
                    url_root=request.url_root,
                    docker_image=docker_image,
                    gpu_requirements=gpu_requirements,
                    notebook_filename=jupyter_notebook['filename'],
                    external_data=external_data,
                    python_requirements=request_data['pythonRequirements']
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
            response.headers["Content-Disposition"] = "attachment; filename={}Result.ipynb".format(
                notebook.get_filename_without_ext()
            )
            response.headers["Content-Length"] = os.path.getsize(
                notebook_database.notebook_id_to_path(notebook_id, is_result=True)
            )
            return response
        else:
            raise NotFound()

    @app.route('/python_requirements/<notebook_id>', methods=['GET'])
    def get_python_requirements(notebook_id):
        """
        Returns the python requirements for the requested notebook

        :param notebook_id: The id of the notebook
        :type notebook_id: str

        :raise NotFound: If the notebook id could not be found, or if there aren't python requirements for this notebook
        """
        validate_notebook_id(notebook_id)

        database_api = DatabaseAPI.create()
        notebook = database_api.get_notebook(notebook_id)

        if notebook.python_requirements is None:
            raise NotFound('Notebook has no python requirements')

        return notebook.python_requirements

    @app.route('/list_results')
    @auth.login_required
    def list_results():
        """
        Endpoint that produces a json list, that lists all experiments for the current user.
        Every entry has a Notebook id and a process status

        :return: A json list, describing the experiments
        """
        database_api = DatabaseAPI.create()

        try:
            _update_notebook_status(g.user)
        except HTTPError as e:
            err_str = 'Failed to update notebook status: {}'.format(str(e))
            print(err_str, file=sys.stderr)
            raise BadRequest(err_str)

        entries = []
        for notebook in database_api.get_notebooks(g.user.user_id):
            entries.append({
                'notebook_id': notebook.notebook_id,
                'process_status': str(notebook.status),
                'notebook_filename': notebook.notebook_filename,
                'execution_time': notebook.execution_time,
                'debug_info': notebook.debug_info
            })
        entries = sorted(entries, key=lambda entry: entry['execution_time'], reverse=True)
        return jsonify(entries)

    @app.route('/predefined_docker_images', methods=['GET'])
    @auth.login_required
    def get_predefined_docker_images():
        """
        Lists the predefined docker images of this server
        """
        result = list(map(lambda pdi: pdi.to_json(), conf.predefined_docker_images))
        return jsonify(result)

    @app.route('/cancel_notebook', methods=['DELETE'])
    @auth.login_required
    def cancel_notebook():
        """
        Cancels the execution of the given notebook.
        """
        if not request.json:
            raise BadRequest('Request should define notebook id in json data')

        data = request.json
        if (not isinstance(data, dict)) or ('notebookId' not in data):
            raise BadRequest('Request should define notebook id in json data')
        notebook_id = data['notebookId']

        user = g.user

        database_api = DatabaseAPI.create()
        notebook = database_api.get_notebook(notebook_id)
        if notebook.user_id != user.user_id:
            raise Unauthorized('You cannot cancel notebooks of different users')

        cookie = database_api.get_newest_cookie(user.user_id)
        if cookie is None:
            raise Unauthorized('No authorization cookie could be found')

        try:
            batch_id = cancel_batch(notebook.experiment_id, user.agency_url, cookie.cookie_text)
        except (ValueError, AgencyError) as e:
            raise BadRequest('Failed to cancel notebook: {}'.format(str(e)))

        return jsonify({'batchId': batch_id})

    database_module.init_app(app)

    return app


def _get_debug_info_for_batch(batch_id, agency_url, cookie):
    """
    Returns the debug information of the given batch.
    First tries to fetch the stderr of the failed process. If this is not successful, tries to fetch the logs from the
    agency.

    :type batch_id: str
    :type agency_url: str
    :type cookie: DatabaseAPI.Cookie
    :rtype: str
    """
    # try stderr
    r = requests.get(
        url_join(agency_url, 'batches/{}/stderr'.format(batch_id)),
        cookies={AUTHORIZATION_COOKIE_KEY: cookie.cookie_text}
    )

    if 200 <= r.status_code < 300 and r.text.strip():
        return r.text

    # if no stderr could be found, look in agency logs
    r = requests.get(
        url_join(agency_url, 'batches/{}'.format(batch_id)),
        cookies={AUTHORIZATION_COOKIE_KEY: cookie.cookie_text}
    )
    r.raise_for_status()
    batch_info = r.json()
    for history_entry in batch_info['history']:
        ccagent_info = history_entry.get('ccagent')
        if ccagent_info:
            debug_info = ccagent_info.get('debugInfo')
            if debug_info:
                return '\n'.join(debug_info)

    for history_entry in batch_info['history']:
        debug_info = history_entry.get('debugInfo')
        if debug_info:
            return debug_info

    raise ValueError('Could not get debug info for batch')


def _update_notebook_status(user):
    """
    Updates the database status for every notebook of the given user. Therefor a request to the agency is made.

    :param user: The user to fetch the notebook status for
    :type user: DatabaseAPI.User

    :raise ValueError: If no authorization cookie could be found
    :raise HTTPError: If the agency could not be contacted
    """
    database_api = DatabaseAPI.create()
    cookie = database_api.get_newest_cookie(user.user_id)
    if cookie is None:
        raise ValueError('No authorization cookie could be found')

    agency_url = normalize_url(user.agency_url)

    notebooks = database_api.get_notebooks(user_id=user.user_id, status=DatabaseAPI.NotebookStatus.PROCESSING)

    for notebook in notebooks:
        r = requests.get(
            url_join(agency_url, 'batches'),
            cookies={AUTHORIZATION_COOKIE_KEY: cookie.cookie_text},
            params={'experimentId': notebook.experiment_id}
        )
        r.raise_for_status()
        batch = r.json()
        if len(batch) != 1:
            raise ValueError('Expected one batch got {} batches'.format(len(batch)))
        batch = batch[0]
        batch_state = batch['state']
        if batch_state in ('succeeded', 'failed', 'cancelled'):
            notebook_state = DatabaseAPI.NotebookStatus.from_experiment_state(batch_state)
            database_api.update_notebook_status(notebook.notebook_id, notebook_state)

            # fetch debug info
            if batch_state == 'failed':
                try:
                    debug_info = _get_debug_info_for_batch(batch['_id'], agency_url, cookie)
                except ValueError as e:
                    debug_info = str(e)
                database_api.update_notebook_debug_info(notebook.notebook_id, debug_info)


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
