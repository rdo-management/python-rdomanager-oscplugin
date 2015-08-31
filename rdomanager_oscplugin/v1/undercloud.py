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

from __future__ import print_function

import collections
import logging
import re
import subprocess
import sys

from cliff import command

from openstackclient.common import utils as osc_utils
from openstackclient.i18n import _


class InstallPlugin(command.Command):
    """Install and setup the undercloud"""

    auth_required = False
    log = logging.getLogger(__name__ + ".InstallPlugin")

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        subprocess.check_call("instack-install-undercloud")

        return


class ValidateCapabilities(command.Command):
    """Validate that baremetal capabilities match flavor metadata"""

    log = logging.getLogger(__name__ + ".ValidateCapabilities")
    total_fails = 0

    def take_action(self, parsed_args):

        self.log.debug("take_action(%s)" % parsed_args)
        bm_client = self.app.client_manager.rdomanager_oscplugin.baremetal()

        compute_client = self.app.client_manager.compute

        kernel_id, ramdisk_id = self._image_ids()
        self.log.debug("Using kernel ID: {0} and ramdisk ID: {1}".format(
            kernel_id, ramdisk_id))

        self._check_flavors_exist(parsed_args)

        # map of profile capability -> [node_uuid, ...]
        profile_map = collections.defaultdict(list)

        for node in bm_client.node.list():
            node = bm_client.node.get(node.uuid)
            self.log.debug("Checking config for Node {0}".format(node.uuid))

            self._check_boot_images(node, kernel_id, ramdisk_id)

            self.log.debug("Collecting flavor information on node "
                           "{}".format(node.uuid))

            profiles = re.findall(r'profile:(.*?)(?:,|$)',
                                  node.properties.get('capabilities', ''))
            if not profiles:
                profile_map[None].append(node.uuid)
            for p in profiles:
                profile_map[p].append(node.uuid)

        # TODO(ryansb): add a check that all the flavors exist

        # map of flavor name -> associated profile
        flavor_profiles = {}
        for flavor in compute_client.flavors.list():
            if flavor.name not in [parsed_args.control_flavor,
                                   parsed_args.compute_flavor,
                                   parsed_args.ceph_storage_flavor,
                                   parsed_args.block_storage_flavor,
                                   parsed_args.swift_storage_flavor,
                                   ]:
                self.log.debug("Flavor {} isn't used in this deployment, "
                               "skipping it".format(flavor.name))
                continue

            profile = flavor.get_keys().get('capabilities:profile')

            if profile is None:
                self.total_fails += 1
                print("Error: flavor \"{}\" has no \"capabilities:profile\" "
                      "key".format(flavor.name))
                continue

            flavor_profiles[flavor.name] = profile

            if flavor.get_keys().get('capabilities:boot_option', '') \
                    != 'local':
                self.total_fails += 1
                print(('Error: Flavor {} "capabilities:boot_option" is '
                       'not set to "local"').format(flavor.name))
                print('Recommended solution: openstack flavor set --property '
                      '"cpu_arch"="x86_64" --property '
                      '"capabilities:boot_option"="local" ' + flavor.name)

        for target, flavor, scale in [
            ('control', parsed_args.control_flavor,
                parsed_args.control_scale),
            ('compute', parsed_args.compute_flavor,
                parsed_args.compute_scale),
            ('ceph-storage', parsed_args.ceph_storage_flavor,
                parsed_args.ceph_storage_scale),
            ('block-storage', parsed_args.block_storage_flavor,
                parsed_args.block_storage_scale),
            ('swift-storage', parsed_args.swift_storage_flavor,
                parsed_args.swift_storage_scale),
        ]:
            if scale == 0 or flavor is None:
                continue
            if flavor_profiles.get(flavor) is None:
                self.total_fails += 1
                print(('Warning: The flavor selected for --{}-flavor "{}" '
                      'has no profile associated').format(target, flavor))
                print('Recommendation: assign a profile with openstack flavor '
                      'set --property "cpu_arch"="x86_64" --property '
                      '"capabilities:profile"="PROFILE_NAME" {}'.format(
                          flavor))
                continue

            if len(profile_map[flavor_profiles.get(flavor, '')]) < scale:
                self.total_fails += 1
                print(("Error: {} of {} requested ironic nodes tagged to "
                       "profile {} (for flavor {})").format(
                           len(profile_map[flavor_profiles.get(flavor)]),
                           scale,
                           flavor_profiles[flavor],
                           flavor))
                print("Recommendation: tag more nodes using ironic node-"
                      "update <NODE ID> add properties/capabilities=profile:"
                      "{},boot_option:local".format(flavor_profiles[flavor]))

        if len(profile_map[None]):
            print(("Warning: There are {} ironic nodes with no profile that "
                   "will not be used: {}").format(
                       len(profile_map[None]),
                       ', '.join(profile_map[None])))

        if self.total_fails > 0:
            message = ("FAILED - {} checks failed, it's likely "
                       "that you should not proceed.").format(self.total_fails)
            print(message)
            self.log.error(message)
            sys.exit(99)
        print("SUCCESS: Validation passed!")
        return

    def _check_boot_images(self, node, kernel_id, ramdisk_id):
        self.log.debug("Doing boot checks for {}".format(node.uuid))
        message = ("FAIL node uuid={uuid} has an incorrectly configured "
                   "{property}. Expected \"{expected}\" but got "
                   "\"{actual}\". {extra}")
        if node.driver_info.get('deploy_ramdisk') != ramdisk_id:
            self.total_fails += 1
            print(message.format(
                uuid=node.uuid,
                property='driver_info/deploy_ramdisk',
                expected=ramdisk_id,
                actual=node.driver_info.get('deploy_ramdisk')
            ))
        if node.driver_info.get('deploy_kernel') != kernel_id:
            self.total_fails += 1
            print(message.format(
                uuid=node.uuid,
                property='driver_info/deploy_kernel',
                expected=ramdisk_id,
                actual=node.driver_info.get('deploy_kernel')
            ))
        if 'boot_option:local' not in node.properties.get('capabilities', ''):
            self.total_fails += 1
            print(message.format(
                uuid=node.uuid,
                property='properties/capabilities',
                expected='boot_option:local',
                actual=node.properties.get('capabilities')
            ))

    def get_parser(self, prog_name):
        parser = super(ValidateCapabilities,
                       self).get_parser(prog_name)
        # directly taken from overcloud_deploy command
        parser.add_argument('--control-scale', type=int)
        parser.add_argument('--compute-scale', type=int)
        parser.add_argument('--ceph-storage-scale', type=int)
        parser.add_argument('--block-storage-scale', type=int)
        parser.add_argument('--swift-storage-scale', type=int)
        parser.add_argument('--control-flavor',
                            help=_("Nova flavor to use for control nodes."))
        parser.add_argument('--compute-flavor',
                            help=_("Nova flavor to use for compute nodes."))
        parser.add_argument('--ceph-storage-flavor',
                            help=_("Nova flavor to use for ceph storage "
                                   "nodes."))
        parser.add_argument('--block-storage-flavor',
                            help=_("Nova flavor to use for cinder storage "
                                   "nodes."))
        parser.add_argument('--swift-storage-flavor',
                            help=_("Nova flavor to use for swift storage "
                                   "nodes."))
        return parser

    def _image_ids(self):
        image_client = self.app.client_manager.image
        try:
            kernel_id = osc_utils.find_resource(
                image_client.images, 'bm-deploy-kernel').id
        except AttributeError as e:
            print("ERROR: Please make sure there is only one image named "
                  "'bm-deploy-kernel' in glance.",
                  file=sys.stderr)
            self.log.exception(e)
            sys.exit(1)

        try:
            ramdisk_id = osc_utils.find_resource(
                image_client.images, 'bm-deploy-ramdisk').id
        except AttributeError as e:
            print("ERROR: Please make sure there is only one image named "
                  "'bm-deploy-ramdisk' in glance.",
                  file=sys.stderr)
            self.log.exception(e)
            sys.exit(1)

        return kernel_id, ramdisk_id

    def _check_flavors_exist(self, parsed_args):
        compute_client = self.app.client_manager.compute

        flavors = {f.name: f for f in compute_client.flavors.list()}

        message = "Warning: provided --{}-flavor, '{}', does not exist"

        for target, flavor in (
            ('control', parsed_args.control_flavor),
            ('compute', parsed_args.compute_flavor),
            ('ceph-storage', parsed_args.ceph_storage_flavor),
            ('block-storage', parsed_args.block_storage_flavor),
            ('swift-storage', parsed_args.swift_storage_flavor),
        ):
            if flavor is None:
                self.log.debug("No argument provided for "
                               "--{}-flavor".format(target))
            elif flavor not in flavors:
                self.total_fails += 1
                print(message.format(target, flavor))
