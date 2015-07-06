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
import os

from cliff import command
from six.moves import configparser


class GenerateTempestDeployerInput(command.Command):
    """Generates deployer-input for Tempest configuration for Overcloud"""

    auth_required = False
    log = logging.getLogger(__name__ + ".GenerateTempestDeployerInput")
    tempest_run_dir = os.path.join(os.path.expanduser("~"), "tempest")
    generated_partial_config_path = os.path.join(tempest_run_dir,
                                                 'overcloud.config')

    def _setup_dir(self):
        if not os.path.isdir(self.tempest_run_dir):
            os.mkdir(self.tempest_run_dir)

    def _generate_partial_config(self):
        config = configparser.ConfigParser()

        config.add_section('compute-feature-enabled')
        # Does the test environment support obtaining instance serial console
        # output? (default: true)
        # set in [nova.serial_console]->enabled
        config.set('compute-feature-enabled', 'console_output', 'false')

        config.add_section('object-storage')
        # Role to add to users created for swift tests to enable creating
        # containers (default: 'Member')
        # keystone role-list returns this role
        config.set('object-storage', 'operator_role', 'swiftoperator')

        config.add_section('orchestration')
        # Role required for users to be able to manage stacks
        # (default: 'heat_stack_owner')
        config.set('orchestration', 'stack_owner_role', 'heat_stack_user')

        config.add_section('volume')
        # Name of the backend1 (must be declared in cinder.conf)
        # (default: 'BACKEND_1')
        # set in [cinder]->enabled_backends
        config.set('volume', 'backend1_name', 'tripleo_iscsi')

        config.add_section('volume-feature-enabled')
        # Update bootable status of a volume Not implemented on icehouse
        # (default: false)
        # python-cinderclient supports set-bootable
        config.set('volume-feature-enabled', 'bootable', 'true')

        with open(self.generated_partial_config_path, 'w+') as config_file:
            config.write(config_file)

    def get_parser(self, prog_name):
        parser = super(GenerateTempestDeployerInput,
                       self).get_parser(prog_name)

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        self._setup_dir()
        self._generate_partial_config()
