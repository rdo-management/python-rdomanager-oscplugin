#   Copyright 2015 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

from unittest import TestCase

from collections import namedtuple
import mock

from rdomanager_oscplugin import exceptions
from rdomanager_oscplugin import utils


class TestPasswordsUtil(TestCase):
    def test_generate_passwords(self):

        passwords = utils.generate_overcloud_passwords()
        passwords2 = utils.generate_overcloud_passwords()

        self.assertEqual(len(passwords), 13)
        self.assertNotEqual(passwords, passwords2)


class TestCheckHypervisorUtil(TestCase):
    def test_check_hypervisor_stats(self):

        mock_compute = mock.Mock()
        mock_stats = mock.Mock()

        return_values = [
            {'count': 0, 'memory_mb': 0, 'vcpus': 0},
            {'count': 1, 'memory_mb': 1, 'vcpus': 1},
        ]

        mock_stats.to_dict.side_effect = return_values
        mock_compute.hypervisors.statistics.return_value = mock_stats

        stats = utils.check_hypervisor_stats(
            mock_compute, nodes=1, memory=1, vcpu=1)

        self.assertEqual(stats, None)
        self.assertEqual(mock_stats.to_dict.call_count, 1)

        stats = utils.check_hypervisor_stats(
            mock_compute, nodes=1, memory=1, vcpu=1)
        self.assertEqual(stats, return_values[-1])
        self.assertEqual(mock_stats.to_dict.call_count, 2)


class TestWaitForStackUtil(TestCase):
    def setUp(self):
        self.mock_orchestration = mock.Mock()
        self.mock_stacks = mock.MagicMock()
        self.stack_status = mock.PropertyMock()
        type(self.mock_stacks).stack_status = self.stack_status
        self.mock_orchestration.stacks.get.return_value = self.mock_stacks

    def test_wait_for_stack_ready(self):
        self.mock_orchestration.reset_mock()
        self.mock_stacks.reset_mock()

        return_values = [
            'CREATE_COMPLETE'
        ]

        self.stack_status.side_effect = return_values

        complete = utils.wait_for_stack_ready(self.mock_orchestration, 'stack')

        self.assertEqual(complete, True)

    def test_wait_for_stack_ready_no_stack(self):
        self.mock_orchestration.reset_mock()

        self.mock_orchestration.stacks.get.return_value = None

        complete = utils.wait_for_stack_ready(self.mock_orchestration, 'stack')

        self.mock_orchestration.stacks.get.return_value = self.mock_stacks

        self.assertEqual(complete, False)

    def test_wait_for_stack_ready_failed(self):
        self.mock_orchestration.reset_mock()
        self.mock_stacks.reset_mock()

        return_values = [
            'CREATE_FAILED'
        ]

        self.stack_status.side_effect = return_values

        complete = utils.wait_for_stack_ready(self.mock_orchestration, 'stack')

        self.assertEqual(complete, False)

    def test_wait_for_stack_ready_timeout(self):
        self.mock_orchestration.reset_mock()
        self.mock_stacks.reset_mock()

        return_values = [
            mock.Mock(stack_status='CREATE_RUNNING'),
            mock.Mock(stack_status='CREATE_RUNNING'),
            mock.Mock(stack_status='CREATE_RUNNING'),
            mock.Mock(stack_status='CREATE_RUNNING'),
            mock.Mock(stack_status='CREATE_COMPLETE')
        ]

        # self.stack_status.side_effect = return_values
        self.mock_orchestration.stacks.get.side_effect = return_values

        complete = utils.wait_for_stack_ready(
            self.mock_orchestration, 'stack', loops=4, sleep=0.1)

        self.assertEqual(complete, False)


