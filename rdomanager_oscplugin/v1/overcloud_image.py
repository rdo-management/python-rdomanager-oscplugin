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

from __future__ import print_function

import logging
import os
import re
import requests
import shutil
import stat
import subprocess
import sys

from cliff import command
from openstackclient.common import exceptions
from openstackclient.common import utils
from prettytable import PrettyTable
from rdomanager_oscplugin import utils as plugin_utils


class BuildOvercloudImage(command.Command):
    """Build images for the overcloud"""

    auth_required = False
    log = logging.getLogger(__name__ + ".BuildOvercloudImage")

    TRIPLEOPUPPETELEMENTS = "/usr/share/tripleo-puppet-elements"
    INSTACKUNDERCLOUDELEMENTS = "/usr/share/instack-undercloud"
    PUPPET_COMMON_ELEMENTS = [
        'sysctl',
        'hosts',
        'baremetal',
        'dhcp-all-interfaces',
        'os-collect-config',
        'heat-config-puppet',
        'heat-config-script',
        'puppet-modules',
        'hiera',
        'os-net-config',
        'stable-interface-names',
        'grub2-deprecated',
        '-p python-psutil,python-debtcollector,plotnetcfg,sos,'
        'python-cisco-networking,python-UcsSdk'
    ]

    OVERCLOUD_FULL_DIB_EXTRA_ARGS = [
        'overcloud-full',
        'overcloud-controller',
        'overcloud-compute',
        'overcloud-ceph-storage',
        'ntp',
    ] + PUPPET_COMMON_ELEMENTS

    DISCOVERY_IMAGE_ELEMENT = [
        'ironic-discoverd-ramdisk-instack',
        'delorean-rdo-management',
    ]

    DEPLOY_IMAGE_ELEMENT = [
        'deploy-ironic'
    ]

    IMAGE_TYPES = [
        'deploy-ramdisk',
        'discovery-ramdisk',
        'fedora-user',
        'overcloud-full',
    ]

    def get_parser(self, prog_name):
        parser = super(BuildOvercloudImage, self).get_parser(prog_name)
        image_group = parser.add_mutually_exclusive_group(required=True)
        image_group.add_argument(
            "--all",
            dest="all",
            action="store_true",
            help="Build all images",
        )
        image_group.add_argument(
            "--type",
            dest="image_types",
            metavar='<image type>',
            choices=self.IMAGE_TYPES,
            action="append",
            help="Build image by name. One of "
                 "%s" % ", ".join(self.IMAGE_TYPES),
        )
        parser.add_argument(
            "--base-image",
            help="Image file to use as a base for new images",
        )
        parser.add_argument(
            "--instack-undercloud-elements",
            dest="instack_undercloud_elements",
            default=os.environ.get(
                "INSTACKUNDERCLOUDELEMENTS", self.INSTACKUNDERCLOUDELEMENTS),
            help="Path to Instack Undercloud elements",
        )
        parser.add_argument(
            "--tripleo-puppet-elements",
            dest="tripleo_puppet_elements",
            default=os.environ.get(
                "TRIPLEOPUPPETELEMENTS", self.TRIPLEOPUPPETELEMENTS),
            help="Path to TripleO Puppet elements",
        )
        parser.add_argument(
            "--elements-path",
            dest="elements_path",
            default=os.environ.get(
                "ELEMENTS_PATH",
                os.pathsep.join([
                    self.TRIPLEOPUPPETELEMENTS,
                    self.INSTACKUNDERCLOUDELEMENTS,
                    '/usr/share/tripleo-image-elements',
                    '/usr/share/diskimage-builder/elements',
                    '/usr/share/openstack-heat-templates/'
                    'software-config/elements',
                ])),
            help="Full elements path, separated by %s" % os.pathsep,
        )
        parser.add_argument(
            "--tmp-dir",
            dest="tmp_dir",
            default=os.environ.get("TMP_DIR", "/var/tmp"),
            help="Path to a temporary directory for creating images",
        )
        parser.add_argument(
            "--node-arch",
            dest="node_arch",
            default=os.environ.get("NODE_ARCH", "amd64"),
            help="Architecture of image to build",
        )
        parser.add_argument(
            "--node-dist",
            dest="node_dist",
            default=os.environ.get("NODE_DIST", ""),
            help="Distribution of image to build",
        )
        parser.add_argument(
            "--registration-method",
            dest="reg_method",
            default=os.environ.get("REG_METHOD", "disable"),
            help="Registration method",
        )
        parser.add_argument(
            "--run-rhos-release",
            dest="run_rhos_release",
            action='store_true',
            default=(os.environ.get('RUN_RHOS_RELEASE', '0') == '1'),
            help="Use RHOS release for repo management (debug only)"
        )
        parser.add_argument(
            "--use-delorean-trunk",
            dest="use_delorean_trunk",
            action='store_true',
            default=(os.environ.get('USE_DELOREAN_TRUNK', '0') == '1'),
            help="Use Delorean trunk repo",
        )
        parser.add_argument(
            "--delorean-trunk-repo",
            dest="delorean_trunk_repo",
            default=os.environ.get(
                'DELOREAN_TRUNK_REPO',
                'http://trunk.rdoproject.org/kilo/centos7/latest-RDO-kilo-CI/'
            ),
            help="URL to Delorean trunk repo",
        )
        parser.add_argument(
            "--delorean-repo-file",
            dest="delorean_repo_file",
            default=os.environ.get('DELOREAN_REPO_FILE', 'delorean-kilo.repo'),
            help="Filename for delorean repo config file",
        )
        parser.add_argument(
            "--overcloud-full-dib-extra-args",
            dest="overcloud_full_dib_extra_args",
            default=os.environ.get(
                "OVERCLOUD_FULL_DIB_EXTRA_ARGS",
                " ".join(self.OVERCLOUD_FULL_DIB_EXTRA_ARGS)),
            help="Extra args for Overcloud Full",
        )
        parser.add_argument(
            "--overcloud-full-name",
            dest="overcloud_full_name",
            default=os.environ.get('OVERCLOUD_FULL_NAME', 'overcloud-full'),
            help="Name of overcloud full image",
        )
        parser.add_argument(
            "--fedora-user-name",
            dest="fedora_user_name",
            default=os.environ.get('FEDORA_USER_NAME', 'fedora-user'),
            help="Name of Fedora user image",
        )
        parser.add_argument(
            "--deploy-name",
            dest="deploy_name",
            default=os.environ.get('DEPLOY_NAME', 'deploy-ramdisk-ironic'),
            help="Name of deployment ramdisk image",
        )
        parser.add_argument(
            "--discovery-name",
            dest="discovery_name",
            default=os.environ.get('DISCOVERY_NAME', 'discovery-ramdisk'),
            help="Name of discovery ramdisk image",
        )
        parser.add_argument(
            "--deploy-image-element",
            dest="deploy_image_element",
            default=os.environ.get(
                'DEPLOY_IMAGE_ELEMENT',
                " ".join(self.DEPLOY_IMAGE_ELEMENT)),
            help="DIB elements for deploy image",
        )
        parser.add_argument(
            "--discovery-image-element",
            dest="discovery_image_element",
            default=os.environ.get(
                'DISCOVERY_IMAGE_ELEMENT',
                " ".join(self.DISCOVERY_IMAGE_ELEMENT)),
            help="DIB elements for discovery image",
        )
        return parser

    def _disk_image_create(self, args):
        subprocess.call('disk-image-create {0}'.format(args), shell=True)

    def _ramdisk_image_create(self, args):
        subprocess.call('ramdisk-image-create {0}'.format(args), shell=True)

    def _env_var_or_set(self, key_name, default_value):
        os.environ[key_name] = os.environ.get(key_name, default_value)

    def _prepare_env_variables(self, parsed_args):
        self._env_var_or_set('ELEMENTS_PATH', parsed_args.elements_path)
        self._env_var_or_set('TMP_DIR', parsed_args.tmp_dir)
        self._env_var_or_set('DIB_DEFAULT_INSTALLTYPE', 'package')
        self._env_var_or_set(
            'DELOREAN_TRUNK_REPO', parsed_args.delorean_trunk_repo)
        self._env_var_or_set(
            'DELOREAN_REPO_FILE', parsed_args.delorean_repo_file)

        # Needed for corosync to be able to use hostnames
        # https://bugs.launchpad.net/tripleo/+bug/1447497
        os.environ['DIB_CLOUD_INIT_ETC_HOSTS'] = ''

        # Attempt to detect host distribution if not specified
        if not parsed_args.node_dist:
            with open('/etc/redhat-release', 'r') as f:
                release = f.readline()
            if re.match('Red Hat Enterprise Linux', release):
                parsed_args.node_dist = 'rhel7'
            elif re.match('CentOS', release):
                parsed_args.node_dist = 'centos7'
            elif re.match('Fedora', release):
                parsed_args.node_dist = 'fedora'
            else:
                raise Exception(
                    "Could not detect distribution from "
                    "/etc/redhat-release!")

        dib_common_elements = []
        if re.match('rhel7', parsed_args.node_dist):
            os.environ['REG_METHOD'] = parsed_args.reg_method

            if parsed_args.run_rhos_release:
                self._env_var_or_set('RHOS_RELEASE', '6')
                dib_common_elements.append('rhos-release')
            os.environ['DELOREAN_REPO_URL'] = parsed_args.delorean_trunk_repo
        elif re.match('centos7', parsed_args.node_dist):
            os.environ['DELOREAN_REPO_URL'] = parsed_args.delorean_trunk_repo
            dib_common_elements.extend([
                'selinux-permissive',
                'centos-cloud-repo',
            ])

            parsed_args.discovery_image_element = " ".join([
                'delorean-rdo-management',
                'ironic-discoverd-ramdisk-instack',
                'centos-cr',
            ])

        dib_common_elements.extend([
            'element-manifest',
            'network-gateway',
        ])

        self._env_var_or_set('RHOS', '0')
        self._env_var_or_set('RHOS_RELEASE', '0')

        if parsed_args.node_dist in ['rhel7', 'centos7']:
            self._env_var_or_set('FS_TYPE', 'xfs')

            if os.environ.get('RHOS') == '0':
                os.environ['RDO_RELEASE'] = 'kilo'
                dib_common_elements.extend([
                    'epel',
                    'rdo-release',
                ])
            elif not os.environ.get('RHOS_RELEASE') == '0':
                dib_common_elements.append('rhos-release')

        self._env_var_or_set('PACKAGES', '1')
        if os.environ.get('PACKAGES') == '1':
            dib_common_elements.extend([
                'undercloud-package-install',
                'pip-and-virtualenv-override',
            ])

        if parsed_args.use_delorean_trunk:
            dib_common_elements.append('delorean-repo')

        parsed_args.dib_common_elements = " ".join(dib_common_elements)

    def _build_image_ramdisk(self, parsed_args, ramdisk_type):
        image_name = vars(parsed_args)["%s_name" % ramdisk_type]
        if (not os.path.isfile("%s.initramfs" % image_name) or
           not os.path.isfile("%s.kernel" % image_name)):
            args = ("-a %(arch)s -o %(name)s "
                    "--ramdisk-element dracut-ramdisk %(node_dist)s "
                    "%(image_element)s %(dib_common_elements)s "
                    "2>&1 | tee dib-%(ramdisk_type)s.log" %
                    {
                        'arch': parsed_args.node_arch,
                        'name': image_name,
                        'node_dist': parsed_args.node_dist,
                        'image_element':
                            vars(parsed_args)["%s_image_element" %
                                              ramdisk_type],
                        'dib_common_elements':
                            parsed_args.dib_common_elements,
                        'ramdisk_type': ramdisk_type,
                    })
            self._ramdisk_image_create(args)

    def _build_image_ramdisks(self, parsed_args):
        self._build_image_ramdisk_deploy(parsed_args)
        self._build_image_ramdisk_discovery(parsed_args)

    def _build_image_ramdisk_deploy(self, parsed_args):
        self._build_image_ramdisk(parsed_args, 'deploy')

    def _build_image_ramdisk_discovery(self, parsed_args):
        self._build_image_ramdisk(parsed_args, 'discovery')

    def _build_image_overcloud(self, parsed_args, node_type):
        image_name = "%s.qcow2" % vars(parsed_args)['overcloud_%s_name' %
                                                    node_type]
        if not os.path.isfile(image_name):
            args = ("-a %(arch)s -o %(name)s "
                    "%(node_dist)s %(overcloud_dib_extra_args)s "
                    "%(dib_common_elements)s 2>&1 | "
                    "tee dib-overcloud-%(image_type)s.log" %
                    {
                        'arch': parsed_args.node_arch,
                        'name': image_name,
                        'node_dist': parsed_args.node_dist,
                        'overcloud_dib_extra_args':
                            vars(parsed_args)["overcloud_%s_dib_extra_args" %
                                              node_type],
                        'dib_common_elements':
                            parsed_args.dib_common_elements,
                        'image_type': node_type,
                    })
            self._disk_image_create(args)

    def _build_image_overcloud_full(self, parsed_args):
        self._build_image_overcloud(parsed_args, 'full')

    def _build_image_fedora_user(self, parsed_args):
        image_name = "%s.qcow2" % parsed_args.fedora_user_name
        if not os.path.isfile(image_name):
            if os.path.isfile('~/.cache/image-create/fedora-21.x86_64.qcow2'):
                # Just copy the already downloaded Fedora cloud image as
                # fedora-user.qcow2
                shutil.copy2(
                    '~/.cache/image-create/fedora-21.x86_64.qcow2',
                    image_name)
            else:
                # Download the image
                r = requests.get(
                    'http://cloud.fedoraproject.org/fedora-21.x86_64.qcow2')
                with open(image_name, 'wb') as f:
                    f.write(r.content)
            # The perms always seem to be wrong when copying out of the cache,
            # so fix them
            os.chmod(
                image_name,
                stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        self._prepare_env_variables(parsed_args)
        self.log.debug("Environment: %s" % os.environ)

        if parsed_args.all:
            self._build_image_ramdisks(parsed_args)
            self._build_image_overcloud_full(parsed_args)
            self._build_image_fedora_user(parsed_args)
        else:
            for image_type in parsed_args.image_types:
                {
                    'deploy-ramdisk': self._build_image_ramdisk_deploy,
                    'discovery-ramdisk': self._build_image_ramdisk_discovery,
                    'fedora-user': self._build_image_fedora_user,
                    'overcloud-full': self._build_image_overcloud_full,
                }[image_type](parsed_args)


class UploadOvercloudImage(command.Command):
    """Create overcloud glance images from existing image files."""
    auth_required = False
    log = logging.getLogger(__name__ + ".UploadOvercloudImage")

    def _env_variable_or_set(self, key_name, default_value):
        os.environ[key_name] = os.environ.get(key_name, default_value)

    def _delete_image_if_exists(self, image_client, name):
        try:
            image = utils.find_resource(image_client.images, name)
            image_client.images.delete(image.id)
        except exceptions.CommandError:
            self.log.debug('Image "%s" have already not existed, '
                           'no problem.' % name)

    def _get_image(self, name):
        try:
            image = utils.find_resource(self.app.client_manager.image.images,
                                        name)
        except exceptions.CommandError as e:
            # TODO(maufart): enhance error detection, when python-glanceclient
            # starts provide it https://bugs.launchpad.net/glance/+bug/1480156
            if 'More than one image exists' in e.args[0]:
                raise exceptions.CommandError(
                    'Image "%s" already exists in glance more than once,'
                    ' delete all copies except the first one.' % name
                )
            else:
                self.log.debug('Image "%s" does not exists, no problem.'
                               % name)
                return None
        return image

    def _image_changed(self, name, filename):
        image = utils.find_resource(self.app.client_manager.image.images,
                                    name)
        return image.checksum != plugin_utils.file_checksum(filename)

    def _check_file_exists(self, file_path):
        if not os.path.isfile(file_path):
            raise exceptions.CommandError(
                'Required file "%s" does not exist.' % file_path
            )

    def _read_image_file_pointer(self, dirname, filename):
        filepath = os.path.join(dirname, filename)
        self._check_file_exists(filepath)
        return open(filepath, 'rb')

    def _copy_file(self, src, dest):
        subprocess.check_call('sudo cp -f "{0}" "{1}"'.format(src, dest),
                              shell=True)

    def _image_try_update(self, image_name, image_file, parsed_args):
        image = self._get_image(image_name)
        if image:
            if self._image_changed(image_name, image_file):
                if parsed_args.update_existing:
                    self.app.client_manager.image.images.update(
                        image.id,
                        name='%s_%s' % (image.name, re.sub(r'[\-:\.]|(0+$)',
                                                           '',
                                                           image.created_at))
                    )
                    return None
                else:
                    print('Image "%s" already exists and can be updated'
                          ' with --update-existing.' % image_name)
                    return image
            else:
                print('Image "%s" is up-to-date, skipping.' % image_name)
                return image
        else:
            return None

    def _files_changed(self, filepath1, filepath2):
        return (plugin_utils.file_checksum(filepath1) !=
                plugin_utils.file_checksum(filepath2))

    def _file_create_or_update(self, src_file, dest_file, update_existing):
        if os.path.isfile(dest_file):
            if self._files_changed(src_file, dest_file):
                if update_existing:
                    self._copy_file(src_file, dest_file)
                else:
                    print('Image file "%s" already exists and can be updated'
                          ' with --update-existing.' % dest_file)
            else:
                print('Image file "%s" is up-to-date, skipping.' % dest_file)
        else:
            self._copy_file(src_file, dest_file)

    def _print_image_info(self, image):
        table = PrettyTable(['ID', 'Name', 'Disk Format', 'Size', 'Status'])
        table.add_row([image.id, image.name, image.disk_format, image.size,
                       image.status])
        print(table, file=sys.stdout)

    def _upload_image(self, *args, **kwargs):
        image = self.app.client_manager.image.images.create(*args, **kwargs)
        print('Image "%s" was uploaded.' % image.name, file=sys.stdout)
        self._print_image_info(image)
        return image

    def get_parser(self, prog_name):
        parser = super(UploadOvercloudImage, self).get_parser(prog_name)
        parser.add_argument(
            "--image-path",
            default=os.environ.get('IMAGE_PATH', './'),
            help="Path to directory containing image files",
        )
        parser.add_argument(
            "--os-image",
            default=os.environ.get('OS_IMAGE', 'overcloud-full.qcow2'),
            help="OpenStack disk image filename",
        )
        parser.add_argument(
            "--http-boot",
            default=os.environ.get('HTTP_BOOT', '/httpboot'),
            help="Root directory for discovery images",
        )
        parser.add_argument(
            "--update-existing",
            dest="update_existing",
            action="store_true",
            help="Update images if already exist",
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        self._env_variable_or_set('DEPLOY_NAME', 'deploy-ramdisk-ironic')
        self._env_variable_or_set('DISCOVERY_NAME', 'discovery-ramdisk')

        self.log.debug("checking if image files exist")

        image_files = [
            '%s.initramfs' % os.environ['DEPLOY_NAME'],
            '%s.kernel' % os.environ['DEPLOY_NAME'],
            '%s.initramfs' % os.environ['DISCOVERY_NAME'],
            '%s.kernel' % os.environ['DISCOVERY_NAME'],
            parsed_args.os_image
        ]

        for image in image_files:
            self._check_file_exists(os.path.join(parsed_args.image_path,
                                                 image))

        image_name = parsed_args.os_image.split('.')[0]

        self.log.debug("uploading overcloud images to glance")

        oc_vmlinuz_name = '%s-vmlinuz' % image_name
        oc_vmlinuz_file = '%s.vmlinuz' % image_name
        kernel = (self._image_try_update(oc_vmlinuz_name,
                                         oc_vmlinuz_file,
                                         parsed_args) or
                  self._upload_image(
                      name=oc_vmlinuz_name,
                      is_public=True,
                      disk_format='aki',
                      data=self._read_image_file_pointer(
                          parsed_args.image_path, oc_vmlinuz_file)
        ))

        oc_initrd_name = '%s-initrd' % image_name
        oc_initrd_file = '%s.initrd' % image_name
        ramdisk = (self._image_try_update(oc_initrd_name,
                                          oc_initrd_file,
                                          parsed_args) or
                   self._upload_image(
                       name=oc_initrd_name,
                       is_public=True,
                       disk_format='ari',
                       data=self._read_image_file_pointer(
                           parsed_args.image_path, oc_initrd_file)
        ))

        oc_name = image_name
        oc_file = '%s.qcow2' % image_name
        overcloud_image = (self._image_try_update(oc_name, oc_file,
                                                  parsed_args) or
                           self._upload_image(
                               name=oc_name,
                               is_public=True,
                               disk_format='qcow2',
                               container_format='bare',
                               properties={'kernel_id': kernel.id,
                                           'ramdisk_id': ramdisk.id},
                               data=self._read_image_file_pointer(
                                   parsed_args.image_path, oc_file)
        ))

        # check overcloud image links
        if (overcloud_image.properties['kernel_id'] != kernel.id or
                overcloud_image.properties['ramdisk_id'] != ramdisk.id):
            self.log.error('Link overcloud image to it\'s initrd and kernel'
                           ' images is MISSING OR leads to OLD image.'
                           ' You can keep it or fix it manually.')

        self.log.debug("uploading bm images to glance")

        deploy_kernel_name = 'bm-deploy-kernel'
        deploy_kernel_file = '%s.kernel' % os.environ['DEPLOY_NAME']
        self._image_try_update(deploy_kernel_name, deploy_kernel_file,
                               parsed_args) or self._upload_image(
            name=deploy_kernel_name,
            is_public=True,
            disk_format='aki',
            data=self._read_image_file_pointer(
                parsed_args.image_path,
                deploy_kernel_file)
        )

        deploy_ramdisk_name = 'bm-deploy-ramdisk'
        deploy_ramdisk_file = '%s.initramfs' % os.environ['DEPLOY_NAME']
        self._image_try_update(deploy_ramdisk_name, deploy_ramdisk_file,
                               parsed_args) or self._upload_image(
            name=deploy_ramdisk_name,
            is_public=True,
            disk_format='ari',
            data=self._read_image_file_pointer(parsed_args.image_path,
                                               deploy_ramdisk_file)
        )

        self.log.debug("copy discovery images to HTTP BOOT dir")

        self._file_create_or_update(
            os.path.join(parsed_args.image_path,
                         '%s.kernel' % os.environ['DISCOVERY_NAME']),
            os.path.join(parsed_args.http_boot, 'discovery.kernel'),
            parsed_args.update_existing
        )

        self._file_create_or_update(
            os.path.join(parsed_args.image_path,
                         '%s.initramfs' % os.environ['DISCOVERY_NAME']),
            os.path.join(parsed_args.http_boot, 'discovery.ramdisk'),
            parsed_args.update_existing
        )
