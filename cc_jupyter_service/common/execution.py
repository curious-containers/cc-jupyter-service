import copy
import uuid

import requests
from flask import g
from werkzeug.urls import url_join

from cc_jupyter_service.common import red_file_template
from cc_jupyter_service.common.helper import normalize_url, AUTHORIZATION_COOKIE_KEY
from cc_jupyter_service.service.db import DatabaseAPI


DEFAULT_DOCKER_IMAGE = 'bruno1996/cc_jupyterservice_base_image'


def exec_notebook(
        notebook_data, agency_url, agency_username, agency_authorization_cookie, notebook_database, url_root,
        docker_image, gpu_requirements
):
    """
    - Validates the agency authentication information
    - Generates a new id and token for the notebook
    - Saves the notebook
    - Saves meta information in the db
    - Executes the notebook on the agency

    :param notebook_data: The notebook data given as dictionary to execute.
    :param agency_url: The agency to use for execution
    :type agency_url: str
    :param agency_username: The agency username to use
    :type agency_username: str
    :param agency_authorization_cookie: The authorization cookie for the given agency user
    :type agency_authorization_cookie: str
    :param notebook_database: The notebook database to save the notebook in
    :type notebook_database: NotebookDatabase
    :param url_root: The url root of this notebook service
    :type url_root: str
    :param docker_image: The docker image to use
    :type docker_image: str
    :param gpu_requirements: The gpu requirements of the request
    :type gpu_requirements: object or None

    :return: The experiment id of the executed experiment
    :rtype: str
    """
    agency_url = normalize_url(agency_url)

    notebook_id = str(uuid.uuid4())

    notebook_token = str(uuid.uuid4())
    notebook_database.save_notebook(notebook_data, notebook_id)

    experiment_id = start_agency(
        notebook_id, notebook_token, agency_url, agency_username, agency_authorization_cookie, url_root, docker_image,
        gpu_requirements
    )

    database_api = DatabaseAPI.create()
    database_api.create_notebook(notebook_id, notebook_token, g.user.user_id, experiment_id)

    return experiment_id


def _create_red_data(
        notebook_id, notebook_token, agency_url, agency_username, url_root, docker_image, gpu_requirements
):
    """
    Creates the red data that can be used for execution on an agency.

    :param notebook_id: The token to reference the notebook.
    :type notebook_id: str
    :param notebook_token: The token to authorize the notebook.
    :type notebook_token: str
    :param agency_url: The agency to use for execution
    :type agency_url: str
    :param agency_username: The agency username to use
    :type agency_username: str
    :param url_root: The url root of this notebook service
    :type url_root: str
    :param docker_image: The docker image to use
    :type docker_image: str
    :param gpu_requirements: The gpu requirements of the request
    :type gpu_requirements: object or None

    :return: The red data filled with the given information to execute on an agency
    """
    red_data = copy.deepcopy(red_file_template.RED_FILE_TEMPLATE)

    # input notebook
    input_notebook_access = red_data['inputs']['inputNotebook']['connector']['access']
    input_notebook_access['url'] = url_join(url_root, 'notebook/' + notebook_id)
    input_notebook_access['auth']['username'] = agency_username
    input_notebook_access['auth']['password'] = notebook_token

    # output notebook
    output_notebook_access = red_data['outputs']['outputNotebook']['connector']['access']
    output_notebook_access['url'] = url_join(url_root, 'result/' + notebook_id)
    output_notebook_access['auth']['username'] = agency_username
    output_notebook_access['auth']['password'] = notebook_token

    # execution engine
    execution_engine_access = red_data['execution']['settings']['access']
    execution_engine_access['url'] = agency_url
    execution_engine_access['auth']['username'] = agency_username
    execution_engine_access['auth']['password'] = ''  # We dont need this, since we do authorization by cookie

    # docker image
    container_settings = red_data['container']['settings']
    container_settings['image']['url'] = docker_image

    # gpu requirements
    if gpu_requirements is not None:
        container_settings['gpus'] = gpu_requirements

    return red_data


def start_agency(
        notebook_id, notebook_token, agency_url, agency_username, authorization_cookie, url_root, docker_image,
        gpu_requirements
):
    """
    Executes the given notebook on the given agency.

    :param notebook_id: The id to reference the notebook.
    :type notebook_id: str
    :param notebook_token: The token to authorize the notebook.
    :type notebook_token: str
    :param agency_url: The agency to use for execution
    :type agency_url: str
    :param agency_username: The agency username to use
    :type agency_username: str
    :param authorization_cookie: The authorization cookie for the given agency user
    :type authorization_cookie: str
    :param url_root: The url root of this notebook service
    :type url_root: str
    :param docker_image: The docker image to use
    :type docker_image: str
    :param gpu_requirements: The gpu requirements of the request
    :type gpu_requirements: object or None

    :return: The experiment id of the started experiment
    :rtype: str

    :raise HTTPError: If the red post failed
    """
    red_data = _create_red_data(
        notebook_id, notebook_token, agency_url, agency_username, url_root, docker_image, gpu_requirements
    )

    r = requests.post(
        url_join(agency_url, 'red'),
        cookies={AUTHORIZATION_COOKIE_KEY: authorization_cookie},
        json=red_data
    )

    r.raise_for_status()

    return r.json()['experimentId']
