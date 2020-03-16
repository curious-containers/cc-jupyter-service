import copy
import uuid

import requests
from werkzeug.urls import url_fix, url_join

from cc_jupyter_service.common import red_file_template
from cc_jupyter_service.service.db import get_db


def check_agency(agency_url, agency_username, agency_password):
    """
    Tries to contact the agency with the given authorization information. Raises a AgencyError, if the agency is not
    available or the authentication information is invalid.

    :param agency_url: The agency to contact
    :type agency_url: str
    :param agency_username: The username to use for authorization
    :type agency_username: str
    :param agency_password: The password to use for authorization
    :type agency_password: str

    :raise AgencyError: If the agency is not available or authentication information is invalid.
    """
    print('agency_url: {}'.format(agency_url))
    agency_url = url_join(agency_url + '/', 'nodes')
    print('agency_url: {}'.format(agency_url))
    response = requests.get(agency_url, auth=(agency_username, agency_password))
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise AgencyError(
            'Failed to verify agency for user "{}".\nstatus code: {}\nmessage: {}'.format(
                agency_username, response.status_code, str(e)
            )
        )


def exec_notebook(notebook_data, agency_url, agency_username, agency_password, notebook_database, url_root):
    """
    - Validates the agency authentication information
    - Generates a new token for the notebook
    - Saves the notebook
    - Saves meta information in the db
    - Executes the notebook on the agency

    :param notebook_data: The notebook data given as dictionary to execute.
    :param agency_url: The agency to use for execution
    :type agency_url: str
    :param agency_username: The agency username to use
    :type agency_username: str
    :param agency_password: The password for the given agency user
    :type agency_password: str
    :param notebook_database: The notebook database to save the notebook in
    :type notebook_database: NotebookDatabase
    :param url_root: The url root of this notebook service
    :type url_root: str
    """
    agency_url = url_fix(agency_url)

    check_agency(agency_url, agency_username, agency_password)

    token = uuid.uuid4()
    notebook_database.save_notebook(notebook_data, token)

    db = get_db()
    db.execute(
        'INSERT INTO notebook (token, username, agencyurl) VALUES (?, ?, ?)',
        (str(token), agency_username, agency_url)
    )

    start_agency(token, agency_url, agency_username, agency_password, url_root)


def start_agency(token, agency_url, agency_username, agency_password, url_root):
    """
    Executes the given notebook on the given agency.

    :param token: The token to reference the notebook.
    :type token: uuid.UUID
    :param agency_url: The agency to use for execution
    :type agency_url: str
    :param agency_username: The agency username to use
    :type agency_username: str
    :param agency_password: The password for the given agency user
    :type agency_password: str
    :param url_root: The url root of this notebook service
    :type url_root: str
    """
    red_data = copy.deepcopy(red_file_template.RED_FILE_TEMPLATE)

    input_notebook_access = red_data['inputs']['inputNotebook']['connector']['access']
    input_notebook_access['url'] = url_join(url_root, 'notebooks')
    input_notebook_access['auth']['username'] = agency_username
    input_notebook_access['auth']['password'] = str(token)

    output_notebook_access = red_data['outputs']['outputNotebook']['connector']['access']
    output_notebook_access['url'] = url_join(url_root, 'notebooks')
    output_notebook_access['auth']['username'] = agency_username
    output_notebook_access['auth']['password'] = str(token)

    execution_engine_access = red_data['execution']['settings']['access']
    execution_engine_access['url'] = agency_url
    execution_engine_access['auth']['username'] = agency_username
    execution_engine_access['auth']['password'] = agency_password


class AgencyError(Exception):
    pass
