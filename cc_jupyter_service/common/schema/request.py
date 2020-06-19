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
        },
        'pythonRequirements': {
            'oneOf': [
                {'type': 'null'},
                {
                    'type': 'object',
                    'properties': {
                        'data': {'type': 'string'},
                        'filename': {'type': 'string'}
                    }
                }
            ]
        },
        'gpuRequirements': {
            'type': 'array',
            'items': {
                'type': 'integer',
                'minimum': 0
            }
        },
        'externalData': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'inputName': {'type': 'string'},
                    'inputType': {
                        'type': 'string',
                        'enum': ['File', 'Directory']
                    },
                    'connectorType': {'type': 'string'},
                }
            }
        }
    },
    'additionalProperties': False,
    'required': ['jupyterNotebooks', 'dependencies', 'pythonRequirements', 'gpuRequirements']
}
