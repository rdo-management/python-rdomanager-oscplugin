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
from __future__ import print_function

import logging
import os
import six
import sys
import tempfile
import uuid

from cliff import command
from heatclient.common import template_utils
from heatclient.exc import HTTPNotFound
from keystoneclient import exceptions as ksc_exc
from openstackclient.i18n import _
from os_cloud_config import keystone
from os_cloud_config import keystone_pki

from rdomanager_oscplugin import utils

TRIPLEO_HEAT_TEMPLATES = "/usr/share/openstack-tripleo-heat-templates/"
OVERCLOUD_YAML_PATH = os.path.join(TRIPLEO_HEAT_TEMPLATES,
                                   "overcloud-without-mergepy.yaml")
RESOURCE_REGISTRY_PATH = os.path.join(
    TRIPLEO_HEAT_TEMPLATES, "overcloud-resource-registry-puppet.yaml")

PARAMETERS = {
    'AdminPassword': None,
    'AdminToken': None,
    'CeilometerPassword': None,
    'CeilometerMeteringSecret': None,
    'CinderPassword': None,
    'CinderISCSIHelper': 'lioadm',
    'CloudName': 'overcloud',
    'ExtraConfig': '{}',
    'GlancePassword': None,
    'HeatPassword': None,
    'NeutronControlPlaneID': None,
    'NeutronDnsmasqOptions': 'dhcp-option-force=26,1400',
    'NeutronPassword': None,
    'NeutronPublicInterface': 'nic1',
    'NeutronFlatNetworks': 'datacentre',
    'HypervisorNeutronPhysicalBridge': 'br-ex',
    'NeutronBridgeMappings': 'datacentre:br-ex',
    'HypervisorNeutronPublicInterface': 'nic1',
    'NovaComputeLibvirtType': 'qemu',
    'NovaPassword': None,
    'SwiftHashSuffix': None,
    'SwiftPassword': None,
    'NeutronNetworkType': 'gre',
    'NeutronTunnelTypes': 'gre',
    'SnmpdReadonlyUserPassword': None,
    'OvercloudControlFlavor': 'baremetal',
    'OvercloudComputeFlavor': 'baremetal',
    'OvercloudBlockStorageFlavor': 'baremetal',
    'OvercloudSwiftStorageFlavor': 'baremetal',
    'OvercloudCephStorageFlavor': 'baremetal',
    'NtpServer': '',
    'controllerImage': 'overcloud-full',
    'NovaImage': 'overcloud-full',
    'BlockStorageImage': 'overcloud-full',
    'SwiftStorageImage': 'overcloud-full',
    'CephStorageImage': 'overcloud-full',
    'Debug': 'True',
}


