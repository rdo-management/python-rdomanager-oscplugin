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

"""Plugin action implementation"""

import logging

from cliff import command
from instack_undercloud import undercloud
from oslo_config import cfg
from tuskarclient import client
from tuskarclient.common import utils


class InstallPlugin(command.Command):
    """Install and setup the undercloud"""

    auth_required = False
    log = logging.getLogger(__name__ + ".InstallPlugin")

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        # TODO(trown): Make the location of the instack root dir configurable
        undercloud.install('.')

        tuskar_defaults = {
            'Ceph-Storage-1::count': '0',
            'Ceph-Storage-1::Flavor': 'baremetal',
            'Ceph-Storage-1::Image': 'overcloud-full',
            'Cinder-Storage-1::CinderISCSIHelper': 'lioadm',
            'Cinder-Storage-1::count': '0',
            'Cinder-Storage-1::Image': 'overcloud-full',
            'Cinder-Storage-1::Flavor': 'baremetal',
            'Compute-1::count': '1',
            'Compute-1::Flavor': 'baremetal',
            'Compute-1::Image': 'overcloud-full',
            'Compute-1::NeutronBridgeMappings': 'datacentre:br-ex',
            'Compute-1::NeutronEnableTunnelling': 'True',
            'Compute-1::NeutronFlatNetworks': 'datacentre',
            'Compute-1::NeutronNetworkType': 'gre',
            'Compute-1::NeutronNetworkVLANRanges': 'datacentre:1:1000',
            'Compute-1::NeutronPhysicalBridge': 'br-ex',
            'Compute-1::NeutronPublicInterface': 'nic1',
            'Compute-1::NeutronTunnelTypes': 'gre',
            'Compute-1::NovaComputeLibvirtType': 'qemu',
            'Compute-1::NtpServer': '',
            'Controller-1::CinderISCSIHelper': 'lioadm',
            'Controller-1::CloudName': 'overcloud',
            'Controller-1::count': '1',
            'Controller-1::Flavor': 'baremetal',
            'Controller-1::Image': 'overcloud-full',
            'Controller-1::NeutronBridgeMappings': 'datacentre:br-ex',
            'Controller-1::NeutronEnableTunnelling': 'True',
            'Controller-1::NeutronFlatNetworks': 'datacentre',
            'Controller-1::NeutronNetworkType': 'gre',
            'Controller-1::NeutronNetworkVLANRanges': 'datacentre:1:1000',
            'Controller-1::NeutronPublicInterface': 'nic1',
            'Controller-1::NeutronTunnelTypes': 'gre',
            'Controller-1::NtpServer': '',
            'Swift-Storage-1::count': '0',
            'Swift-Storage-1::Flavor': 'baremetal',
            'Swift-Storage-1::Image': 'overcloud-full',
        }

	# Reload the config so we can get the passwords
        undercloud._load_config()
        # Create a tuskar client
        management = client.get_client(
            '2',
            os_auth_token=cfg.CONF['auth']['undercloud_admin_token'],
            os_tenant_name='admin',
            tuskar_url='http://192.0.2.1:8585/v2')

        plan = utils.find_resource(management.plans, 'overcloud')

        parameters = [{'name': pair[0], 'value': pair[1]}
                      for pair in tuskar_defaults.items()]
        management.plans.patch(plan.uuid, parameters)

        return
