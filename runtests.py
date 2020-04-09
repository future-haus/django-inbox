#!/usr/bin/env python
import os
import sys

from django.conf import settings
from django.test.utils import get_runner
import django


def runtests():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'

    # TODO Need to get this working so that we can create/destroy the
    #  DB each time to assure starting from clean state
    # from django.db import connections
    # cursor = connections['postgres'].cursor()
    # cursor.execute("""
    #         CREATE ROLE inbox WITH LOGIN PASSWORD 'password';
    #         ALTER USER inbox WITH superuser;
    #         CREATE DATABASE inbox;
    #         ALTER ROLE inbox SET client_encoding TO 'utf8';
    #         ALTER ROLE inbox SET default_transaction_isolation TO 'read committed';
    #         ALTER ROLE inbox SET timezone TO 'UTC';
    #         ALTER USER inbox CREATEDB;
    #         GRANT ALL PRIVILEGES ON DATABASE inbox TO inbox;
    #     """)

    # Create migrations
    from django.core.management import execute_from_command_line
    args = ['django', 'makemigrations']
    execute_from_command_line(args)

    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['tests'])
    sys.exit(bool(failures))

    # TODO Destroy DB
    # TODO Clear migrations folder in inbox


if __name__ == '__main__':
    runtests()