class DeployOvercloud(command.Command):
    """Deploy Overcloud"""

    log = logging.getLogger(__name__ + ".DeployOvercloud")

    def set_overcloud_passwords(self, parameters, parsed_args):
        """Add passwords to the parameters dictionary

        :param parameters: A dictionary for the passwords to be added to
        :type parameters: dict
        """

        self.passwords = passwords = utils.generate_overcloud_passwords()
        ceilometer_pass = passwords['OVERCLOUD_CEILOMETER_PASSWORD']
        ceilometer_secret = passwords['OVERCLOUD_CEILOMETER_SECRET']
        if parsed_args.use_tht:
            parameters['AdminPassword'] = passwords['OVERCLOUD_ADMIN_PASSWORD']
            parameters['AdminToken'] = passwords['OVERCLOUD_ADMIN_TOKEN']
            parameters['CeilometerPassword'] = ceilometer_pass
            parameters['CeilometerMeteringSecret'] = ceilometer_secret
            parameters['CinderPassword'] = passwords[
                'OVERCLOUD_CINDER_PASSWORD']
            parameters['GlancePassword'] = passwords[
                'OVERCLOUD_GLANCE_PASSWORD']
            parameters['HeatPassword'] = passwords['OVERCLOUD_HEAT_PASSWORD']
            parameters['NeutronPassword'] = passwords[
                'OVERCLOUD_NEUTRON_PASSWORD']
            parameters['NovaPassword'] = passwords['OVERCLOUD_NOVA_PASSWORD']
            parameters['SwiftHashSuffix'] = passwords['OVERCLOUD_SWIFT_HASH']
            parameters['SwiftPassword'] = passwords['OVERCLOUD_SWIFT_PASSWORD']
        else:
            parameters['Controller-1::AdminPassword'] = passwords[
                'OVERCLOUD_ADMIN_PASSWORD']
            parameters['Controller-1::AdminToken'] = passwords[
                'OVERCLOUD_ADMIN_TOKEN']
            parameters['Compute-1::AdminPassword'] = passwords[
                'OVERCLOUD_ADMIN_PASSWORD']
            parameters['Controller-1::SnmpdReadonlyUserPassword'] = (
                parsed_args.undercloud_ceilometer_snmpd_password)
            parameters['Cinder-Storage-1::SnmpdReadonlyUserPassword'] = (
                parsed_args.undercloud_ceilometer_snmpd_password)
            parameters['Swift-Storage-1::SnmpdReadonlyUserPassword'] = (
                parsed_args.undercloud_ceilometer_snmpd_password)
            parameters['Compute-1::SnmpdReadonlyUserPassword'] = (
                parsed_args.undercloud_ceilometer_snmpd_password)
            parameters['Controller-1::CeilometerPassword'] = ceilometer_pass
            parameters[
                'Controller-1::CeilometerMeteringSecret'] = ceilometer_secret
            parameters['Compute-1::CeilometerPassword'] = ceilometer_pass
            parameters[
                'Compute-1::CeilometerMeteringSecret'] = ceilometer_secret
            parameters['Controller-1::CinderPassword'] = (
                passwords['OVERCLOUD_CINDER_PASSWORD'])
            parameters['Controller-1::GlancePassword'] = (
                passwords['OVERCLOUD_GLANCE_PASSWORD'])
            parameters['Controller-1::HeatPassword'] = (
                passwords['OVERCLOUD_HEAT_PASSWORD'])
            parameters['Controller-1::NeutronPassword'] = (
                passwords['OVERCLOUD_NEUTRON_PASSWORD'])
            parameters['Compute-1::NeutronPassword'] = (
                passwords['OVERCLOUD_NEUTRON_PASSWORD'])
            parameters['Controller-1::NovaPassword'] = (
                passwords['OVERCLOUD_NOVA_PASSWORD'])
            parameters['Compute-1::NovaPassword'] = (
                passwords['OVERCLOUD_NOVA_PASSWORD'])
            parameters['Controller-1::SwiftHashSuffix'] = (
                passwords['OVERCLOUD_SWIFT_HASH'])
            parameters['Controller-1::SwiftPassword'] = (
                passwords['OVERCLOUD_SWIFT_PASSWORD'])
            parameters['Controller-1::CinderISCSIHelper'] = 'lioadm'
            parameters['Cinder-Storage-1::CinderISCSIHelper'] = 'lioadm'
            parameters['Controller-1::CloudName'] = 'overcloud'
            parameters['Controller-1::NeutronPublicInterface'] = (
                parsed_args.neutron_public_interface)
            parameters['Controller-1::NeutronBridgeMappings'] = (
                parsed_args.neutron_bridge_mappings)
            parameters['Compute-1::NeutronBridgeMappings'] = (
                parsed_args.neutron_bridge_mappings)
            parameters['Controller-1::NeutronFlatNetworks'] = (
                parsed_args.neutron_flat_networks)
            parameters['Compute-1::NeutronFlatNetworks'] = (
                parsed_args.neutron_flat_networks)
            parameters['Compute-1::NeutronPhysicalBridge'] = (
                parsed_args.neutron_physical_bridge)
            parameters['Compute-1::NeutronPublicInterface'] = (
                parsed_args.neutron_public_interface)
            parameters['Compute-1::NovaComputeLibvirtType'] = (
                parsed_args.libvirt_type)
            parameters['Controller-1::NtpServer'] = parsed_args.ntp_server
            parameters['Compute-1::NtpServer'] = parsed_args.ntp_server
            parameters['Controller-1::NeutronNetworkType'] = (
                parsed_args.neutron_network_type)
            parameters['Compute-1::NeutronNetworkType'] = (
                parsed_args.neutron_network_type)
            parameters['Controller-1::NeutronTunnelTypes'] = (
                parsed_args.neutron_tunnel_types)
            parameters['Compute-1::NeutronTunnelTypes'] = (
                parsed_args.neutron_tunnel_types)
            parameters['Controller-1::count'] = parsed_args.control_scale
            parameters['Compute-1::count'] = parsed_args.compute_scale
            parameters['Swift-Storage-1::count'] = (
                parsed_args.swift_storage_scale)
            parameters['Cinder-Storage-1::count'] = (
                parsed_args.block_storage_scale)
            parameters['Ceph-Storage-1::count'] = (
                parsed_args.ceph_storage_scale)
            parameters['Cinder-Storage-1::Flavor'] = 'baremetal'
            parameters['Compute-1::Flavor'] = 'baremetal'
            parameters['Controller-1::Flavor'] = 'baremetal'
            parameters['Swift-Storage-1::Flavor'] = 'baremetal'
            parameters['Ceph-Storage-1::Flavor'] = 'baremetal'
            parameters['Swift-Storage-1::Image'] = 'overcloud-full'
            parameters['Cinder-Storage-1::Image'] = 'overcloud-full'
            parameters['Ceph-Storage-1::Image'] = 'overcloud-full'
            parameters['Controller-1::Image'] = 'overcloud-full'
            parameters['Compute-1::Image'] = 'overcloud-full'

    def _get_stack(self, orchestration_client):
        """Get the ID for the current deployed overcloud stack if it exists."""

        try:
            stack = orchestration_client.stacks.get('overcloud')
            self.log.info("Stack found, will be doing a stack update")
            return stack
        except HTTPNotFound:
            self.log.info("No stack found, will be doing a stack create")

    def _update_paramaters(self, args, network_client):

        parameters = PARAMETERS.copy()

        snmp_pass = utils.get_hiera_key("snmpd_readonly_user_password")
        parameters['SnmpdReadonlyUserPassword'] = snmp_pass

        self.log.debug("Generating overcloud passwords")
        self.set_overcloud_passwords(parameters, args)

        self.log.debug("Getting ctlplane from Neutron")

        net = network_client.api.find_attr('networks', 'ctlplane')
        parameters['NeutronControlPlaneID'] = net['id']

        if args.control_scale > 1:
            if args.use_tht:
                parameters['NeutronL3HA'] = True
            else:
                parameters.update({
                    'Controller-1::NeutronL3HA': True,
                    'Controller-1::NeutronAllowL3AgentFailover': False,
                    'Compute-1::NeutronL3HA': True,
                    'Controller-1::NeutronAllowL3AgentFailover': False,
                })

        if args.ceph_storage_scale > 0:
            parameters.update({
                'CephClusterFSID': six.text_type(uuid.uuid1()),
                'CephMonKey': utils.create_cephx_key(),
                'CephAdminKey': utils.create_cephx_key()
            })

            if args.use_tht:
                parameters.update({
                    'CinderEnableRbdBackend': True,
                    'NovaEnableRbdBackend': True,
                })
            else:
                parameters.update({
                    'Controller-1::CinderEnableRbdBackend': True,
                    'Controller-1::GlanceBackend': 'rbd',
                    'Compute-1::NovaEnableRbdBackend': True,
                    'Controller-1::CinderEnableIscsiBackend': True
                })

        return parameters

    def _heat_deploy(self, stack, template_path, parameters, environments):
        """Verify the Baremetal nodes are available and do a stack update"""

        self.log.debug("Processing environment files")
        env_files, env = (
            template_utils.process_multiple_environments_and_files(
                environments))

        self.log.debug("Getting template contents")
        template_files, template = template_utils.get_template_contents(
            template_path)

        files = dict(list(template_files.items()) + list(env_files.items()))

        clients = self.app.client_manager
        orchestration_client = clients.rdomanager_oscplugin.orchestration()
        baremetal_client = clients.rdomanager_oscplugin.baremetal()

        self.log.debug("Verifying that Baremetal nodes to available or active")
        utils.set_nodes_state(
            baremetal_client, baremetal_client.node.list(),
            'provide', 'available', skipped_states=("available", "active"))

        stack_name = "overcloud"

        self.log.debug("Deploying stack: %s", stack_name)
        self.log.debug("Deploying template: %s", template)
        self.log.debug("Deploying parameters: %s", parameters)
        self.log.debug("Deploying environment: %s", env)
        self.log.debug("Deploying files: %s", files)

        stack_args = {
            'stack_name': stack_name,
            'template': template,
            'parameters': parameters,
            'environment': env,
            'files': files
        }

        if stack is None:
            self.log.info("Performing Heat stack create")
            orchestration_client.stacks.create(**stack_args)
        else:
            self.log.info("Performing Heat stack update")
            orchestration_client.stacks.update(stack.id, **stack_args)

        create_result = utils.wait_for_stack_ready(
            orchestration_client, "overcloud")
        if not create_result:
            if stack is None:
                raise Exception("Heat Stack create failed.")
            else:
                raise Exception("Heat Stack update failed.")

    def _get_overcloud_endpoint(self, stack):
        for output in stack.to_dict().get('outputs', {}):
            if output['output_key'] == 'KeystoneURL':
                return output['output_value']

    def _pre_heat_deploy(self):
        """Setup before the Heat stack create or update has been done."""
        clients = self.app.client_manager
        compute_client = clients.compute

        self.log.debug("Checking hypervisor stats")
        if utils.check_hypervisor_stats(compute_client) is None:
            print("Expected hypervisor stats not met", file=sys.stderr)
            return

    def _deploy_tripleo_heat_templates(self, stack, parsed_args):
        """Deploy the fixed templates in TripleO Heat Templates"""
        clients = self.app.client_manager
        network_client = clients.network

        parameters = self._update_paramaters(parsed_args, network_client)

        self.log.debug("Creating Environment file")
        env_path = utils.create_environment_file()

        if stack is None:
            self.log.debug("Creating Keystone certificates")
            keystone_pki.generate_certs_into_json(env_path, False)

        self._heat_deploy(stack, OVERCLOUD_YAML_PATH, parameters,
                          [RESOURCE_REGISTRY_PATH, env_path])

    def _deploy_tuskar(self, stack, parsed_args):

        clients = self.app.client_manager
        management = clients.rdomanager_oscplugin.management()

        # TODO(dmatthews): The Tuskar client has very similar code to this. It
        # should be refactored upstream so we can use it.

        if parsed_args.output_dir:
            output_dir = parsed_args.output_dir
        else:
            output_dir = tempfile.mkdtemp()

        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)

        # retrieve templates
        templates = management.plans.templates(parsed_args.plan_uuid)

        # write file for each key-value in templates
        print("The following templates will be written:")
        for template_name, template_content in templates.items():

            # It's possible to organize the role templates and their dependent
            # files into directories, in which case the template_name will
            # carry the directory information. If that's the case, first
            # create the directory structure (if it hasn't already been
            # created by another file in the templates list).
            template_dir = os.path.dirname(template_name)
            output_template_dir = os.path.join(output_dir, template_dir)
            if template_dir and not os.path.exists(output_template_dir):
                os.makedirs(output_template_dir)

            filename = os.path.join(output_dir, template_name)
            with open(filename, 'w+') as template_file:
                template_file.write(template_content)
            print(filename)

        overcloud_yaml = os.path.join(output_dir, 'plan.yaml')
        environment_yaml = os.path.join(output_dir, 'environment.yaml')

        self._heat_deploy(stack, overcloud_yaml, None, [environment_yaml, ])

    def _post_heat_deploy(self):
        """Setup after the Heat stack create or update has been done."""

        clients = self.app.client_manager
        orchestration_client = clients.rdomanager_oscplugin.orchestration()
        stack = self._get_stack(orchestration_client)
        identity_client = self.app.client_manager.identity

        overcloud_endpoint = self._get_overcloud_endpoint(stack)
        overcloud_ip = six.moves.urllib.parse.urlparse(
            overcloud_endpoint).hostname
        utils.remove_known_hosts(overcloud_ip)

        # TODO(dmatthews): Update os-cloud-config so that we don't need to
        # copy all the defaults from their CLI parser. They force us to pass
        # all values.
        keystone.initialize(
            overcloud_ip, self.passwords['OVERCLOUD_ADMIN_TOKEN'],
            'admin.example.com', self.passwords['OVERCLOUD_ADMIN_PASSWORD'],
            'regionOne', None, None, 'heat-admin', 600, 10, True)

        try:
            identity_client.roles.create(name='swiftoperator')
        except ksc_exc.Conflict:
            pass

        try:
            identity_client.roles.create(name='ResellerAdmin')
        except ksc_exc.Conflict:
            pass

        utils.setup_endpoints(overcloud_ip, self.passwords, identity_client)

        try:
            identity_client.roles.create(name='heat_stack_user')
        except ksc_exc.Conflict:
            pass

    def get_parser(self, prog_name):
        parser = super(DeployOvercloud, self).get_parser(prog_name)
        parser.add_argument('--control-scale', type=int, default=1)
        parser.add_argument('--compute-scale', type=int, default=1)
        parser.add_argument('--ceph-storage-scale', type=int, default=0)
        parser.add_argument('--block-storage-scale', type=int, default=0)
        parser.add_argument('--swift-storage-scale', type=int, default=0)
        parser.add_argument('--use-tripleo-heat-templates',
                            dest='use_tht', action='store_true')
        parser.add_argument('--neutron-flat-networks', default='datacentre')
        parser.add_argument('--neutron-physical-bridge', default='br-ex')
        parser.add_argument('--neutron-bridge-mappings',
                            default='datacentre:br-ex')
        parser.add_argument('--neutron-public-interface', default='nic1')
        parser.add_argument('--hypervisor-neutron-public-interface',
                            default='nic1')
        parser.add_argument('--neutron-network-type', default='gre')
        parser.add_argument('--neutron-tunnel-types', default='gre')

        parser.add_argument('--libvirt-type', default='qemu')
        parser.add_argument('--ntp-server', default='')
        parser.add_argument(
            '--undercloud-ceilometer-snmpd-password',
            default=os.environ.get('UNDERCLOUD_CEILOMETER_SNMPD_PASSWORD'),
            help=_('Password for undercloud Ceilometer SNMPD. Defaults to '
                   'UNDERCLOUD_CEILOMETER_SNMPD_PASSWORD environment '
                   'variable')
        )
        parser.add_argument(
            '--plan-uuid',
            help=_("The UUID of the Tuskar plan to deploy.")
        )
        parser.add_argument(
            '-O', '--output-dir', metavar='<OUTPUT DIR>',
            help=_('Directory to write Tuskar template files into. It will be '
                   'created if it does not exist. If not provided a temporary '
                   'directory will be used.')
        )

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        clients = self.app.client_manager
        orchestration_client = clients.rdomanager_oscplugin.orchestration()

        stack = self._get_stack(orchestration_client)

        self._pre_heat_deploy()

        if parsed_args.use_tht:
            self._deploy_tripleo_heat_templates(stack, parsed_args)
        else:
            self._deploy_tuskar(stack, parsed_args)

        self._post_heat_deploy()
