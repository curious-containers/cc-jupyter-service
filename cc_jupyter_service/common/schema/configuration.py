configuration_schema = {
    'type': 'object',
    'properties': {
        'notebookDirectory': {'type': 'string'},
        'flaskSecretKey': {'type': 'string'},
        'preventLocalhost': {'type': 'boolean'}
    },
    'additionalProperties': False,
    'required': ['notebookDirectory', 'flaskSecretKey']
}
