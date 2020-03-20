import os

from flask import Flask, render_template, request, jsonify
from requests import HTTPError
from werkzeug.exceptions import BadRequest
import jsonschema
import nbformat

import cc_jupyter_service.service.db as db
from cc_jupyter_service.common.execution import exec_notebook
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

    def validate_request(request_data):
        """
        This function validates the given request data.

        :param request_data: The request data to validate

        :raise BadRequest: If the request data is invalid
        """
        try:
            jsonschema.validate(request_data, request_schema)
        except jsonschema.ValidationError as e:
            raise BadRequest('Failed to validate request data. {}'.format(str(e)))

        for jupyter_notebook in request_data['jupyterNotebooks']:
            try:
                nbformat.validate(jupyter_notebook['data'])
            except nbformat.ValidationError as e:
                raise BadRequest('Failed to validate notebook "{}.\n{}"'.format(jupyter_notebook['filename'], str(e)))

    @app.route('/', methods=['GET'])
    def get_root():
        return render_template('hello.html')

    @app.route('/executeNotebook', methods=['POST'])
    def execute_notebook():
        if not request.json:
            raise BadRequest('Did not send data as json')

        request_data = request.json

        validate_request(request_data)

        if 'localhost' in request.url_root or '127.0.0.1' in request.url_root:
            raise BadRequest(
                'Cant retrieve public endpoint of this jupyter service. '
                'Make sure this jupyter service runs not on localhost'
            )

        experiment_ids = []

        for jupyter_notebook in request_data['jupyterNotebooks']:
            try:
                experiment_id = exec_notebook(
                    jupyter_notebook['data'],
                    agency_url=request_data['agencyUrl'],
                    agency_username=request_data['agencyUsername'],
                    agency_password=request_data['agencyPassword'],
                    notebook_database=notebook_database,
                    url_root=request.url_root
                )
            except HTTPError as e:
                raise BadRequest('Could not execute {}. {}'.format(jupyter_notebook['filename'], str(e)))
            experiment_ids.append(experiment_id)

        return jsonify({'experimentIds': experiment_ids})

    db.init_app(app)

    return app
