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

from rdomanager_oscplugin.tests.v1.test_plugin import TestPluginV1

# Load the plugin init module for the plugin list and show commands
from rdomanager_oscplugin.v1 import overcloud_image


class FakePluginV1Client(object):
    def __init__(self, **kwargs):
        self.auth_token = kwargs['token']
        self.management_url = kwargs['endpoint']


class TestOvercloudImageBuild(TestPluginV1):

    def setUp(self):
        super(TestOvercloudImageBuild, self).setUp()

        # Get the command object to test
        self.cmd = overcloud_image.BuildPlugin(self.app, None)


class TestOvercloudImageCreate(TestPluginV1):
    def setUp(self):
        super(TestOvercloudImageCreate, self).setUp()

        # Get the command object to test
        self.cmd = overcloud_image.CreatePlugin(self.app, None)

        self.app.client_manager.image = mock.Mock()
        self.app.client_manager.compute = mock.Mock()
        self.cmd._read_image_file = mock.Mock(return_value=b'IMGDATA')

    @mock.patch('os.path.isfile', return_value=True)
    @mock.patch('subprocess.call')
    def test_overcloud_create_images(self, mock_subprocess_call, mock_isfile):
        parsed_args = self.check_parser(self.cmd, [], [])

        self.cmd.take_action(parsed_args)

        self.assertEqual(mock_isfile.call_count, 5)
        self.assertEqual(
            mock_isfile.call_args_list, [
                mock.call('./deploy-ramdisk-ironic.initramfs'),
                mock.call('./deploy-ramdisk-ironic.kernel'),
                mock.call('./discovery-ramdisk.initramfs'),
                mock.call('./discovery-ramdisk.kernel'),
                mock.call('./openstack-full.qcow2')
            ])

        self.assertEqual(
            self.app.client_manager.image.images.delete.call_count,
            2
        )
        self.assertEqual(
            self.app.client_manager.image.images.create.call_count,
            2
        )
        self.assertEqual(
            self.app.client_manager.image.images.create.call_args_list,
            [mock.call(disk_format='aki',
                       name='bm_deploy_kernel',
                       data=b'IMGDATA',
                       is_public=True),
             mock.call(disk_format='ari',
                       name='bm_deploy_ramdisk',
                       data=b'IMGDATA',
                       is_public=True)])

        self.assertEqual(
            self.app.client_manager.compute.flavors.find.call_count,
            1
        )

        self.assertEqual(mock_subprocess_call.call_count, 3)
        self.assertEqual(
            mock_subprocess_call.call_args_list, [
                mock.call('tripleo load-image -d ./openstack-full.qcow2',
                          shell=True),
                mock.call('sudo cp -f "./discovery-ramdisk.kernel" '
                          '"/tftpboot/discovery.kernel"', shell=True),
                mock.call('sudo cp -f "./discovery-ramdisk.initramfs" '
                          '"/tftpboot/discovery.ramdisk"', shell=True)
            ])
