import os

import jsonschema
from ruamel.yaml import YAML, YAMLError

from cc_jupyter_service.common.schema.configuration import configuration_schema

yaml = YAML(typ='safe')
yaml.default_flow_style = False

CONFIG_FILE_LOCATIONS = ['cc-agency-jupyter-service-config.yml', '~/.config/cc-jupyter-service.yml']


class Conf:
    def __init__(self, notebook_directory, flask_secret_key, prevent_localhost):
        """
        Creates a new Conf object.

        :param notebook_directory: The directory where to save the notebooks
        :type notebook_directory: str
        :param flask_secret_key: The secret key for flask
        :type flask_secret_key: str
        :param prevent_localhost: Whether to prevent cc jupyter service to run on localhost or not
        :type prevent_localhost: bool
        """
        self.notebook_directory = notebook_directory
        self.flask_secret_key = flask_secret_key
        self.prevent_localhost = prevent_localhost

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

        raise ConfigurationError('No configuration file could be found')

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

        return Conf(
            notebook_directory=data['notebookDirectory'],
            flask_secret_key=data['flaskSecretKey'],
            prevent_localhost=data.get('preventLocalhost', True)
        )


class ConfigurationError(Exception):
    pass
