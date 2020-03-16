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
        return os.path.join(database_directory, '{}.ipynb'.format(str(self.token)))


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

    def save_notebook(self, notebook_data, token):
        """
        Saves the given notebook on the filesystem.

        :param notebook_data: The notebook file data
        :type notebook_data: object
        :param token: The token for identification of the notebook
        :type token: uuid.UUID
        :return: A NotebookCursor pointing to the created file
        :rtype: NotebookCursor
        """
        notebook_cursor = NotebookCursor(token)
        with open(notebook_cursor.get_path(self.database_directory), 'w') as file:
            json.dump(notebook_data, file)

        return notebook_cursor
