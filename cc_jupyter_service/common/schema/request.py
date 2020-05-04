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
        'dependencies': {'type': 'array'}
    },
    'additionalProperties': False,
    'required': ['jupyterNotebooks', 'dependencies']
}
