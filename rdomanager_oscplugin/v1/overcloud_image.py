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
import os.path
from openstackclient.common import utils
# from IPython import embed

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

    def _error(self, text='', subject=''):
      print("ERROR: {0} {1}".format(text, subject))
      exit(1)

    def _find_by_name(self, list, name):
        return utils.find_resource(list, name)

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)
        image_files = [
            '%s.initramfs' % parsed_args.deploy_name,
            '%s.kernel' % parsed_args.deploy_name,
            '%s.initramfs' % parsed_args.discovery_name,
            '%s.kernel' % parsed_args.discovery_name,
            parsed_args.os_image
        ]

        # print(dir(self.app.client_manager.image.images.delete('testimg')))

        image_client = self.app.client_manager.image
        compute_client = self.app.client_manager.compute

        print(image_client.images)
        print(dir(compute_client))

        self.log.debug("check image files")
        for image in image_files:
            image_path = parsed_args.image_path + image
            if not os.path.isfile(image_path):
                print('ERROR: Image file "%s" does not exist' % image_path)
                # return

        # TODO: subprocess.call("tripleo load-image -d {image_path}{os_image}")

        self.log.debug("prepare glance images")
        try:
            bm_deploy_kernel = utils.find_resource(image_client.images, 'testimg')
            image_client.images.delete(bm_deploy_kernel.id)
        except Exception:   # TODO: better?
            pass
        try:
            bm_deploy_ramdisk = utils.find_resource(image_client.images, 'testimg')
            image_client.images.delete(bm_deploy_ramdisk.id)
        except Exception:   # TODO: better?
            pass

        # embed()

        image_client.images.create({'name': 'bm_deploy_kernel', 'is_public': True,
                            'disk_format': 'aki',
                            'data': open('{0}{1}.kernel'.format(
                                parsed_args.image_path,
                                parsed_args.deploy_name)).read()})  # TODO: do it better?

        # glance_mngr.images.create({'name': 'bm_deploy_ramdisk', 'is_public': True,
        #                    'disk_format': 'ari', 'data': '.initramfs'})

        self.log.debug("prepare flavor")

        self.log.debug("copy images to TFTP")
