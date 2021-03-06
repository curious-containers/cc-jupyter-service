import enum
import os

import sqlite3
import time

import click
from flask import g, current_app, Flask
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash


class DatabaseAPI:
    class User:
        def __init__(self, user_id, agency_username, agency_url):
            """
            Creates a new Database User.

            :type user_id: int
            :type agency_username: str
            :type agency_url: str
            """
            self.user_id = user_id
            self.agency_username = agency_username
            self.agency_url = agency_url

    class Notebook:
        def __init__(
            self, db_id, notebook_id, notebook_token, experiment_id, status, notebook_filename, execution_time,
            debug_info, user_id, python_requirements
        ):
            """
            Creates a Notebook.

            :param db_id: The db id
            :type db_id: int
            :param notebook_id: The notebook id
            :type notebook_id: str
            :param notebook_token: The token for this notebook
            :type notebook_token: str
            :param experiment_id: The id of the experiment executing this notebook
            :type experiment_id: str
            :param status: The processing status of this notebook as int
            :type status: int
            :param notebook_filename: The filename of the notebook
            :type notebook_filename: str
            :param execution_time: The timestamp of the execution of this notebook
            :type execution_time: int
            :param debug_info: The debug information, if the batch failed
            :type debug_info: str or None
            :param user_id: The user id that executed this notebook
            :type user_id: int
            :param python_requirements: The content of a requirements.txt file
            :type python_requirements: str
            """
            self.db_id = db_id
            self.notebook_id = notebook_id
            self.notebook_token = notebook_token
            self.experiment_id = experiment_id
            self.status = DatabaseAPI.NotebookStatus.from_int(status)
            self.notebook_filename = notebook_filename
            self.execution_time = execution_time
            self.debug_info = debug_info
            self.user_id = user_id
            self.python_requirements = python_requirements

        def get_filename_without_ext(self):
            """
            :return: The filename without extension
            :rtype: str
            """
            return os.path.splitext(self.notebook_filename)[0]

    class Cookie:
        def __init__(self, db_id, cookie_text, creation_time, user_id):
            """
            Creates a Cookie.

            :param db_id: The database id of this cookie
            :type db_id: int
            :param cookie_text: The text of the cookie
            :type cookie_text: str
            :param creation_time: The creation time of the cookie as timestamp
            :type creation_time: float
            :param user_id: The owning user id
            :type user_id: int
            """
            self.db_id = db_id
            self.cookie_text = cookie_text
            self.creation_time = creation_time
            self.user_id = user_id

    class NotebookStatus(enum.IntEnum):
        PROCESSING = 0
        SUCCESS = 1
        FAILURE = 2
        CANCELLED = 3

        def __str__(self):
            return self.name.lower()

        @classmethod
        def from_int(cls, value):
            for e in cls:
                if e == value:
                    return e
            raise ValueError('Cannot create NotebookStatus with value {}'.format(value))

        @staticmethod
        def from_experiment_state(experiment_state):
            notebook_status = DatabaseAPI.EXPERIMENT_STATE_TO_NOTEBOOK_STATUS.get(experiment_state)
            if notebook_status is None:
                raise ValueError('Cannot create NotebookStatus from experiment state "{}"'.format(experiment_state))
            return notebook_status

    EXPERIMENT_STATE_TO_NOTEBOOK_STATUS = {
        'processing': NotebookStatus.PROCESSING,
        'succeeded': NotebookStatus.SUCCESS,
        'failed': NotebookStatus.FAILURE,
        'cancelled': NotebookStatus.CANCELLED
    }

    def __init__(self, db):
        """
        Initializes a new DatabaseAPI.

        :param db: The db object to handle requests with
        :type db: sqlite3.Connection
        """
        self.db = db

    @staticmethod
    def create():
        """
        Creates a new Database.

        :return: The Database object
        :rtype: DatabaseAPI
        """
        return DatabaseAPI(get_db())

    def create_notebook(
            self, notebook_id, notebook_token, user_id, experiment_id, notebook_filename, execution_time,
            status=NotebookStatus.PROCESSING, python_requirements=None
    ):
        """
        Inserts the given notebook information into the db.

        :param notebook_id: The notebook id
        :type notebook_id: str
        :param notebook_token: The authentication token for the notebook
        :type notebook_token: str
        :param user_id: The id of the user
        :type user_id: int
        :param experiment_id: The id of the experiment executing this notebook
        :type experiment_id: str
        :param notebook_filename: The filename of the notebook
        :type notebook_filename: str
        :param execution_time: The timestamp of the notebook execution in seconds per epoch
        :type execution_time: int
        :param status: The initial status of the notebook. Defaults to PROCESSING
        :type status: DatabaseAPI.NotebookStatus
        :param python_requirements: The python requirements for this notebook
        :type python_requirements: str or None
        """
        self.db.execute(
            'INSERT INTO notebook ('
            'notebook_id, notebook_token, experiment_id, status, notebook_filename, execution_time, user_id, '
            'python_requirements'
            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (
                notebook_id, generate_password_hash(notebook_token), experiment_id, int(status), notebook_filename,
                execution_time, user_id, python_requirements
            )
        )
        self.db.commit()

    def update_notebook_status(self, notebook_id, status):
        """
        Updates the status of the given notebook

        :param notebook_id: The id of the notebook
        :type notebook_id: str
        :param status: The status to set
        :type status: DatabaseAPI.NotebookStatus
        """
        self.db.execute(
            'UPDATE notebook SET status = (?) WHERE notebook_id is ?',
            (int(status), notebook_id)
        )
        self.db.commit()

    def update_notebook_debug_info(self, notebook_id, debug_info):
        """
        Updates the debug info in the database

        :param notebook_id: The notebook id to update the debug info for
        :type notebook_id: str
        :param debug_info: The debug info to save
        :type debug_info: str
        :return:
        """
        self.db.execute(
            'UPDATE notebook SET debug_info = (?) WHERE notebook_id is ?',
            (debug_info, notebook_id)
        )
        self.db.commit()

    def get_notebook(self, notebook_id):
        """
        Returns information about the notebook

        :param notebook_id: The id of the notebook
        :return: The requested Notebook
        :rtype: DatabaseAPI.Notebook

        :raise DatabaseError: If the given notebook_id is not unique or could not be found
        """
        cur = self.db.execute(
            'SELECT id, notebook_id, notebook_token, experiment_id, status, notebook_filename, execution_time, '
            'debug_info, user_id, python_requirements '
            'FROM notebook WHERE notebook_id is ?',
            (notebook_id,)
        )

        row = None
        for index, r in enumerate(cur):
            if index > 0:
                raise DatabaseError('NotebookID "{}" is not unique.'.format(notebook_id))
            row = r

        if row is None:
            raise DatabaseError('NotebookID "{}" could not be found'.format(notebook_id))

        return DatabaseAPI.Notebook(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9])

    def get_notebooks(self, user_id, status=None):
        """
        Returns a list of notebook executed by the given user

        :param user_id: The user id of the executing user
        :type user_id: int
        :param status: The status that is used for filtering
        :type status: DatabaseAPI.NotebookStatus
        :return: List of Notebooks
        :rtype: list[DatabaseAPI.Notebook]
        """
        if status is None:
            cur = self.db.execute(
                'SELECT id, notebook_id, notebook_token, experiment_id, status, notebook_filename, execution_time, '
                'debug_info, user_id, python_requirements '
                'FROM notebook '
                'WHERE user_id is ?',
                (user_id,)
            )
        else:
            cur = self.db.execute(
                'SELECT id, notebook_id, notebook_token, experiment_id, status, notebook_filename, execution_time, '
                'debug_info, user_id, python_requirements '
                'FROM notebook '
                'WHERE user_id is ? AND status is ?',
                (user_id, int(status))
            )

        notebooks = []
        for notebook_data in cur:
            notebooks.append(DatabaseAPI.Notebook(
                db_id=notebook_data[0],
                notebook_id=notebook_data[1],
                notebook_token=notebook_data[2],
                experiment_id=notebook_data[3],
                status=notebook_data[4],
                notebook_filename=notebook_data[5],
                execution_time=notebook_data[6],
                debug_info=notebook_data[7],
                user_id=notebook_data[8],
                python_requirements=notebook_data[9]
            ))
        return notebooks

    def create_user(self, agency_username, agency_url):
        """
        Creates a new user.

        :param agency_username: The username valid for an agency
        :type agency_username: str
        :param agency_url: The url for the agency of this user
        :type agency_url: str
        :return: The id of the created user
        :rtype: int
        """
        cur = self.db.cursor()
        cur.execute(
            'INSERT INTO user (agency_username, agency_url) VALUES (?, ?)', (agency_username, agency_url)
        )
        self.db.commit()
        return cur.lastrowid

    def get_user(self, user_id=None, agency_username_url=None):
        """
        Gets a user by id or agency username and url. At least one of both should be given. If both are given agency
        username/url is ignored.

        :param user_id: The user id
        :type user_id: int
        :param agency_username_url: A tuple containing the agency username of the user and the agency url
        :type agency_username_url: tuple[str, str]
        :return: The user, if available. Otherwise None.
        :rtype: DatabaseAPI.User or None

        :raise ValueError: If user_id and agency_username is None
        """
        if user_id is not None:
            cur = self.db.execute(
                'SELECT id, agency_username, agency_url FROM user WHERE id is ?',
                (user_id,)
            )
        elif agency_username_url is not None:
            cur = self.db.execute(
                'SELECT id, agency_username, agency_url FROM user WHERE agency_username is ? AND agency_url is ?',
                (agency_username_url[0], agency_username_url[1])
            )
        else:
            raise ValueError('user id and agency username/url are None')
        user_data = cur.fetchone()
        if user_data is None:
            return None

        return DatabaseAPI.User(user_data[0], user_data[1], user_data[2])

    def create_cookie(self, cookie_text, user_id):
        """
        Creates a new cookie.

        :param cookie_text: The text of the cookie
        :type cookie_text: str
        :param user_id: The id of the user
        :type user_id: int

        :return: The id of the created cookie
        :rtype: int
        """
        cur = self.db.cursor()
        cur.execute(
            'INSERT INTO cookie (cookie_text, creation_time, user_id) VALUES (?, ?, ?)',
            (cookie_text, time.time(), user_id)
        )
        self.db.commit()
        return cur.lastrowid

    def get_cookies(self, user_id):
        """
        Gets the cookies of the given user.

        :param user_id: The user id
        :type user_id: int
        :return: The list of cookies of the given user
        :rtype: list[DatabaseAPI.Cookie]
        """
        cur = self.db.execute(
            'SELECT id, cookie_text, creation_time, user_id FROM cookie WHERE user_id is ?',
            (user_id,)
        )
        cookies = []
        for cookie in cur:
            cookies.append(DatabaseAPI.Cookie(cookie[0], cookie[1], cookie[2], cookie[3]))
        return cookies

    def get_newest_cookie(self, user_id):
        """
        Gets the newest cookie of the given user id

        :param user_id: The user id
        :type user_id: int
        :return: The cookie with the highest creation time
        :rtype: DatabaseAPI.Cookie or None
        """
        cur = self.db.execute(
            'SELECT id, cookie_text, creation_time, user_id FROM cookie WHERE user_id is ? ORDER BY creation_time DESC',
            (user_id,)
        )

        cookie_data = cur.fetchone()
        if cookie_data is None:
            return None

        return DatabaseAPI.Cookie(cookie_data[0], cookie_data[1], cookie_data[2], cookie_data[3])


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(_e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))


def init_app(app):
    """

    :param app:
    :type app: Flask
    :return:
    """
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


class DatabaseError(Exception):
    pass
