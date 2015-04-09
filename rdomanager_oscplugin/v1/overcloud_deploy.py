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

import logging

from rdomanager_oscplugin.v1 import util

from cliff import command


CONFIG = {
    'NeutronPublicInterface': 'nic1',
    'HypervisorNeutronPublicInterface': 'nic1',
    'NEUTRON_NETWORK_TYPE': 'gre',
    'NEUTRON_TUNNEL_TYPES': 'gre',
    'OVERCLOUD_LIBVIRT_TYPE': 'qemu',
    'NtpServer': '',
    'OVERCLOUD_EXTRA_CONFIG': '{}'
}


class DeployPlugin(command.Command):
    """Overcloud Image Build plugin"""

    auth_required = False
    log = logging.getLogger(__name__ + ".BuildPlugin")

    def get_parser(self, prog_name):
        parser = super(DeployPlugin, self).get_parser(prog_name)
        parser.add_argument('-P', '--parameter', dest='parameters',
                            metavar='<KEY1=VALUE1>',
                            help='This can be specified multiple times.',
                            action='append')
        parser.add_argument('-t', '--template')
        parser.add_argument('-r', '--resource-registry')
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        # Parameters
        # - Paramaters - scale counts and flavors
        # - template (optional)
        # - resource registry (optional)

        util.generate_overcloud_passwords()

        util.wait_for_hypervisor_stats(
            self.app.client_manager.compute, 1, 2, 3)
