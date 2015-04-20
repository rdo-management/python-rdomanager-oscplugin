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
from tripleo_common import update


class UpdateOvercloud(command.Command):
    """Overcloud Stack Update plugin"""

    auth_required = False
    log = logging.getLogger(__name__ + ".UpdateOvercloud")

    def get_parser(self, prog_name):
        parser = super(UpdateOvercloud, self).get_parser(prog_name)
        parser.add_argument('-s', '--stack', dest='stack_id',
                            default='overcloud')
        parser.add_argument('-p', '--plan', dest='plan_id',
                            default='overcloud')
        parser.add_argument('-i', '--interactive', dest='interactive',
                            action='store_true')
        parser.add_argument('-c', '--continue', dest='continue_update',
                            action='store_true')
        parser.add_argument('-a', '--abort', dest='abort_update',
                            action='store_true')
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)
        management = self.app.client_manager.rdomanager_oscplugin.management()
        orchestration = self.app.client_manager.rdomanager_oscplugin.orchestration()
        update_manager = update.UpdateManager(
                tuskarclient=management,
                heatclient=orchestration,
                plan_id=parsed_args.plan_id,
                stack_id=parsed_args.stack_id)
        if parsed_args.abort_update:
            update_manager.cancel()
        elif not parsed_args.continue_update:
            update_manager.update()

        if parsed_args.interactive:
            update_manager.do_interactive_update()
        else:
            print update_manager.get_status()
