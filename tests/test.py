import json
import platform

from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase

from jsonschema import Draft4Validator

_is_cpython = (
        hasattr(platform, 'python_implementation') and
        platform.python_implementation().lower() == "cpython"
)


class HTTPStatusTestCaseMixin(object):

    def assertHTTP200(self, response):
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def assertHTTP201(self, response):
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def assertHTTP204(self, response):
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def assertHTTP400(self, response):
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def assertHTTP401(self, response):
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def assertHTTP403(self, response):
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def assertHTTP404(self, response):
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ClientHelperMixin(object):

    def validate(self, data, schema):
        v = Draft4Validator(schema)
        if not v.is_valid(data):
            for error in sorted(v.iter_errors(data), key=str):
                if error.context:
                    self.fail("\n".join('{} {}'.format(cerror.absolute_path, cerror.message) for cerror in error.context))
                else:
                    self.fail(error.message)

    def validate_retrieve(self, response, schema):
        self.validate(response.data, schema)

    def validate_list(self, response, schema, pages=True):
        if pages:
            self.validate(response.data['results'][0], schema['items']['oneOf'][0])
            self.validate(response.data['results'], schema)
        else:
            self.validate(response.data[0], schema['items']['oneOf'][0])
            self.validate(response.data, schema)

    def get(self, path, data=None, follow=False, secure=False, **extra):
        print('***' * 15)
        print('GET {}'.format(path))
        print('Authenticated' if '_auth_user_id' in self.client.session else 'Not Authenticated')
        response = self.client.get(path=path, data=data, follow=follow, secure=secure, **extra)
        print('Response status code: {}'.format(response.status_code))
        if hasattr(response, 'data'):
            print('Response body:')
            print(json.dumps(response.data))
        return response

    def post(self, path, data=None, content_type=None, follow=False, secure=False, **extra):
        print('***' * 15)
        print('POST {}'.format(path))
        print('Authenticated' if '_auth_user_id' in self.client.session else 'Not Authenticated')
        print('Request body:')
        print(json.dumps(data))
        response = self.client.post(path=path, data=data, content_type=content_type, follow=follow, secure=secure,
                                    **extra)
        print('Response status code: {}'.format(response.status_code))
        print('Response body:')
        if response.status_code not in (204, 404):
            print(json.dumps(response.data))
        return response

    def patch(self, path, data=None, content_type=None, follow=False, secure=False, **extra):
        print('***' * 15)
        print('PATCH {}'.format(path))
        print('Authenticated' if '_auth_user_id' in self.client.session else 'Not Authenticated')
        print('Request body:')
        print(json.dumps(data))
        response = self.client.patch(path=path, data=data, content_type=content_type, follow=follow, secure=secure,
                                     **extra)
        print('Response status code: {}'.format(response.status_code))
        print('Response body:')
        print(json.dumps(response.data))
        return response

    def put(self, path, data=None, content_type=None, follow=False, secure=False, **extra):
        print('***' * 15)
        print('PUT {}'.format(path))
        print('Authenticated' if '_auth_user_id' in self.client.session else 'Not Authenticated')
        print('Request body:')
        print(json.dumps(data))
        response = self.client.put(path=path, data=data, content_type=content_type, follow=follow, secure=secure,
                                   **extra)
        print('Response status code: {}'.format(response.status_code))
        print('Response body:')
        print(json.dumps(response.data))
        return response

    def delete(self, path, data=None, content_type=None, follow=False, secure=False, **extra):
        print('***' * 15)
        print('DELETE {}'.format(path))
        print('Authenticated' if '_auth_user_id' in self.client.session else 'Not Authenticated')
        print('Request body:')
        print(json.dumps(data))
        response = self.client.delete(path=path, data=data, content_type=content_type, follow=follow, secure=secure,
                                      **extra)
        print('Response status code: {}'.format(response.status_code))
        print('Response body:')
        print(json.dumps(response.data))
        return response


class TestCase(HTTPStatusTestCaseMixin, ClientHelperMixin, APITestCase):
    pass


class TransactionTestCase(HTTPStatusTestCaseMixin, ClientHelperMixin, APITransactionTestCase):
    pass
