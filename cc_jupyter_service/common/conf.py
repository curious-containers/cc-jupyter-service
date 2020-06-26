import os

import jsonschema
from ruamel.yaml import YAML, YAMLError

from cc_jupyter_service.common.schema.configuration import configuration_schema

yaml = YAML(typ='safe')
yaml.default_flow_style = False

CONFIG_FILE_LOCATIONS = ['cc-jupyter-service-config.yml', '~/.config/cc-jupyter-service.yml']
DEFAULT_SESSION_COOKIE = 'session'


class ImageInfo:
    def __init__(self, name, description, tag):
        """
        Creates a new predefined information object for an predefined docker image.

        :param name: The name of the image. This should be a short string that names the image
        :type name: str
        :param description: The description of the image.
        :type description: str
        :param tag: The tag that can be used by docker to identify the image at docker hub.
        :type tag: str
        """
        self.name = name
        self.description = description
        self.tag = tag

    def to_json(self):
        return {'name': self.name, 'description': self.description, 'tag': self.tag}


class Conf:
    def __init__(
        self, notebook_directory, flask_secret_key, prevent_localhost, predefined_docker_images, predefined_agency_urls,
        flask_session_cookie
    ):
        """
        Creates a new Conf object.

        :param notebook_directory: The directory where to save the notebooks
        :type notebook_directory: str
        :param flask_secret_key: The secret key for flask
        :type flask_secret_key: str
        :param prevent_localhost: Whether to prevent cc jupyter service to run on localhost or not
        :type prevent_localhost: bool
        :param predefined_docker_images: A list of predefined docker images. The user can choose docker images out of
                                         this list in the frontend.
        :type predefined_docker_images: list[ImageInfo]
        :param predefined_agency_urls: A list of strings defining agency urls which are displayed at the login page
        :type predefined_agency_urls: list[str] or None
        :param flask_session_cookie: The name of the flask session cookie
        :type flask_session_cookie: str
        """
        self.notebook_directory = notebook_directory
        self.flask_secret_key = flask_secret_key
        self.prevent_localhost = prevent_localhost
        self.predefined_docker_images = predefined_docker_images
        self.predefined_agency_urls = predefined_agency_urls
        self.flask_session_cookie = flask_session_cookie

    @staticmethod
    def from_system():
        """
        Loads the configuration file by searching at the following locations:
        - $HOME/.config/cc-jupyter-service.yml
        - ./cc-jupyter-service.yml

        The first present configuration file will be used.
        If no configuration file could an ConfigurationError is raised.

        :return: The first configuration that was found
        :rtype: Conf

        :raise ConfigurationError: If an invalid configuration file was found or no configuration file could be found
        """
        for config_location in CONFIG_FILE_LOCATIONS:
            path = os.path.expanduser(config_location)
            try:
                return Conf.from_path(path)
            except ConfigurationError as e:
                raise ConfigurationError('An invalid configuration file was found at "{}".\n{}'.format(path, str(e)))
            except FileNotFoundError:
                continue

        raise ConfigurationError('No configuration file could be found. Looked at {}'.format(CONFIG_FILE_LOCATIONS))

    @staticmethod
    def from_path(path):
        """
        Creates a Configuration object from the given path.

        :param path: The path of the config file
        :type path: str

        :return: A new conf object
        :rtype: Conf

        :raise ConfigurationError: If the configuration file is invalid or could not be found
        """
        try:
            with open(path, 'r') as f:
                data = yaml.load(f)
        except YAMLError as e:
            raise ConfigurationError(
                'Could not parse config file "{}". File is not yaml formatted.\n{}'.format(path, e)
            )

        try:
            jsonschema.validate(data, configuration_schema)
        except jsonschema.ValidationError as e:
            raise ConfigurationError('Invalid config file. {}'.format(e))

        predefined_docker_images = list(map(
            lambda image: ImageInfo(image['name'], image['description'], image['tag']),
            data.get('predefinedDockerImages', [])
        ))

        return Conf(
            notebook_directory=data['notebookDirectory'],
            flask_secret_key=data['flaskSecretKey'],
            prevent_localhost=data.get('preventLocalhost', True),
            predefined_docker_images=predefined_docker_images,
            predefined_agency_urls=data.get('predefinedAgencyUrls'),
            flask_session_cookie=data.get('flaskSessionCookie', DEFAULT_SESSION_COOKIE)
        )


class ConfigurationError(Exception):
    pass
