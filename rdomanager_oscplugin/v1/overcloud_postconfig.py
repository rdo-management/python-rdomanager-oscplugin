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

from cliff import command
from keystoneclient import exceptions as ksc_exc
from openstackclient.i18n import _
from os_cloud_config import keystone
from os_cloud_config import neutron

from rdomanager_oscplugin import utils


class PostconfigOvercloud(command.Command):
    """Complete the configuration of the overcloud"""

    auth_required = False
    log = logging.getLogger(__name__ + ".PostconfigOvercloud")

    def get_parser(self, prog_name):
        parser = super(PostconfigOvercloud, self).get_parser(prog_name)

        parser.add_argument('--overcloud_nameserver', default='8.8.8.8')
        parser.add_argument('--floating-id-cidr', default='192.0.2.0/24')
        parser.add_argument('--floating-ip-start', default='192.0.2.45')
        parser.add_argument('--floating-ip-end', default='192.0.2.64')
        parser.add_argument('--ibm-network-gateway', default='192.0.2.1')
        parser.add_argument(
            'overcloud_ip',
            help=_('The IP address of the Overcloud endpoint')
        )

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        identity_client = self.app.client_manager.identity

        passwords = utils.generate_overcloud_passwords()

        utils.remove_known_hosts(parsed_args.overcloud_ip)

        # TODO(dmatthews): Update os-cloud-config so that we don't need to
        # copy all the defaults from their CLI parser. They force us to pass
        # all values.
        keystone.initialize(
            parsed_args.overcloud_ip, passwords['OVERCLOUD_ADMIN_TOKEN'],
            'admin.example.com', passwords['OVERCLOUD_ADMIN_PASSWORD'],
            'regionOne', None, None, 'heat-admin', 600, 10, True)

        try:
            identity_client.roles.create(name='swiftoperator')
        except ksc_exc.Conflict:
            pass

        try:
            identity_client.roles.create(name='ResellerAdmin')
        except ksc_exc.Conflict:
            pass

        utils.setup_endpoints(parsed_args.overcloud_ip,
                              passwords,
                              identity_client)

        try:
            identity_client.roles.create(name='heat_stack_user')
        except ksc_exc.Conflict:
            pass

        network_description = {
            "float": {
                "cidr": parsed_args.network_cidr,
                "name": "default-net",
                "nameserver": parsed_args.overcloud_nameserver
            },
            "external": {
                "name": "ext-net",
                "cidr": parsed_args.floating_id_cidr,
                "allocation_start": parsed_args.floating_ip_start,
                "allocation_end": parsed_args.floating_ip_end,
                "gateway": parsed_args.ibm_network_gateway,
            }
        }

        neutron.initialize_neutron(
            network_description,
            neutron_client=self.app.client_manager.network,
            keystone_client=self.app.client_manager.identity,
        )

        self.app.client_manager.compute.flavors.create(
            'm1.demo', 512, 1, 10, 'auto')
