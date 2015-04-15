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

from heatclient.common import template_utils
from cliff import command

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


class DeployPlugin(command.Command):
    """Overcloud Image Build plugin"""

    log = logging.getLogger(__name__ + ".BuildPlugin")

    def get_parser(self, prog_name):
        parser = super(DeployPlugin, self).get_parser(prog_name)
        parser.add_argument('--control-scale', type=int, default=1)
        parser.add_argument('--compute-scale', type=int, default=1)
        parser.add_argument('--ceph-storage-scale', type=int, default=0)
        parser.add_argument('--block-storage-scale', type=int, default=0)
        parser.add_argument('--swift-storage-scale', type=int, default=0)
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        clients = self.app.client_manager

        self.log.debug("Checking hypervisor stats")
        utils.check_hypervisor_stats(clients.compute)

        self.log.debug("Generating overcloud passwords")
        passwords = utils.generate_overcloud_passwords()

        network_client = clients.network
        net = network_client.api.find_attr('networks', 'ctlplane')
        PARAMETERS['NeutronControlPlaneID'] = net['id']

        PARAMETERS['AdminPassword'] = passwords['OVERCLOUD_ADMIN_PASSWORD']
        PARAMETERS['AdminToken'] = passwords['OVERCLOUD_ADMIN_TOKEN']
        cielometer_pass = passwords['OVERCLOUD_CEILOMETER_PASSWORD']
        ceilometer_secret = passwords['OVERCLOUD_CEILOMETER_SECRET']
        PARAMETERS['CeilometerPassword'] = cielometer_pass
        PARAMETERS['CeilometerMeteringSecret'] = ceilometer_secret
        PARAMETERS['CinderPassword'] = passwords['OVERCLOUD_CINDER_PASSWORD']
        PARAMETERS['GlancePassword'] = passwords['OVERCLOUD_GLANCE_PASSWORD']
        PARAMETERS['HeatPassword'] = passwords['OVERCLOUD_HEAT_PASSWORD']
        PARAMETERS['NeutronPassword'] = passwords['OVERCLOUD_NEUTRON_PASSWORD']
        PARAMETERS['NovaPassword'] = passwords['OVERCLOUD_NOVA_PASSWORD']
        PARAMETERS['SwiftHashSuffix'] = passwords['OVERCLOUD_SWIFT_HASH']
        PARAMETERS['SwiftPassword'] = passwords['OVERCLOUD_SWIFT_PASSWORD']

        if parsed_args.control_scale > 1:
            PARAMETERS['NeutronL3HA'] = True

        if parsed_args.ceph_storage_scale > 0:
            PARAMETERS.update({
                'CephClusterFSID': six.text_type(uuid.uuid1()),
                # TODO
                #'CephMonKey': $MON_KEY,
                #'CephAdminKey': $ADMIN_KEY,
                'CinderEnableRbdBackend': True,
                'NovaEnableRbdBackend': True,
            })

        env_path = os.path.expanduser("~/overcloud-env.json")

        self.log.debug("Creating Environment file")
        with open(env_path, 'w+') as f:
            f.write(json.dumps({
                "parameters": {
                    "ControllerCount": parsed_args.control_scale,
                    "ComputeCount": parsed_args.compute_scale,
                    "CephStorageCount": parsed_args.ceph_storage_scale,
                    "BlockStorageCount": parsed_args.block_storage_scale,
                    "ObjectStorageCount": parsed_args.swift_storage_scale}
            }))

        orchestration = clients.rdomanager_oscplugin.orchestration()

        self.log.debug("Processing environment files")
        env_files, env = template_utils.process_multiple_environments_and_files(
            [RESOURCE_REGISTRY_PATH, env_path])

        self.log.debug("Getting template contents")
        tpl_files, template = template_utils.get_template_contents(
            OVERCLOUD_YAML_PATH)

        self.log.debug("Template    : {0}".format(template))
        self.log.debug("Parameters  : {0}".format(PARAMETERS))
        self.log.debug("Environment : {0}".format(env))

        client = self.app.client_manager.rdomanager_oscplugin.baremetal()

        for node in client.node.list():

            if node.provision_state != "available":

                self.log.debug(("Setting provision state from {0} to "
                                "'available' for Node {1}"
                                ).format(node.provision_state, node.uuid))

                client.node.set_provision_state(node.uuid, 'provide')

        orchestration.stacks.create(
            stack_name="overcloud",
            template=template,
            parameters=PARAMETERS,
            environment=env,
            files=dict(list(tpl_files.items()) + list(env_files.items())),
        )

        create_result = utils.wait_for_stack_ready(orchestration, "overcloud")

        if not create_result:
            print("Heat Stack create failed", file=sys.stderr)
            return
