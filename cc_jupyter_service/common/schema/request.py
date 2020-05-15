request_schema = {
    'type': 'object',
    'properties': {
        'jupyterNotebooks': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'data': {'type': 'object'},
                    'filename': {'type': 'string'}
                }
            }
        },
        'dependencies': {
            'type': 'object',
            'properties': {
                'custom': {'type': 'boolean'},
                'predefinedImage': {'type': 'string'},
                'customImage': {'type': 'string'}
            },
            'additionalProperties': False,
            'required': ['custom', 'predefinedImage', 'customImage']
        }
    },
    'additionalProperties': False,
    'required': ['jupyterNotebooks', 'dependencies']
}
