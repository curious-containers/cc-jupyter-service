configuration_schema = {
    'type': 'object',
    'properties': {
        'notebookDirectory': {'type': 'string'},
        'flaskSecretKey': {'type': 'string'},
        'preventLocalhost': {'type': 'boolean'},
        'predefinedDockerImages': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'description': {'type': 'string'},
                    'tag': {'type': 'string'},
                },
                'additionalProperties': False,
                'required': ['name', 'description', 'tag']
            }
        },
        'predefinedAgencyUrls': {
            'type': 'array',
            'items': {'type': 'string'},
            'minItems': 1
        },
        'flaskSessionCookie': {'type': 'string'}
    },
    'additionalProperties': False,
    'required': ['notebookDirectory', 'flaskSecretKey']
}
