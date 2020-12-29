# TODO https://github.com/chibisov/drf-extensions/issues/294
from django.db.models.sql import datastructures
from django.core.exceptions import EmptyResultSet

datastructures.EmptyResultSet = EmptyResultSet