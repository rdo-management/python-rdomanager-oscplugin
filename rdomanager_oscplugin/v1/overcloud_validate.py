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

from rdomanager_oscplugin import utils


class ValidateOvercloud(command.Command):
    """Validates the functionality of an overcloud using Tempest"""

    auth_required = False
    log = logging.getLogger(__name__ + ".ValidateOvercloud")
    tempest_run_dir = os.path.join(os.path.expanduser("~"), "tempest")
    generated_partial_config_path = os.path.join(tempest_run_dir,
                                                 'deployer.config')

    def _setup_dir(self):
        if not os.path.isdir(self.tempest_run_dir):
            os.mkdir(self.tempest_run_dir)

    def _generate_partial_config(self):
        config = configparser.ConfigParser()

        config.add_section('network')
        config.set('network', 'tenant_network_cidr', '10.0.0.0/24')
        config.set('network', 'floating_network_name ', 'ext-net')

        config.add_section('compute-feature-enabled')
        config.set('compute-feature-enabled', 'resize', 'false')

        config.add_section('identity-feature-enabled')
        config.set('identity-feature-enabled', 'api_v3', 'false')

        config.add_section('volume')
        config.set('volume', 'backend1_name', 'tripleo_iscsi')
        config.set('volume', 'storage_protocol', 'iSCSI')
        config.set('volume', 'vendor_name', 'Open Source')

        config.add_section('volume-feature-enabled')
        config.set('volume-feature-enabled', 'multi_backend', 'false')
        config.set('volume-feature-enabled', 'backup', 'false')
        config.set('volume-feature-enabled', 'snapshot', 'false')
        config.set('volume-feature-enabled', 'api_v1', 'false')
        config.set('volume-feature-enabled', 'api_v2', 'true')
        config.set('volume-feature-enabled', 'bootable', 'false')

        config.add_section('object-storage')
        config.set('object-storage', 'operator_role', 'swiftoperator')

        with open(self.generated_partial_config_path, 'w+') as config_file:
            config.write(config_file)

    def _run_tempest(self, overcloud_auth_url, overcloud_admin_password,
                     deployer_input, tempest_args, skipfile):
        os.chdir(self.tempest_run_dir)

        if not deployer_input:
            self._generate_partial_config()
            deployer_input = self.generated_partial_config_path

        utils.run_shell('/usr/share/openstack-tempest-kilo/tools/'
                        'configure-tempest-directory')
        utils.run_shell('./tools/config_tempest.py --out etc/tempest.conf '
                        '--deployer-input %(partial_config_file)s '
                        '--debug --create '
                        'identity.uri %(auth_url)s '
                        'compute.allow_tenant_isolation true '
                        'object-storage.operator_role SwiftOperator '
                        'identity.admin_password %(admin_password)s '
                        'compute.build_timeout 500 '
                        'compute.image_ssh_user cirros '
                        'compute.ssh_user cirros '
                        'network.build_timeout 500 '
                        'volume.build_timeout 500 '
                        'scenario.ssh_user cirros' %
                        {'partial_config_file': deployer_input,
                         'auth_url': overcloud_auth_url,
                         'admin_password': overcloud_admin_password})

        args = ['./tools/run-tests.sh', ]

        if tempest_args is not None:
            args.append(tempest_args)
        if skipfile is not None:
            args.extend(['--skip-file', skipfile])

        utils.run_shell(' '.join(args))

    def get_parser(self, prog_name):
        parser = super(ValidateOvercloud, self).get_parser(prog_name)

        parser.add_argument('--overcloud-auth-url', required=True)
        parser.add_argument('--overcloud-admin-password', required=True)
        parser.add_argument('--deployer-input')
        parser.add_argument('--tempest-args')
        parser.add_argument('--skipfile')

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        self._setup_dir()
        self._run_tempest(parsed_args.overcloud_auth_url,
                          parsed_args.overcloud_admin_password,
                          parsed_args.deployer_input,
                          parsed_args.tempest_args,
                          parsed_args.skipfile)
