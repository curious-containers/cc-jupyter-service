import os

from flask import Flask, render_template, request, jsonify
from werkzeug.exceptions import BadRequest
import jsonschema
import nbformat

import cc_jupyter_service.service.db as db
from cc_jupyter_service.common.schema.request import request_schema

DESCRIPTION = 'CC-Jupyter-Service.'


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',  # TODO: overwrite dev
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

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
            raise BadRequest('Failed to validate toplevel schema. {}'.format(str(e)))

        for jupyterNotebook in request_data['jupyterNotebooks']:
            try:
                nbformat.validate(jupyterNotebook['data'])
            except nbformat.ValidationError as e:
                raise BadRequest('Failed to validate notebook "{}.\n{}"'.format(jupyterNotebook['filename'], str(e)))

        return jsonify({'hello': 'world'})

    db.init_app(app)

    return app
