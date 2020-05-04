import sqlite3
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
        def __init__(self, db_id, notebook_id, notebook_token, user_id):
            """
            Creates a Notebook.

            :param db_id: The db id
            :type db_id: int
            :param notebook_id: The notebook id
            :type notebook_id: str
            :param notebook_token: The token for this notebook
            :type notebook_token: str
            :param user_id: The user id that executed this notebook
            :type user_id: int
            """
            self.db_id = db_id
            self.notebook_id = notebook_id
            self.notebook_token = notebook_token
            self.user_id = user_id

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

    def create_notebook(self, notebook_id, notebook_token, user_id):
        """
        Inserts the given notebook information into the db.

        :param notebook_id: The notebook id
        :type notebook_id: str
        :param notebook_token: The authentication token for the notebook
        :type notebook_token: str
        :param user_id: The id of the user
        :type user_id: int
        """
        self.db.execute(
            'INSERT INTO notebook (notebook_id, notebook_token, user_id) VALUES (?, ?, ?)',
            (notebook_id, generate_password_hash(notebook_token), user_id)
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
            'SELECT id, notebook_id, notebook_token, user_id FROM notebook WHERE notebook_id is ?',
            (notebook_id,)
        )

        row = None
        for index, r in enumerate(cur):
            if index > 0:
                raise DatabaseError('NotebookID "{}" is not unique.'.format(notebook_id))
            row = r

        if row is None:
            raise DatabaseError('NotebookID "{}" could not be found'.format(notebook_id))

        return DatabaseAPI.Notebook(row[0], row[1], row[2], row[3])

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

    def get_user(self, user_id=None, agency_username=None):
        """
        Gets a user by id or agency username. At least one of both should be given. If both are given agency username is
        ignored.

        :param user_id: The user id
        :type user_id: int
        :param agency_username: The agency username of the user
        :type agency_username: str
        :return: The user, if available. Otherwise None.
        :rtype: DatabaseAPI.User or None

        :raise ValueError: If user_id and agency_username is None
        """
        if user_id is not None:
            cur = self.db.execute(
                'SELECT id, agency_username, agency_url FROM user WHERE id is ?',
                (user_id,)
            )
        elif agency_username is not None:
            cur = self.db.execute(
                'SELECT id, agency_username, agency_url FROM user WHERE agency_username is ?',
                (agency_username,)
            )
        else:
            raise ValueError('user id and agency username are None')
        user_data = cur.fetchone()
        if user_data is None:
            return None

        return DatabaseAPI.User(user_data[0], user_data[1], user_data[2])


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