class TestWaitForDiscovery(TestCase):

    def test_wait_for_discovery_success(self):

        mock_discoverd = mock.Mock()
        self.node_uuids = [
            'NODE1',
            'NODE2',
        ]

        mock_discoverd.get_status.return_value = {
            'finished': True,
            'error': None
        }

        result = utils.wait_for_node_discovery(mock_discoverd, "TOKEN",
                                               "URL", self.node_uuids,
                                               loops=4, sleep=0.01)

        self.assertEqual(list(result), [
            ('NODE1', {'error': None, 'finished': True}),
            ('NODE2', {'error': None, 'finished': True})
        ])

    def test_wait_for_discovery_partial_success(self):

        mock_discoverd = mock.Mock()
        self.node_uuids = [
            'NODE1',
            'NODE2',
        ]

        mock_discoverd.get_status.side_effect = [{
            'finished': True,
            'error': None
        }, {
            'finished': True,
            'error': "Failed"
        }]

        result = utils.wait_for_node_discovery(mock_discoverd, "TOKEN",
                                               "URL", self.node_uuids,
                                               loops=4, sleep=0.01)

        self.assertEqual(list(result), [
            ('NODE1', {'error': None, 'finished': True}),
            ('NODE2', {'error': "Failed", 'finished': True})
        ])

    def test_wait_for_discovery_timeout(self):

        mock_discoverd = mock.Mock()
        self.node_uuids = [
            'NODE1',
            'NODE2',
        ]

        mock_discoverd.get_status.return_value = {
            'finished': False,
            'error': None
        }

        result = utils.wait_for_node_discovery(mock_discoverd, "TOKEN",
                                               "URL", self.node_uuids,
                                               loops=4, sleep=0.01)

        self.assertEqual(list(result), [])

    def test_create_environment_file(self):

        json_file_path = "env.json"

        mock_open = mock.mock_open()

        with mock.patch('six.moves.builtins.open', mock_open):
            with mock.patch('json.dumps', return_value="JSON"):
                utils.create_environment_file(path=json_file_path)

                mock_open.assert_called_with('env.json', 'w+')

        mock_open().write.assert_called_with('JSON')

    @mock.patch('rdomanager_oscplugin.utils.wait_for_provision_state')
    def test_set_nodes_state(self, wait_for_state_mock):

        wait_for_state_mock.return_value = True
        bm_client = mock.Mock()

        # One node already deployed, one in the manageable state after
        # introspection.
        nodes = [
            mock.Mock(uuid="ABCDEFGH", provision_state="active"),
            mock.Mock(uuid="IJKLMNOP", provision_state="manageable")
        ]

        skipped_states = ('active', 'available')
        utils.set_nodes_state(bm_client, nodes, 'provide', 'available',
                              skipped_states)

        bm_client.node.set_provision_state.assert_has_calls([
            mock.call('IJKLMNOP', 'provide'),
        ])

    @mock.patch("subprocess.Popen")
    def test_get_hiera_key(self, mock_popen):

        process_mock = mock.Mock()
        process_mock.communicate.return_value = ["pa$$word", ""]
        mock_popen.return_value = process_mock

        value = utils.get_hiera_key('password_name')

        self.assertEqual(value, "pa$$word")

    def test_wait_for_provision_state(self):

        baremetal_client = mock.Mock()

        baremetal_client.node.get.return_value = mock.Mock(
            provision_state="available")

        result = utils.wait_for_provision_state(baremetal_client, 'UUID',
                                                "available")

        self.assertEqual(result, True)

    def test_wait_for_provision_state_not_found(self):

        baremetal_client = mock.Mock()

        baremetal_client.node.get.return_value = None

        result = utils.wait_for_provision_state(baremetal_client, 'UUID',
                                                "available")

        self.assertEqual(result, True)

    def test_wait_for_provision_state_fail(self):

        baremetal_client = mock.Mock()

        baremetal_client.node.get.return_value = mock.Mock(
            provision_state="not what we want")

        result = utils.wait_for_provision_state(baremetal_client, 'UUID',
                                                "available", loops=1,
                                                sleep=0.01)

        self.assertEqual(result, False)

    @mock.patch('subprocess.check_call')
    @mock.patch('os.path.exists')
    def test_remove_known_hosts(self, mock_exists, mock_check_call):

        mock_exists.return_value = True

        utils.remove_known_hosts('192.168.0.1')

        mock_check_call.assert_called_with(['ssh-keygen', '-R', '192.168.0.1'])

    @mock.patch('subprocess.check_call')
    @mock.patch('os.path.exists')
    def test_remove_known_hosts_no_file(self, mock_exists, mock_check_call):

        mock_exists.return_value = False

        utils.remove_known_hosts('192.168.0.1')

        mock_check_call.assert_not_called()


