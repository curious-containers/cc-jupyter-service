import json
import os
from uuid import UUID


class NotebookCursor:
    def __init__(self, token):
        """
        Represents a notebook saved on disk. Does not contain the data of the notebook.

        :param token: The token of the notebook
        :type token: UUID
        """
        self.token = token

    def get_path(self, database_directory):
        """
        :param database_directory: The database directory
        :type database_directory: str

        :return: the path of the notebook
        :rtype: str
        """
        return


class NotebookDatabase:
    """
    This class manages jupyter notebook files on disk.

    The database directory is ordered in the following way:
    / database_directory/
      / notebook_token.ipynb
    """
    def __init__(self, database_directory):
        """
        Creates a NotebookDatabase that manages notebook files under the given database directory.

        :param database_directory: The base directory of the notebooks to save
        :type database_directory: str
        """
        self.database_directory = database_directory

        if not os.path.isdir(database_directory):
            os.makedirs(database_directory)

    def _notebook_id_to_path(self, notebook_id):
        """
        Returns the path of the requested notebook.

        :param notebook_id: The id to get the path of
        :type notebook_id: str
        :return: The path to the notebook
        :rtype: str
        """
        return os.path.join(self.database_directory, '{}.ipynb'.format(notebook_id))

    def save_notebook(self, notebook_data, notebook_id):
        """
        Saves the given notebook on the filesystem.

        :param notebook_data: The notebook file data
        :type notebook_data: object
        :param notebook_id: The id of the notebook
        :type notebook_id: uuid.UUID
        :return: A NotebookCursor pointing to the created file
        :rtype: NotebookCursor
        """
        path = self._notebook_id_to_path(str(notebook_id))
        with open(path, 'w') as file:
            json.dump(notebook_data, file)

    def get_notebook(self, notebook_id):
        """
        Returns the requested notebook.

        :param notebook_id: The id of the requested notebook
        :type notebook_id: str
        :return: The requested notebook data
        :rtype: object
        """
        raise NotImplementedError()
