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

import sys

from rdomanager_oscplugin.tests import base
from rdomanager_oscplugin.tests import fakes
from rdomanager_oscplugin.tests.v1.test_plugin import TestPluginV1
from rdomanager_oscplugin.v1.plugin import undercloud

# Load the plugin init module for the plugin list and show commands
import rdomanager_oscplugin.plugin
plugin_name = 'rdomanager_oscplugin'
plugin_client = 'rdomanager_oscplugin.plugin'


class FakePluginV1Client(object):
    def __init__(self, **kwargs):
        #self.servers = mock.Mock()
        #self.servers.resource_class = fakes.FakeResource(None, {})
        self.auth_token = kwargs['token']
        self.management_url = kwargs['endpoint']


class TestUndercloudInstall(TestPluginV1):

    def setUp(self):
        super(TestUndercloudInstall, self).setUp()

        self.app.ext_modules = [
            sys.modules[plugin_client],
        ]

        # Get the command object to test
        self.cmd = plugin.undercloud.InstallPlugin(self.app, None)

    @mock.patch('subprocess.call')
    def test_undercloud_install(self, mock_subprocess):
        arglist = []
        verifylist = []
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        # DisplayCommandBase.take_action() returns two tuples
        self.cmd.take_action(parsed_args)


        mock_subprocess.assert_called_with('instack-install-undercloud')
