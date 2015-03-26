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
from openstackclient.common import exceptions
from openstackclient.common import utils
import os.path
import subprocess

from cliff import command


class BuildPlugin(command.Command):
    """Overcloud Image Build plugin"""

    auth_required = False
    log = logging.getLogger(__name__ + ".BuildPlugin")

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)
        pass


class CreatePlugin(command.Command):
    """Overcloud Image Create plugin"""
    auth_required = False
    log = logging.getLogger(__name__ + ".CreatePlugin")

    def get_parser(self, prog_name):
        parser = super(CreatePlugin, self).get_parser(prog_name)
        parser.add_argument(
            "--image-path",
            default='./',
            help="",
        )
        parser.add_argument(
            "--deploy-name",
            default='deploy-ramdisk-ironic',
            help="",
        )
        parser.add_argument(
            "--discovery-name",
            default='discovery-ramdisk',
            help="",
        )
        parser.add_argument(
            "--tftp-root",
            default='/tftpboot',
            help="",
        )
        parser.add_argument(
            "--os-image",
            default='openstack-full.qcow2',
            help="",
        )
        return parser

    def _find_by_name(self, list, name):
        return utils.find_resource(list, name)

    def _read_image_file(self, dir, file):
        open('{0}{1}'.format(dir, file)).read()

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)
        image_files = [
            '%s.initramfs' % parsed_args.deploy_name,
            '%s.kernel' % parsed_args.deploy_name,
            '%s.initramfs' % parsed_args.discovery_name,
            '%s.kernel' % parsed_args.discovery_name,
            parsed_args.os_image
        ]

        image_client = self.app.client_manager.image
        compute_client = self.app.client_manager.compute

        self.log.debug("check image files")

        for image in image_files:
            image_path = parsed_args.image_path + image
            if not os.path.isfile(image_path):
                print('ERROR: Image file "%s" does not exist' % image_path)
                return

        subprocess.call('tripleo load-image -d {0}{1}'.format(
            parsed_args.image_path,
            parsed_args.os_image),
            shell=True)

        self.log.debug("prepare glance images")

        try:
            bm_deploy_kernel = utils.find_resource(image_client.images,
                                                   'bm_deploy_kernel')
            image_client.images.delete(bm_deploy_kernel.id)
        except exceptions.CommandError:
            self.log.exception("Image bm_deploy_kernel have already not "
                               "existed, no problem.")
        try:
            bm_deploy_ramdisk = utils.find_resource(image_client.images,
                                                    'bm_deploy_ramdisk')
            image_client.images.delete(bm_deploy_ramdisk.id)
        except exceptions.CommandError:
            self.log.exception("Image bm_deploy_ramdisk have already not "
                               "existed, no problem.")

        kernel_id = image_client.images.create(
            name='bm_deploy_kernel',
            is_public=True,
            disk_format='aki',
            data=self._read_image_file(parsed_args.image_path,
                                       '%s.kernel' %
                                       parsed_args.deploy_name)
        ).id

        ramdisk_id = image_client.images.create(
            name='bm_deploy_ramdisk',
            is_public=True,
            disk_format='ari',
            data=self._read_image_file(parsed_args.image_path,
                                       '%s.initramfs' %
                                       parsed_args.deploy_name)
        ).id

        try:
            utils.find_resource(compute_client.flavors, 'baremetal')
        except exceptions.CommandError:
            compute_client.flavors.create('baremetal', 4096, 1, 40, 1)

        self.log.debug("prepare flavor")

        compute_client.flavors.find(name='baremetal').set_keys({
            'cpu_arch': 'x86_64',
            'baremetal:deploy_kernel_id': kernel_id,
            'baremetal:deploy_ramdisk_id': ramdisk_id,
            'baremetal:localboot': 'true'})

        self.log.debug("copy images to TFTP")

        subprocess.call('sudo cp -f "{0}{1}.kernel" '
                        '"{2}/discovery.kernel"'.
                        format(parsed_args.image_path,
                               parsed_args.discovery_name,
                               parsed_args.tftp_root),
                        shell=True)

        subprocess.call('sudo cp -f "{0}{1}.initramfs" '
                        '"{2}/discovery.ramdisk"'.
                        format(parsed_args.image_path,
                               parsed_args.discovery_name,
                               parsed_args.tftp_root),
                        shell=True)
