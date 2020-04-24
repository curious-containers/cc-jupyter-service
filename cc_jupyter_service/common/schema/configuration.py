configuration_schema = {
    'type': 'object',
    'properties': {
        'notebookDirectory': {'type': 'string'},
        'flaskSecretKey': {'type': 'string'}
    },
    'additionalProperties': False,
    'required': ['notebookDirectory', 'flaskSecretKey']
}
