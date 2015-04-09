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
from tripleo_common import scales


class ScalePlugin(command.Command):
    """Overcloud Stack Scale plugin"""

    auth_required = False
    log = logging.getLogger(__name__ + ".ScalePlugin")

    def get_parser(self, prog_name):
        parser = super(ScalePlugin, self).get_parser(prog_name)
        parser.add_argument('-r', '--role', dest='role', required=True)
        parser.add_argument('-n', '--num', dest='num', required=True)
        parser.add_argument('-s', '--stack', dest='stack_id',
                            default='overcloud')
        parser.add_argument('-p', '--plan', dest='plan_id',
                            default='overcloud')
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)
        management = self.app.client_manager.rdomanager_oscplugin.management()
        orchestration = self.app.client_manager.rdomanager_oscplugin.orchestration()
        scale_manager = scales.ScaleManager(
                tuskarclient=management,
                heatclient=orchestration,
                plan_id=parsed_args.plan_id,
                stack_id=parsed_args.stack_id)
        scale_manager.scaleup(parsed_args.role, parsed_args.num)
