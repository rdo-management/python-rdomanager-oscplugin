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
import subprocess

from cliff import command
from tuskarclient.openstack.common.apiclient import exceptions


class InstallPlugin(command.Command):
    """Install and setup the undercloud"""

    auth_required = False
    log = logging.getLogger(__name__ + ".InstallPlugin")

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        subprocess.check_call("instack-install-undercloud")

        tuskar_defaults = {
            'Controller-1::CinderISCSIHelper': 'lioadm',
            'Cinder-Storage-1::CinderISCSIHelper': 'lioadm',
            'Controller-1::CloudName': 'overcloud',
            'Swift-Storage-1::Image': 'overcloud-full',
            'Cinder-Storage-1::Image': 'overcloud-full',
            'Ceph-Storage-1::Image': 'overcloud-full',
            'Controller-1::Image': 'overcloud-full',
            'Compute-1::Image': 'overcloud-full',
            }

        management = self.app.client_manager.rdomanager_oscplugin.management()
        plans = [plan for plan in management.plans.list()
                 if plan.name == 'overcloud']
        if not plans:
            self.log.error('Could not find plan "overcloud"')
            raise KeyError('Could not find plan "overcloud"')

        if len(plans) > 1:
            self.log.error('More than one plan is called "overcloud"')
            raise KeyError('More than one plan is called "overcloud"')

        parameters = [{'name': pair[0], 'value': pair[1]}
                      for pair in tuskar_defaults.items()]
        management.plans.patch(plans[0].uuid, parameters)

        return
