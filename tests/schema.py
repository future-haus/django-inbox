
group = {
    'type': 'object',
    'required': ['id', 'label', 'description'],
    'properties': {
        'id': {'type': 'string'},
        'label': {'type': 'string'},
        'description': {'type': 'string'},
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
    'required': ['groups'],
    'properties': {
        'groups': groups
    },
    'additionalProperties': False
}
