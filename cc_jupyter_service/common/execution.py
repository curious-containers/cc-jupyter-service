import copy
import time
import uuid

import requests
from flask import g
from werkzeug.urls import url_join

from cc_jupyter_service.common import red_file_template
from cc_jupyter_service.common.helper import normalize_url, AUTHORIZATION_COOKIE_KEY, AgencyError
from cc_jupyter_service.service.db import DatabaseAPI


DEFAULT_DOCKER_IMAGE = 'bruno1996/cc_jupyterservice_base_image'


def exec_notebook(
        notebook_data, agency_url, agency_username, agency_authorization_cookie, notebook_database, url_root,
        docker_image, gpu_requirements, notebook_filename, external_data, python_requirements
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
    :param notebook_filename: The filename of the notebook
    :type notebook_data: str
    :param external_data: A list of dictionaries containing information about external data.
                          Should at least contain the keys ['inputName', 'inputType', 'connectorType']
    :type external_data: dict
    :param python_requirements: A dictionary containing a the keys 'data' and 'filename'. The value of 'data' is the
                                content of a requirements specification file for pip and filename is the filename of
                                this file.
    :type python_requirements: dict or None

    :return: The experiment id of the executed experiment
    :rtype: str
    """
    agency_url = normalize_url(agency_url)

    notebook_id = str(uuid.uuid4())

    notebook_token = str(uuid.uuid4())
    notebook_database.save_notebook(notebook_data, notebook_id)

    experiment_id = start_agency(
        notebook_id, notebook_token, agency_url, agency_username, agency_authorization_cookie, url_root, docker_image,
        gpu_requirements, external_data, python_requirements
    )

    py_reqs = None
    if python_requirements is not None:
        py_reqs = python_requirements['data']

    database_api = DatabaseAPI.create()
    database_api.create_notebook(
        notebook_id, notebook_token, g.user.user_id, experiment_id, notebook_filename, int(time.time()),
        python_requirements=py_reqs
    )

    return experiment_id


def _create_red_data(
        notebook_id, notebook_token, agency_url, agency_username, url_root, docker_image, gpu_requirements,
        external_data, python_requirements
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
    :param external_data: A list of dictionaries containing information about external data.
                          Should at least contain the keys ['inputName', 'inputType', 'connectorType']
    :type external_data: dict
    :param python_requirements: A dictionary containing a the keys 'data' and 'filename'. The value of 'data' is the
                                content of a requirements specification file for pip and filename is the filename of
                                this file.
    :type python_requirements: dict

    :return: The red data filled with the given information to execute on an agency

    :raise ValueError: If an unsupported external data connector type is specified.
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

    # TODO: validate external data information before accessing it
    # external data
    cli_inputs = red_data['cli']['inputs']
    for external_datum in external_data:
        if external_datum['connectorType'] == 'SSH':
            input_name = external_datum['inputName']

            # add cli specification
            cli_inputs[input_name] = {
                'type': external_datum['inputType'],
                'inputBinding': {
                    'prefix': input_name + '=',
                    'separate': False
                }
            }

            # add input specification
            red_data['inputs'][input_name] = {
                'class': external_datum['inputType'],
                'connector': {
                    'command': 'red-connector-ssh',
                    'access': {
                        'host': external_datum['host'],
                        'auth': {
                            'username': external_datum['username'],
                            'password': external_datum['password']
                        }
                    }
                }
            }
            if external_datum['inputType'] == 'File':
                red_data['inputs'][input_name]['connector']['access']['filePath'] = external_datum['path']
            elif external_datum['inputType'] == 'Directory':
                red_data['inputs'][input_name]['connector']['access']['dirPath'] = external_datum['path']
                red_data['inputs'][input_name]['connector']['mount'] = external_datum['mount']
                if external_datum['mount']:
                    red_data['inputs'][input_name]['connector']['access']['writable'] = True
            else:
                raise ValueError('Unknown inputType "{}" for "{}"'.format(external_datum['inputType'], input_name))
        else:
            raise ValueError(
                'Connector Types different from SSH are currently not supported. Got connector type: {}'
                .format(external_datum['connectorType'])
            )

    # python requirements
    if python_requirements is None:
        del red_data['inputs']['pythonRequirements']
    else:
        python_requirements_access = red_data['inputs']['pythonRequirements']['connector']['access']
        python_requirements_access['url'] = url_join(url_root, 'python_requirements/' + notebook_id)
        python_requirements_access['auth']['username'] = agency_username
        python_requirements_access['auth']['password'] = notebook_token

    return red_data


def start_agency(
        notebook_id, notebook_token, agency_url, agency_username, authorization_cookie, url_root, docker_image,
        gpu_requirements, external_data, python_requirements
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
    :param external_data: A list of dictionaries containing information about external data.
                          Should at least contain the keys ['inputName', 'inputType', 'connectorType']
    :type external_data: dict
    :param python_requirements: A dictionary containing a the keys 'data' and 'filename'. The value of 'data' is the
                                content of a requirements specification file for pip and filename is the filename of
                                this file.
    :type python_requirements: dict

    :return: The experiment id of the started experiment
    :rtype: str

    :raise HTTPError: If the red post failed
    """
    red_data = _create_red_data(
        notebook_id, notebook_token, agency_url, agency_username, url_root, docker_image, gpu_requirements,
        external_data, python_requirements
    )

    r = requests.post(
        url_join(agency_url, 'red'),
        cookies={AUTHORIZATION_COOKIE_KEY: authorization_cookie},
        json=red_data
    )

    try:
        r.raise_for_status()
    except Exception as e:
        print(e, flush=True)
        print(r.text, flush=True)
        raise

    return r.json()['experimentId']


def cancel_batch(experiment_id, agency_url, authorization_cookie):
    """
    Cancels the batch of the given experiment id
    :param experiment_id: The experiment to cancel. It is assumed that this experiment only contains one batch
    :type experiment_id: str
    :param agency_url: The agency url to use
    :type agency_url: str
    :param authorization_cookie: The authorization cookie value to use
    :type authorization_cookie: str

    :raise ValueError: If the experiment contains not only one batch
    :raise AgencyError: If the batch id could not be found or the batch could not be cancelled
    """
    r = requests.get(
        url_join(agency_url, 'batches?experimentId={}'.format(experiment_id)),
        cookies={AUTHORIZATION_COOKIE_KEY: authorization_cookie}
    )
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        raise AgencyError('Could not request the batch id. {}'.format(str(e)))

    batches = r.json()

    if len(batches) != 1:
        raise ValueError('Experiment has more than one batch.\nNumber of batches: {}'.format(len(batches)))
    batch_id = batches[0]['_id']

    r = requests.delete(
        url_join(agency_url, 'batches/{}'.format(batch_id)),
        cookies={AUTHORIZATION_COOKIE_KEY: authorization_cookie}
    )
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        raise AgencyError('Could not cancel batch {}. {}'.format(batch_id, str(e)))

    return batch_id
