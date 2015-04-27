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

from cliff import command
from tripleo_common import scale


class ScaleOvercloud(command.Command):
    """Scale Overcloud nodes

    Update role's count in tuskar overcloud plan and
    trigger overcloud stack-update. Tuskar role is specified
    with version, e.g.:
    openstack overcloud scale stack overcloud overcloud -r Compute-1 -n 2
    """

    log = logging.getLogger(__name__ + ".ScaleOvercloud")

    def get_parser(self, prog_name):
        parser = super(ScaleOvercloud, self).get_parser(prog_name)
        parser.add_argument('-r', '--role', dest='role', required=True)
        parser.add_argument('-n', '--num', dest='num', required=True)
        parser.add_argument('plan', help="Name or ID of tuskar plan to scale")
        parser.add_argument('stack', help="Name or ID of heat stack to scale")
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)
        management = self.app.client_manager.rdomanager_oscplugin.management()
        orchestration = (self.app.client_manager.rdomanager_oscplugin.
                         orchestration())
        scale_manager = scale.ScaleManager(
            tuskarclient=management,
            heatclient=orchestration,
            plan_id=parsed_args.plan,
            stack_id=parsed_args.stack)
        scale_manager.scaleup(parsed_args.role, parsed_args.num)
