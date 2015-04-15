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

import mock

from heatclient.exc import HTTPNotFound

from rdomanager_oscplugin.tests.v1.overcloud_deploy import fakes
from rdomanager_oscplugin.v1 import overcloud_deploy


class TestDeployOvercloud(fakes.TestDeployOvercloud):

    def setUp(self):
        super(TestDeployOvercloud, self).setUp()

        # Get the command object to test
        self.cmd = overcloud_deploy.OvercloudDeploy(self.app, None)

    @mock.patch('rdomanager_oscplugin.utils.wait_for_stack_ready')
    @mock.patch('rdomanager_oscplugin.utils.set_nodes_state')
    @mock.patch('heatclient.common.template_utils.'
                'process_multiple_environments_and_files')
    @mock.patch('heatclient.common.template_utils.get_template_contents')
    @mock.patch('os_cloud_config.keystone_pki.generate_certs_into_json')
    @mock.patch('rdomanager_oscplugin.utils.create_environment_file')
    @mock.patch('rdomanager_oscplugin.utils.get_heira_password')
    @mock.patch('rdomanager_oscplugin.utils.check_hypervisor_stats')
    def test_deploy(self, mock_check_hypervisor_stats, mock_get_password,
                    mock_create_env, generate_certs_mock,
                    mock_get_templte_contents, mock_process_multiple_env,
                    set_nodes_state_mock, wait_for_stack_ready_mock):

        clients = self.app.client_manager
        orchestration_client = clients.rdomanager_oscplugin.orchestration()
        orchestration_client.stacks.get.side_effect = HTTPNotFound

        mock_check_hypervisor_stats.return_value = {
            'count': 4,
            'memory_mb': 4096,
            'vcpus': 8,
        }
        mock_get_password.return_value = "PASSWORD"
        clients.network.api.find_attr.return_value = {
            "id": "network id"
        }
        mock_create_env.return_value = "/fake/path"
        mock_process_multiple_env.return_value = [{}, "env"]
        mock_get_templte_contents.return_value = [{}, "template"]
        wait_for_stack_ready_mock.return_value = True

        parsed_args = self.check_parser(self.cmd, [], [])

        self.cmd.take_action(parsed_args)

        args, kwargs = orchestration_client.stacks.create.call_args

        self.assertEqual(args, ())

        # The parameters output contains lots of output and some in random.
        # So lets just check that it is present
        self.assertTrue('parameters' in kwargs)

        self.assertEqual(kwargs['files'], {})
        self.assertEqual(kwargs['template'], 'template')
        self.assertEqual(kwargs['environment'], 'env')
        self.assertEqual(kwargs['stack_name'], 'overcloud')
