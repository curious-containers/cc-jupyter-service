import sqlite3
import click
from flask import g, current_app, Flask
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash


class DatabaseAPI:
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

    def insert_notebook(self, notebook_id, notebook_token, agency_username, agency_url):
        """
        Inserts the given notebook information into the db.

        :param notebook_id: The notebook id
        :type notebook_id: str
        :param notebook_token: The authentication token for the notebook
        :type notebook_token: str
        :param agency_username: The agency username
        :type agency_username: str
        :param agency_url: The agency url
        :type agency_url: str
        """
        self.db.execute(
            'INSERT INTO notebook (notebook_id, token, username, agencyurl) VALUES (?, ?, ?, ?)',
            (notebook_id, generate_password_hash(notebook_token), agency_username, agency_url)
        )
        self.db.commit()

    def get_notebook(self, notebook_id):
        """
        Returns information about the notebook

        :param notebook_id: The id of the notebook
        :return: A tuple containing (notebook_token, agency_username, agency_url)
        :rtype: tuple[str, str, str]

        :raise DatabaseError: If the given notebook_id is not unique or could not be found
        """
        cur = self.db.execute('SELECT token, username, agencyurl FROM notebook WHERE notebook_id is ?', (notebook_id,))

        row = None
        for index, r in enumerate(cur):
            if index > 0:
                raise DatabaseError('NotebookID "{}" is not unique.'.format(notebook_id))
            row = r

        if row is None:
            raise DatabaseError('NotebookID "{}" could not be found'.format(notebook_id))

        return row


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
