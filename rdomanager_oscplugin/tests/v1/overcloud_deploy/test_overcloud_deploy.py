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

from tuskarclient.v2.plans import Plan

from rdomanager_oscplugin.tests.v1.overcloud_deploy import fakes
from rdomanager_oscplugin.tests.v1.utils import (
    generate_overcloud_passwords_mock)
from rdomanager_oscplugin.v1 import overcloud_deploy


class TestDeployOvercloud(fakes.TestDeployOvercloud):

    def setUp(self):
        super(TestDeployOvercloud, self).setUp()

        # Get the command object to test
        self.cmd = overcloud_deploy.DeployOvercloud(self.app, None)

        self._get_passwords = generate_overcloud_passwords_mock

    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_deploy_postconfig')
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_update_nodesjson')
    @mock.patch('rdomanager_oscplugin.utils.get_config_value', autospec=True)
    @mock.patch('rdomanager_oscplugin.utils.generate_overcloud_passwords')
    @mock.patch('heatclient.common.template_utils.'
                'process_multiple_environments_and_files')
    @mock.patch('heatclient.common.template_utils.get_template_contents')
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_get_stack')
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_pre_heat_deploy')
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_create_overcloudrc')
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_heat_deploy')
    def test_tuskar_deploy(self, mock_heat_deploy, mock_create_overcloudrc,
                           most_pre_deploy, mock_get_stack,
                           mock_get_templte_contents,
                           mock_process_multiple_env,
                           mock_generate_overcloud_passwords,
                           mock_get_key, mock_update_nodesjson,
                           mock_deploy_postconfig):

        arglist = ['--plan', 'undercloud', '--output-dir', 'fake',
                   '--compute-flavor', 'baremetal',
                   '--neutron-bridge-mappings', 'datacentre:br-test',
                   '--neutron-disable-tunneling',
                   '--control-scale', '3',
                   '--neutron-mechanism-drivers', 'linuxbridge']

        verifylist = [
            ('plan', 'undercloud'),
            ('output_dir', 'fake'),
        ]

        clients = self.app.client_manager
        management = clients.rdomanager_oscplugin.management()

        management.plans.templates.return_value = {}
        management.plans.resource_class = Plan

        mock_plan = mock.Mock()
        mock_plan.configure_mock(name="undercloud")
        management.plans.list.return_value = [mock_plan, ]

        mock_get_templte_contents.return_value = ({}, "template")
        mock_process_multiple_env.return_value = ({}, "envs")
        clients.network.api.find_attr.return_value = {
            "id": "network id"
        }

        mock_get_key.return_value = "PASSWORD"

        mock_generate_overcloud_passwords.return_value = self._get_passwords()

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.cmd.take_action(parsed_args)

        parameters = {
            'Controller-1::SnmpdReadonlyUserPassword': "PASSWORD",
            'Compute-1::NeutronPassword': 'password',
            'Controller-1::NeutronPassword': 'password',
            'Cinder-Storage-1::SnmpdReadonlyUserPassword': "PASSWORD",
            'Compute-1::CeilometerMeteringSecret': 'password',
            'NeutronControlPlaneID': 'network id',
            'Compute-1::NeutronBridgeMappings': 'datacentre:br-test',
            'Controller-1::AdminPassword': 'password',
            'Compute-1::Flavor': 'baremetal',
            'Compute-1::SnmpdReadonlyUserPassword': "PASSWORD",
            'Controller-1::NeutronEnableTunnelling': False,
            'Compute-1::NeutronEnableTunnelling': False,
            'Controller-1::count': 3,
            'Compute-1::CeilometerPassword': 'password',
            'Controller-1::CinderPassword': 'password',
            'Controller-1::CeilometerPassword': 'password',
            'Compute-1::AdminPassword': 'password',
            'Controller-1::HeatPassword': 'password',
            'Controller-1::HeatStackDomainAdminPassword': 'password',
            'Controller-1::CeilometerMeteringSecret': 'password',
            'Controller-1::SwiftPassword': 'password',
            'Controller-1::NeutronBridgeMappings': 'datacentre:br-test',
            'Controller-1::NovaPassword': 'password',
            'Controller-1::SwiftHashSuffix': 'password',
            'Compute-1::NovaPassword': 'password',
            'Controller-1::GlancePassword': 'password',
            'Swift-Storage-1::SnmpdReadonlyUserPassword': "PASSWORD",
            'Controller-1::AdminToken': 'password',
            'Controller-1::NeutronL3HA': True,
            'Controller-1::NeutronAllowL3AgentFailover': False,
            'Compute-1::NeutronL3HA': True,
            'Compute-1::NeutronAllowL3AgentFailover': False,
            'Controller-1::NeutronMechanismDrivers': 'linuxbridge',
            'Compute-1::NeutronMechanismDrivers': 'linuxbridge',
        }

        mock_heat_deploy.assert_called_with(
            mock_get_stack(),
            'fake/plan.yaml',
            parameters,
            ['fake/environment.yaml']
        )

    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_deploy_postconfig')
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_update_nodesjson')
    @mock.patch('rdomanager_oscplugin.utils.get_config_value', autospec=True)
    @mock.patch('rdomanager_oscplugin.utils.generate_overcloud_passwords')
    @mock.patch('heatclient.common.template_utils.'
                'process_multiple_environments_and_files')
    @mock.patch('heatclient.common.template_utils.get_template_contents')
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_get_stack')
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_pre_heat_deploy')
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_create_overcloudrc')
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_heat_deploy')
    def test_tuskar_deploy_extra_config(self, mock_heat_deploy,
                                        mock_create_overcloudrc,
                                        most_pre_deploy, mock_get_stack,
                                        mock_get_templte_contents,
                                        mock_process_multiple_env,
                                        mock_generate_overcloud_passwords,
                                        mock_get_key, mock_update_nodesjson,
                                        mock_deploy_postconfig):

        arglist = ['--plan', 'undercloud', '--output-dir', 'fake',
                   '--compute-flavor', 'baremetal',
                   '--neutron-bridge-mappings', 'datacentre:br-test',
                   '--neutron-disable-tunneling',
                   '--control-scale', '3',
                   '-e', 'extra_registry.yaml',
                   '-e', 'extra_environment.yaml']

        verifylist = [
            ('plan', 'undercloud'),
            ('output_dir', 'fake'),
            ('extra_templates', ['extra_registry.yaml',
                                 'extra_environment.yaml'])
        ]

        clients = self.app.client_manager
        management = clients.rdomanager_oscplugin.management()

        management.plans.templates.return_value = {}
        management.plans.resource_class = Plan

        mock_plan = mock.Mock()
        mock_plan.configure_mock(name="undercloud")
        management.plans.list.return_value = [mock_plan, ]

        mock_get_templte_contents.return_value = ({}, "template")
        mock_process_multiple_env.return_value = ({}, "envs")
        clients.network.api.find_attr.return_value = {
            "id": "network id"
        }

        mock_get_key.return_value = "PASSWORD"

        mock_generate_overcloud_passwords.return_value = self._get_passwords()

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.cmd.take_action(parsed_args)

        parameters = {
            'Controller-1::SnmpdReadonlyUserPassword': "PASSWORD",
            'Compute-1::NeutronPassword': 'password',
            'Controller-1::NeutronPassword': 'password',
            'Cinder-Storage-1::SnmpdReadonlyUserPassword': "PASSWORD",
            'Compute-1::CeilometerMeteringSecret': 'password',
            'NeutronControlPlaneID': 'network id',
            'Compute-1::NeutronBridgeMappings': 'datacentre:br-test',
            'Controller-1::AdminPassword': 'password',
            'Compute-1::Flavor': 'baremetal',
            'Compute-1::SnmpdReadonlyUserPassword': "PASSWORD",
            'Controller-1::NeutronEnableTunnelling': False,
            'Compute-1::NeutronEnableTunnelling': False,
            'Controller-1::count': 3,
            'Compute-1::CeilometerPassword': 'password',
            'Controller-1::CinderPassword': 'password',
            'Controller-1::CeilometerPassword': 'password',
            'Compute-1::AdminPassword': 'password',
            'Controller-1::HeatPassword': 'password',
            'Controller-1::HeatStackDomainAdminPassword': 'password',
            'Controller-1::CeilometerMeteringSecret': 'password',
            'Controller-1::SwiftPassword': 'password',
            'Controller-1::NeutronBridgeMappings': 'datacentre:br-test',
            'Controller-1::NovaPassword': 'password',
            'Controller-1::SwiftHashSuffix': 'password',
            'Compute-1::NovaPassword': 'password',
            'Controller-1::GlancePassword': 'password',
            'Swift-Storage-1::SnmpdReadonlyUserPassword': "PASSWORD",
            'Controller-1::AdminToken': 'password',
            'Controller-1::NeutronL3HA': True,
            'Controller-1::NeutronAllowL3AgentFailover': False,
            'Compute-1::NeutronL3HA': True,
            'Compute-1::NeutronAllowL3AgentFailover': False,
        }

        mock_heat_deploy.assert_called_with(
            mock_get_stack(),
            'fake/plan.yaml',
            parameters,
            ['fake/environment.yaml',
             'extra_registry.yaml',
             'extra_environment.yaml']
        )

    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_deploy_tuskar', autospec=True)
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_deploy_tripleo_heat_templates', autospec=True)
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_pre_heat_deploy', autospec=True)
    def test_missing_sat_url(self, mock_pre_deploy, mock_deploy_tht,
                             mock_deploy_tuskar):

        arglist = ['--plan', 'undercloud', '--rhel-reg',
                   '--reg-method', 'satellite', '--reg-org', '123456789',
                   '--reg-activation-key', 'super-awesome-key']
        verifylist = [
            ('rhel_reg', True),
            ('reg_method', 'satellite'),
            ('reg_org', '123456789'),
            ('reg_activation_key', 'super-awesome-key')
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        self.cmd.take_action(parsed_args)
        self.assertFalse(mock_deploy_tht.called)
        self.assertFalse(mock_deploy_tuskar.called)

    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_update_nodesjson', autospec=True)
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_create_overcloudrc', autospec=True)
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_get_overcloud_endpoint', autospec=True)
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_deploy_tuskar', autospec=True)
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_deploy_tripleo_heat_templates', autospec=True)
    @mock.patch('rdomanager_oscplugin.v1.overcloud_deploy.DeployOvercloud.'
                '_pre_heat_deploy', autospec=True)
    def test_rhel_reg_params_provided(self, mock_pre_deploy, mock_deploy_tht,
                                      mock_deploy_tuskar, mock_oc_endpoint,
                                      mock_create_ocrc, mock_update_njson):

        arglist = ['--plan', 'undercloud', '--rhel-reg',
                   '--reg-sat-url', 'https://example.com',
                   '--reg-method', 'satellite', '--reg-org', '123456789',
                   '--reg-activation-key', 'super-awesome-key']
        verifylist = [
            ('rhel_reg', True),
            ('reg_sat_url', 'https://example.com'),
            ('reg_method', 'satellite'),
            ('reg_org', '123456789'),
            ('reg_activation_key', 'super-awesome-key')
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        self.cmd.take_action(parsed_args)
        self.assertFalse(mock_deploy_tht.called)
        self.assertTrue(mock_oc_endpoint.called)
        self.assertTrue(mock_create_ocrc.called)
        self.assertTrue(mock_update_njson.called)
        self.assertTrue(mock_deploy_tuskar.called)