class TestRegisterEndpoint(TestCase):
    def setUp(self):
        self.mock_identity = mock.Mock()

        Project = namedtuple('Project', 'id name')
        self.mock_identity.projects.list.return_value = [
            Project(id='123', name='service'),
            Project(id='234', name='admin')
        ]

        def _role_list_side_effect(*args, **kwargs):
            Role = namedtuple('Role', 'id name')
            user = kwargs.get('user')
            project = kwargs.get('project')

            if user and project:
                return Role(id='123', name='admin')
            else:
                return [
                    Role(id='123', name='admin'),
                    Role(id='345', name='ResellerAdmin'),
                ]
        self.mock_identity.roles.list.side_effect = _role_list_side_effect

        User = namedtuple('User', 'id name')
        self.mock_identity.users.list.return_value = [
            User(id='123', name='nova')
        ]

        self.services_create_mock = mock.Mock()
        self.mock_identity.services.create.return_value = (
            self.services_create_mock)

        self.endpoints_create_mock = mock.Mock()
        self.mock_identity.endpoints.create.return_value = (
            self.endpoints_create_mock)

        self.users_create_mock = mock.Mock()
        self.mock_identity.users.create.return_value = (
            self.users_create_mock)

    def test_unknown_service(self):
        self.mock_identity.reset_mock()

        self.assertRaises(exceptions.UnknownService,
                          utils.register_endpoint,
                          'unknown_name',
                          'unknown_endpoint_type',
                          'unknown_url',
                          self.mock_identity)

    def test_no_admin_role(self):
        local_mock_identity = mock.Mock()
        local_mock_identity.roles.list.return_value = []
        self.assertRaises(exceptions.NotFound,
                          utils.register_endpoint,
                          'name',
                          'compute',
                          'url',
                          local_mock_identity)

    def test_endpoint_is_dashboard(self):
        self.mock_identity.reset_mock()

        utils.register_endpoint(
            'name',
            'dashboard',
            'url',
            self.mock_identity,
            description='description'
        )

        self.mock_identity.roles.list.assert_called_once_with()

        self.mock_identity.services.create.assert_called_once_with(
            name='name',
            type='dashboard',
            description='description',
            enabled=True
        )

        self.mock_identity.endpoints.create.assert_called_once_with(
            'regionOne',
            self.services_create_mock.id,
            "url/",
            "url/admin",
            "url/"
        )

    def test_endpoint_is_not_dashboard(self):
        self.mock_identity.reset_mock()

        utils.register_endpoint(
            'nova',
            'compute',
            'url',
            self.mock_identity,
            description='description'
        )

        assert not self.mock_identity.users.create.called
        self.mock_identity.users.list.assert_called_once_with()

        self.mock_identity.projects.list.assert_called_once_with()

        self.mock_identity.roles.list.assert_has_calls([
            mock.call(),
            mock.call(user='123', project='123')
        ])

        self.mock_identity.services.create.assert_called_once_with(
            name='nova',
            type='compute',
            description='description',
            enabled=True
        )

        self.mock_identity.endpoints.create.assert_called_once_with(
            'regionOne',
            self.services_create_mock.id,
            "url/v2/$(tenant_id)s",
            "url/v2/$(tenant_id)s",
            "url/v2/$(tenant_id)s"
        )

    def test_endpoint_is_metering(self):
        self.mock_identity.reset_mock()

        utils.register_endpoint(
            'ceilometer',
            'metering',
            'url',
            self.mock_identity,
            description='description',
            password='password'
        )

        self.mock_identity.users.list.assert_called_once_with()

        self.mock_identity.users.create.assert_called_once_with(
            name='ceilometer',
            domain=None,
            default_project='123',
            password='password',
            email='nobody@example.com',
            description=None,
            enabled=True
        )
        self.mock_identity.services.create.assert_called_once_with(
            name='ceilometer',
            type='metering',
            description='description',
            enabled=True
        )

        self.mock_identity.endpoints.create.assert_called_once_with(
            'regionOne',
            self.services_create_mock.id,
            "url/",
            "url/",
            "url/"
        )

        self.mock_identity.roles.list.assert_has_calls([
            mock.call(),
            mock.call(user=self.users_create_mock.id, project='123'),
            mock.call(user=self.users_create_mock.id, project='234'),
        ])

        self.mock_identity.projects.list.assert_called_once_with()
