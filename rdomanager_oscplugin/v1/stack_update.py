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

import argparse
import logging
import sys

from cliff import lister
from openstackclient.common import utils

from cliff import command


class UpdatePlugin(IntrospectionParser, lister.Lister):
    """Heat stack update plugin"""

    log = logging.getLogger(__name__ + ".StackUpdatePlugin")

    def take_action(self, parsed_args):

        self.log.debug("take_action(%s)" % parsed_args)
        client = self.app.client_manager.rdomanager_oscplugin.baremetal()

        statuses = []

        for node in client.node.list():
            self.log.debug("Getting introspection status of Ironic node {0}"
                           .format(node.uuid))
            auth_token = self.app.client_manager.auth_ref.auth_token
            statuses.append((node.uuid, discoverd_client.get_status(
                node.uuid,
                base_url=parsed_args.discoverd_url,
                auth_token=auth_token)))

        return (
            ("Node UUID", "Finished", "Error"),
            list((node_uuid, status['finished'], status['error'])
                 for (node_uuid, status) in statuses)
        )
