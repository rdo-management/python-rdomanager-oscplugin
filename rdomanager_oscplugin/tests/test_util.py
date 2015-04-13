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

from unittest import TestCase

import mock

from rdomanager_oscplugin.v1 import util


class TestPasswordsUtil(TestCase):

    def test_generate_passwords(self):

        passwords = util.generate_overcloud_passwords()
        passwords2 = util.generate_overcloud_passwords()

        self.assertEqual(len(passwords), 13)
        self.assertNotEqual(passwords, passwords2)

    def test_wait_for_hypervisor_stats(self):

        mock_comute = mock.Mock()
        mock_stats = mock.Mock()

        return_values = [
            {'count': 0, 'memory_mb': 0, 'vcpus': 0},
            {'count': 1, 'memory_mb': 1, 'vcpus': 1},
        ]

        mock_stats.to_dict.side_effect = return_values
        mock_comute.hypervisors.statistics.return_value = mock_stats

        stats = util.wait_for_hypervisor_stats(
            mock_comute, nodes=1, memory=1, vcpu=1, sleep=0.01)

        self.assertEqual(stats, return_values[-1])
        self.assertEqual(mock_stats.to_dict.call_count, 2)
