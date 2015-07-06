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

import mock
from six.moves import builtins as __builtin__

from rdomanager_oscplugin.tests.v1.overcloud_validate import fakes
from rdomanager_oscplugin.v1 import overcloud_validate


class TestGenerateTempestDeployerInput(fakes.TestGenerateTempestDeployerInput):

    def setUp(self):
        super(TestGenerateTempestDeployerInput, self).setUp()

        # Get the command object to test
        self.cmd = overcloud_validate.GenerateTempestDeployerInput(self.app,
                                                                   None)
        self.cmd.tempest_run_dir = '/home/user/tempest'
        self.cmd.generated_partial_config_path = ('/home/user/tempest/'
                                                  'deployer.config')

    @mock.patch.object(__builtin__, 'open')
    @mock.patch('rdomanager_oscplugin.v1.overcloud_validate.'
                'GenerateTempestDeployerInput._setup_dir')
    def test_validate_ok(self, mock_setup_dir, mock_open):
        parsed_args = self.check_parser(self.cmd, [], [])
        self.cmd.take_action(parsed_args)

        mock_setup_dir.assert_called_once_with()
        mock_open.assert_called_once_with('/home/user/tempest/deployer.config',
                                          'w+')
