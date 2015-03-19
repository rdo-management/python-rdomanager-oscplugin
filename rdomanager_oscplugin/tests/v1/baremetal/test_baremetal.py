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

import tempfile

import json
import mock
import os

from rdomanager_oscplugin.tests.v1.baremetal import fakes
from rdomanager_oscplugin.v1 import baremetal


class TestBaremetal(fakes.TestBaremetal):

    def setUp(self):
        super(TestBaremetal, self).setUp()

        # Get a shortcut to the ImportManager Mock
        self.import_mock = self.app.client_manager.baremetal.import_
        self.import_mock.reset_mock()

        # Get the command object to test
        self.cmd = baremetal.ImportPlugin(self.app, None)


class TestBaremetalImport(TestBaremetal):

    def setUp(self):
        super(TestBaremetalImport, self).setUp()

        self.json_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        self.csv_file = tempfile.NamedTemporaryFile(mode='w', delete=False)

        self.csv_file.write("""\
pxe_ssh,192.168.122.1,root,"KEY1",00:d0:28:4c:e8:e8
pxe_ssh,192.168.122.1,root,"KEY2",00:7c:ef:3d:eb:60""")

        json.dump([{
            "pm_user": "stack",
            "pm_addr": "192.168.122.1",
            "pm_password": "KEY1",
            "pm_type": "pxe_ssh",
            "mac": [
                "00:0b:d0:69:7e:59"
            ],
        }, {
            "arch": "x86_64",
            "pm_user": "stack",
            "pm_addr": "192.168.122.2",
            "pm_password": "KEY2",
            "pm_type": "pxe_ssh",
            "mac": [
                "00:0b:d0:69:7e:58"
            ]
        }], self.json_file)

        self.json_file.close()
        self.csv_file.close()

    def tearDown(self):

        super(TestBaremetalImport, self).tearDown()
        os.unlink(self.json_file.name)
        os.unlink(self.csv_file.name)

    @mock.patch('os_cloud_config.nodes.register_all_nodes')
    def test_json_import(self, mock_register_nodes):

        arglist = [self.json_file.name, '--json', '-s', 'http://localhost']

        verifylist = [
            ('csv', False),
            ('json', True),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.cmd.take_action(parsed_args)

        mock_register_nodes.assert_called_with(
            'http://localhost',
            [
                {
                    'pm_password': 'KEY1',
                    'pm_type': 'pxe_ssh',
                    'pm_user': 'stack',
                    'pm_addr': '192.168.122.1',
                    'mac': ['00:0b:d0:69:7e:59']
                }, {
                    'pm_user': 'stack',
                    'pm_password': 'KEY2',
                    'pm_addr': '192.168.122.2',
                    'arch': 'x86_64',
                    'pm_type': 'pxe_ssh',
                    'mac': ['00:0b:d0:69:7e:58']
                }
            ],
            client=self.app.client_manager.baremetal,
            keystone_client=None)

    @mock.patch('os_cloud_config.nodes.register_all_nodes')
    def test_csv_import(self, mock_register_nodes):

        arglist = [self.csv_file.name, '--csv', '-s', 'http://localhost']

        verifylist = [
            ('csv', True),
            ('json', False),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.cmd.take_action(parsed_args)

        mock_register_nodes.assert_called_with(
            'http://localhost',
            [
                {
                    'pm_password': 'KEY1',
                    'pm_user': 'root',
                    'pm_type': 'pxe_ssh',
                    'pm_addr': '192.168.122.1',
                    'mac': ['00:d0:28:4c:e8:e8']
                }, {
                    'pm_password': 'KEY2',
                    'pm_user': 'root',
                    'pm_type': 'pxe_ssh',
                    'pm_addr': '192.168.122.1',
                    'mac': ['00:7c:ef:3d:eb:60']
                }
            ],
            client=self.app.client_manager.baremetal,
            keystone_client=None)
