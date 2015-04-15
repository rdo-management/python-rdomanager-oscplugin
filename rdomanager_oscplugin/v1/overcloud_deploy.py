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
import uuid

from cliff import command
from heatclient.common import template_utils
from heatclient.exc import HTTPNotFound
from os_cloud_config import keystone_pki

from rdomanager_oscplugin import utils


TRIPLEO_HEAT_TEMPLATES = "/usr/share/openstack-tripleo-heat-templates/"
OVERCLOUD_YAML_PATH = os.path.join(TRIPLEO_HEAT_TEMPLATES,
                                   "overcloud-without-mergepy.yaml")
RESOURCE_REGISTRY_PATH = os.path.join(
    TRIPLEO_HEAT_TEMPLATES, "overcloud-resource-registry-puppet.yaml")

CONFIG = {
    'CONTROLSCALE': 1,
    'COMPUTESCALE': 1,
    'CEPHSTORAGESCALE': 0,
    'BLOCKSTORAGESCALE': 0,
    'SWIFTSTORAGESCALE': 0,
}

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
    'OvercloudControlFlavor': 'baremetal_control',
    'OvercloudComputeFlavor': 'baremetal_compute',
    'OvercloudBlockStorageFlavor': 'baremetal_compute',
    'OvercloudSwiftStorageFlavor': 'baremetal_compute',
    'OvercloudCephStorageFlavor': 'baremetal_ceph-storage',
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

    log = logging.getLogger(__name__ + ".BuildPlugin")

    def get_parser(self, prog_name):
        parser = super(DeployOvercloud, self).get_parser(prog_name)
        parser.add_argument('--control-scale', type=int, default=1)
        parser.add_argument('--compute-scale', type=int, default=1)
        parser.add_argument('--ceph-storage-scale', type=int, default=0)
        parser.add_argument('--block-storage-scale', type=int, default=0)
        parser.add_argument('--swift-storage-scale', type=int, default=0)
        return parser

    def set_overcloud_passwords(self, parameters):
        """Add passwords to the parameters dictionary

        :param parameters: A dictionary for the passwords to be added to
        :type parameters: dict
        """

        passwords = utils.generate_overcloud_passwords()
        parameters['AdminPassword'] = passwords['OVERCLOUD_ADMIN_PASSWORD']
        parameters['AdminToken'] = passwords['OVERCLOUD_ADMIN_TOKEN']
        cielometer_pass = passwords['OVERCLOUD_CEILOMETER_PASSWORD']
        ceilometer_secret = passwords['OVERCLOUD_CEILOMETER_SECRET']
        parameters['CeilometerPassword'] = cielometer_pass
        parameters['CeilometerMeteringSecret'] = ceilometer_secret
        parameters['CinderPassword'] = passwords['OVERCLOUD_CINDER_PASSWORD']
        parameters['GlancePassword'] = passwords['OVERCLOUD_GLANCE_PASSWORD']
        parameters['HeatPassword'] = passwords['OVERCLOUD_HEAT_PASSWORD']
        parameters['NeutronPassword'] = passwords['OVERCLOUD_NEUTRON_PASSWORD']
        parameters['NovaPassword'] = passwords['OVERCLOUD_NOVA_PASSWORD']
        parameters['SwiftHashSuffix'] = passwords['OVERCLOUD_SWIFT_HASH']
        parameters['SwiftPassword'] = passwords['OVERCLOUD_SWIFT_PASSWORD']

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        clients = self.app.client_manager
        baremetal_client = clients.rdomanager_oscplugin.baremetal()
        compute_client = clients.compute
        network_client = clients.network
        orchestration_client = clients.rdomanager_oscplugin.orchestration()

        try:
            stack = orchestration_client.stacks.get('overcloud')
            self.log.debug("Stack found, will be doing a stack update")
            stack_create = False
        except HTTPNotFound:
            stack_create = True
            self.log.debug("No stack found, will be doing a stack create")

        self.log.debug("Checking hypervisor stats")
        if utils.check_hypervisor_stats(compute_client) is None:
            print("Expected hypervisor stats not met", file=sys.stderr)
            return

        parameters = PARAMETERS.copy()

        snmp_pass = utils.get_heira_password("snmpd_readonly_user_password")
        parameters['SnmpdReadonlyUserPassword'] = snmp_pass

        self.log.debug("Generating overcloud passwords")
        self.set_overcloud_passwords(parameters)

        self.log.debug("Getting ctlplane from Neutron")

        net = network_client.api.find_attr('networks', 'ctlplane')
        parameters['NeutronControlPlaneID'] = net['id']

        if parsed_args.control_scale > 1:
            parameters['NeutronL3HA'] = True

        if parsed_args.ceph_storage_scale > 0:
            parameters.update({
                'CephClusterFSID': six.text_type(uuid.uuid1()),
                'CinderEnableRbdBackend': True,
                'NovaEnableRbdBackend': True,
            })

        self.log.debug("Creating Environment file")
        env_path = utils.create_environment_file()

        if stack_create:
            self.log.debug("Creating Environment file")
            keystone_pki.generate_certs_into_json(env_path, False)

        self.log.debug("Processing environment files")
        env_files, env = template_utils.\
            process_multiple_environments_and_files(
                [RESOURCE_REGISTRY_PATH, env_path])

        self.log.debug("Getting template contents")
        template_files, template = template_utils.get_template_contents(
            OVERCLOUD_YAML_PATH)

        self.log.debug("Verifying that Ironic nodes to available or active")
        utils.set_nodes_state(
            baremetal_client.node.list(), baremetal_client,
            'provide', skipped_states=("available", "active"))

        stack_args = {
            'stack_name': "overcloud",
            'template': template,
            'parameters': parameters,
            'environment': env,
            'files': dict(
                list(template_files.items()) + list(env_files.items())
            ),
        }

        if stack_create:
            self.log.debug("Perform Heat stack create")
            orchestration_client.stacks.create(**stack_args)
        else:
            self.log.debug("Perform Heat stack update")
            orchestration_client.stacks.update(stack.id, **stack_args)

        create_result = utils.wait_for_stack_ready(
            orchestration_client, "overcloud")

        if not create_result:
            print("Heat Stack create failed", file=sys.stderr)
