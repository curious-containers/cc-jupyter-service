import requests
from werkzeug.urls import url_fix, url_join


AUTHORIZATION_COOKIE_KEY = 'authorization_cookie'


def normalize_url(url):
    """
    Adds https:// at the begin and / at the end if missing.

    :param url: The url to fix
    :type url: str
    :return: The fixed url
    :rtype: str
    """
    url = url_fix(url)
    if not (url.startswith('https://') or url.startswith('http://')):
        url = 'https://' + url
    if not url.endswith('/'):
        url = url + '/'
    return url


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
    :return: The authorization cookie of the agency
    :rtype: str

    :raise AgencyError: If the agency is not available or authentication information is invalid.
    :rtype: str
    """
    agency_url = url_join(agency_url, 'nodes')
    response = None
    try:
        response = requests.get(agency_url, auth=(agency_username, agency_password))
        response.raise_for_status()
        authorization_cookie = response.cookies.get(AUTHORIZATION_COOKIE_KEY)
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
        if response is not None:
            raise AgencyError(
                'Failed to verify agency "{}" for user "{}".\nstatus code: {}\nmessage: {}'.format(
                    agency_url, agency_username, response.status_code, str(e)
                )
            )
        else:
            raise AgencyError(
                'Failed to verify agency "{}" for user "{}".\nmessage: {}'.format(agency_url, agency_username, str(e))
            )

    return authorization_cookie


class AgencyError(Exception):
    pass
