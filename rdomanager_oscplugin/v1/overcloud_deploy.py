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

import uuid
import logging
import os
import six

from rdomanager_oscplugin.v1 import util

from cliff import command


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
    'HypervisorNeutronPublicInterface': 'nic1',
    'NovaComputeLibvirtType': 'qemu',
    'NovaPassword': None,
    'SwiftHashSuffix': None,
    'SwiftPassword': None,
    'NeutronNetworkType': 'gre',
    'NeutronTunnelTypes': 'gre',
    'SnmpdReadonlyUserPassword': '${UNDERCLOUD_CEILOMETER_SNMPD_PASSWORD}', #TODO
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

        util.wait_for_hypervisor_stats(clients.compute)

        passwords = util.generate_overcloud_passwords()

        network_client = clients.network
        net = network_client.api.find_attr('networks', 'ctlplane')
        PARAMETERS['NeutronControlPPlaneID'] = net['id']
        PARAMETERS.update(passwords)

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

        environment = {
            "ControllerCount": parsed_args.control_scale,
            "ComputeCount": parsed_args.compute_scale,
            "CephStorageCount": parsed_args.ceph_storage_scale,
            "BlockStorageCount": parsed_args.block_storage_scale,
            "ObjectStorageCount": parsed_args.swift_storage_scale
        }

        orchestration = clients.rdomanager_oscplugin.orchestration()
        orchestration.stacks.create(
            stack_name="overcloud",
            template=OVERCLOUD_YAML_PATH,
            parameters=PARAMETERS,
            environment=environment,
        )
