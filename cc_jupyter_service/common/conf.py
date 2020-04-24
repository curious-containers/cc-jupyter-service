import os

import jsonschema
from ruamel.yaml import YAML, YAMLError

from cc_jupyter_service.common.schema.configuration import configuration_schema

yaml = YAML(typ='safe')
yaml.default_flow_style = False

CONFIG_FILE_LOCATIONS = ['cc-agency-jupyter-service-config.yml', '~/.config/cc-jupyter-service.yml']


class Conf:
    def __init__(self, notebook_directory):
        """
        Creates a new Conf object.

        :param notebook_directory: The directory where to save the notebooks
        :type notebook_directory: str
        """
        self.notebook_directory = notebook_directory

    @staticmethod
    def from_system():
        """
        Loads the configuration file by searching at the following locations:
        - $HOME/.config/cc-jupyter-service.yml
        - ./cc-jupyter-service.yml

        The first present configuration file will be used.
        If on configuration file could be found a default configuration will be used.

        :return: The first configuration that was found
        :rtype: Conf

        :raise ConfigurationError: if an invalid configuration file was found
        """
        for config_location in CONFIG_FILE_LOCATIONS:
            path = os.path.expanduser(config_location)
            try:
                return Conf.from_path(path)
            except ConfigurationError as e:
                raise ConfigurationError('An invalid configuration file was found at "{}".\n{}'.format(path, str(e)))
            except FileNotFoundError:
                continue

        return Conf(notebook_directory='notebook_database')

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

        return Conf(notebook_directory=data['notebookDirectory'])


class ConfigurationError(Exception):
    pass
