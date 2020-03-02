from argparse import ArgumentParser

from flask import Flask

DESCRIPTION = 'CC-Agency Broker.'


def get_arguments():
    parser = ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        '-c', '--conf-file', action='store', type=str, metavar='CONF_FILE',
        help='CONF_FILE (yaml) as local path.'
    )
    return parser.parse_args()


app = Flask('cc-jupyter-service')


@app.route('/', methods=['GET'])
def get_root():
    return "<span style='color:red'>I am app 3</span>"
