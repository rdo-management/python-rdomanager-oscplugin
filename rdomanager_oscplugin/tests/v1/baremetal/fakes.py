import mock

from openstackclient.tests import fakes
from openstackclient.tests import utils


class FakeBaremetalClient(object):
    def __init__(self, **kwargs):
        self.import_ = mock.Mock()
        self.import_.resource_class = fakes.FakeResource(None, {})
        self.auth_token = kwargs['token']
        self.management_url = kwargs['endpoint']


class TestBaremetal(utils.TestCommand):

    def setUp(self):
        super(TestBaremetal, self).setUp()

        self.app.client_manager.baremetal = FakeBaremetalClient(
            endpoint=fakes.AUTH_URL,
            token=fakes.AUTH_TOKEN,
        )
