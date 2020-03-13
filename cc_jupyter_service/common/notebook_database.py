import json
import os
import base64
from uuid import uuid4


class NotebookCursor:
    def __init__(self, token, agency_url, agency_username):
        """
        Represents a notebook saved on disk. Does not contain the data of the notebook.

        :param token: The token of the notebook
        :type token: str
        :param agency_url: The agency url
        :type agency_url: str
        :param agency_username: The owning user
        :type agency_username: str
        """
        self.token = token
        self.agency_url = agency_url
        self.agency_username = agency_username

    def get_path(self, database_directory):
        """
        :param database_directory: The database directory
        :type database_directory: str

        :return: the path of the saved notebook
        :rtype: str
        """
        return os.path.join(database_directory, base64.b64encode(self.agency_url), base64.b64encode(self.agency_username), self.token)


class NotebookDatabase:
    """
    This class manages jupyter notebook files on disk.

    The database directory is ordered in the following way:
    / database_directory/
      / agency_url_base64_encoded/
        / agency_username_base64_encoded/
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

    def save_notebook(self, notebook_data, agency_url, agency_username):
        """
        Saves the given notebook on the filesystem.

        :param notebook_data: The notebook file data
        :type notebook_data: object
        :param agency_url: The url of the agency
        :type agency_url: str
        :param agency_username: The username of the user owning the notebook
        :type agency_username: str
        :return: A NotebookCursor pointing to the created file
        :rtype: NotebookCursor
        """
        token = str(uuid4())
        notebook_cursor = NotebookCursor(token, agency_url, agency_username)
        with open(notebook_cursor.get_path(self.database_directory), 'w') as file:
            json.dump(notebook_data, file)
        return notebook_cursor
