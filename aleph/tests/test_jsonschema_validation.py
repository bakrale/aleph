from werkzeug.exceptions import BadRequest

from aleph.tests.util import TestCase
from aleph.views.util import validate


class SchemaValidationTest(TestCase):

    def test_role_schema(self):
        data = {
            "name": "sunu",
            "is_muted": True,
            "password": "very-secret-password",
            "current_password": "secret-password",
            "locale": "en-us",
        }
        with self.assertRaises(BadRequest):
            validate(data, 'RoleUpdate')
