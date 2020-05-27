
group = {
    'type': 'object',
    'required': ['id', 'label', 'description', 'data'],
    'properties': {
        'id': {'type': 'string'},
        'label': {'type': 'string'},
        'description': {'type': 'string'},
        'data': {'type': ['null', 'object']},
        'app_push': {'type': ['null', 'boolean']},
        'email': {'type': ['null', 'boolean']},
        'sms': {'type': ['null', 'boolean']},
        'web_push': {'type': ['null', 'boolean']}
    },
    'additionalProperties': False
}

groups = {
    "type": [
        "array"
    ],
    "items": {
        "type": "object",
        "oneOf": [group]
    },
    "minItems": 0
}

message_preferences = {
    'type': 'object',
    'required': ['results'],
    'properties': {
        'results': groups
    },
    'additionalProperties': False
}

message = {
    'type': 'object',
    'required': ['id',],
    'properties': {
        'id': {'type': 'string'},
        'subject': {'type': 'string'},
        'body': {'type': 'string'},
        'data': {'type': ['null', 'object']},
        'group': {
            'type': 'object',
            'required': ['id', 'label', 'data'],
            'properties': {
                'id': {'type': 'string'},
                'label': {'type': 'string'},
                'data': {'type': ['null', 'object']}
            },
            'additionalProperties': False
        },
        'is_read': {'type': 'boolean'},
        'created_at': {'type': 'string'}
    },
    'additionalProperties': False
}

messages = {
    "type": [
        "array"
    ],
    "items": {
        "type": "object",
        "oneOf": [message]
    },
    "minItems": 0
}

unread_count = {
    "type": "integer"
}