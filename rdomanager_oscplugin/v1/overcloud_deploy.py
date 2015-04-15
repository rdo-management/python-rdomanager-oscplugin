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

import json
import logging
import os
import six
import subprocess
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


def _get_password(password):
    command = ["hiera", password]
    p = subprocess.Popen(command, stdout=subprocess.PIPE)
    out, err = p.communicate()
    return out


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
    'SnmpdReadonlyUserPassword': _get_password("snmpd_readonly_user_password"),
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


class OvercloudDeploy(command.Command):
    """Overcloud Image Build plugin"""

    log = logging.getLogger(__name__ + ".BuildPlugin")

    def get_parser(self, prog_name):
        parser = super(OvercloudDeploy, self).get_parser(prog_name)
        parser.add_argument('--control-scale', type=int, default=1)
        parser.add_argument('--compute-scale', type=int, default=1)
        parser.add_argument('--ceph-storage-scale', type=int, default=0)
        parser.add_argument('--block-storage-scale', type=int, default=0)
        parser.add_argument('--swift-storage-scale', type=int, default=0)
        return parser

    def set_overcloud_passwords(self, parameters):

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

    def create_environment_file(self, control_scale=1, compute_scale=1,
                                ceph_storage_scale=0, block_storage_scale=0,
                                swift_storage_scale=0):

        env_path = os.path.expanduser("~/overcloud-env.json")
        with open(env_path, 'w+') as f:
            f.write(json.dumps({
                "parameters": {
                    "ControllerCount": control_scale,
                    "ComputeCount": compute_scale,
                    "CephStorageCount": ceph_storage_scale,
                    "BlockStorageCount": block_storage_scale,
                    "ObjectStorageCount": swift_storage_scale}
            }))

        return env_path

    def make_nodes_available(self, bm_client):

        for node in bm_client.node.list():

            if node.provision_state != "available":

                self.log.debug(("Setting provision state from {0} to "
                                "'available' for Node {1}"
                                ).format(node.provision_state, node.uuid))

                bm_client.node.set_provision_state(node.uuid, 'provide')

                if not utils.wait_for_provision_state(bm_client, node.uuid,
                                                      'available'):
                    print("FAIL: State not updated for Node {0}".format(
                          node.uuid, file=sys.stderr))

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        clients = self.app.client_manager
        orchestration_client = clients.rdomanager_oscplugin.orchestration()
        network_client = clients.network
        compute_client = clients.compute

        try:
            stack = orchestration_client.stacks.get('overcloud')
            stack_create = False
        except HTTPNotFound:
            stack_create = True

        self.log.debug("Checking hypervisor stats")
        if utils.check_hypervisor_stats(compute_client) is None:
            print("")

        parameters = PARAMETERS.copy()

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
                # TODO
                #'CephMonKey': $MON_KEY,
                #'CephAdminKey': $ADMIN_KEY,
                'CinderEnableRbdBackend': True,
                'NovaEnableRbdBackend': True,
            })

        self.log.debug("Creating Environment file")
        env_path = self.create_environment_file()

        if stack_create:
            self.log.debug("Creating Environment file")
            keystone_pki.generate_certs_into_json(env_path, False)

        self.log.debug("Processing environment files")
        env_files, env = template_utils.process_multiple_environments_and_files(
            [RESOURCE_REGISTRY_PATH, env_path])

        self.log.debug("Getting template contents")
        tpl_files, template = template_utils.get_template_contents(
            OVERCLOUD_YAML_PATH)

        self.log.debug("Set Ironic nodes to available")
        bm_client = self.app.client_manager.rdomanager_oscplugin.baremetal()
        self.make_nodes_available(bm_client)

        stack_args = {
            'stack_name': "overcloud",
            'template': template,
            'parameters': parameters,
            'environment': env,
            'files': dict(list(tpl_files.items()) + list(env_files.items())),
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
