request_schema = {
    'type': 'object',
    'properties': {
        'agencyUrl': {'type': 'string'},
        'agencyUsername': {'type': 'string'},
        'agencyPassword': {'type': 'string'},
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
    'required': ['agencyUrl', 'agencyUsername', 'agencyPassword', 'jupyterNotebooks', 'dependencies']
}
