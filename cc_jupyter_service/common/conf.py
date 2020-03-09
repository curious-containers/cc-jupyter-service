import jsonschema
from ruamel.yaml import YAML, YAMLError

from cc_jupyter_service.common.schema.configuration import configuration_schema

yaml = YAML(typ='safe')
yaml.default_flow_style = False


class Conf:
    @staticmethod
    def from_path(path):
        """
        Creates a Configuration object from the given path.

        :param path: The path of the config file
        :type path: str

        :return: A new conf object
        :rtype: Conf

        :raise ConfigurationError: If the configuration file is invalid
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

    def __init__(self, notebook_directory):
        """
        Creates a new Conf object.

        :param notebook_directory: The directory where to save the notebooks
        :type notebook_directory: str
        """
        self.notebook_directory = notebook_directory


class ConfigurationError(Exception):
    pass
