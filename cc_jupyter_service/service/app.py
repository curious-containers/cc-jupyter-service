import os

from flask import Flask, render_template, request, jsonify
from werkzeug.exceptions import BadRequest
import jsonschema
import nbformat

import cc_jupyter_service.service.db as db
from cc_jupyter_service.common.notebook_database import NotebookDatabase
from cc_jupyter_service.common.schema.request import request_schema
from cc_jupyter_service.common.conf import Conf

DESCRIPTION = 'CC-Jupyter-Service.'


conf = Conf.from_system()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',  # TODO: overwrite dev
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    notebook_database = NotebookDatabase(conf.notebook_directory)

    @app.route('/', methods=['GET'])
    def get_root():
        return render_template('hello.html')

    @app.route('/executeNotebook', methods=['POST'])
    def execute_notebook():
        if not request.json:
            raise BadRequest('Did not send data as json')

        request_data = request.json

        try:
            jsonschema.validate(request_data, request_schema)
        except jsonschema.ValidationError as e:
            raise BadRequest('Failed to validate request data. {}'.format(str(e)))

        for jupyter_notebook in request_data['jupyterNotebooks']:
            try:
                nbformat.validate(jupyter_notebook['data'])
            except nbformat.ValidationError as e:
                raise BadRequest('Failed to validate notebook "{}.\n{}"'.format(jupyter_notebook['filename'], str(e)))

        for jupyter_notebook in request_data['jupyterNotebooks']:
            notebook_database.save_notebook(
                jupyter_notebook['data'],
                request_data['agencyUrl'],
                request_data['agencyUsername']
            )

        return jsonify({'hello': 'world'})

    db.init_app(app)

    return app
