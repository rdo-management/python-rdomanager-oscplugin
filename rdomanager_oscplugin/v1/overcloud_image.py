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
import re
import subprocess

from cliff import command
from openstackclient.common import exceptions
from openstackclient.common import utils


class BuildOvercloudImage(command.Command):
    """Build images for the overcloud"""

    auth_required = False
    log = logging.getLogger(__name__ + ".BuildOvercloudImage")

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
            "--name",
            dest="image_name",
            metavar='<image name>',
            help="Build image by name"
        )
        parser.add_argument(
            "--base-image",
            help="Image file to use as a base for new images",
        )
        return parser

    def _disk_image_create(self, args):
        subprocess.call('disk-image-create {0}'.format(args), shell=True)

    def _env_variable_or_set(self, key_name, default_value):
        os.environ[key_name] = os.environ.get(key_name, default_value)

    def _shell_source(self, path):
        pass    # TODO(bcrochet) custom load, no subprocess

    def _prepare_env_variables(self):
        os.environ['DIB_REPOREF_puppetlabs_concat'] = (
            '15ecb98dc3a551024b0b92c6aafdefe960a4596f')
        INSTACKUNDERCLOUDELEMENTS = '/usr/share/instack-undercloud'
        # This is not the best. Open to suggestions? The old script
        # had this, but I don't think it works in this context.
        if not os.path.isdir(INSTACKUNDERCLOUDELEMENTS):
            INSTACKUNDERCLOUDELEMENTS = os.path.join(
                os.path.dirname(__file__),
                '..',
                'elements'
            )

        TRIPLEOPUPPETELEMENTS = '/usr/share/tripleo-puppet-elements'
        # Same as above. Needs some TLC.
        if not os.path.isdir(TRIPLEOPUPPETELEMENTS):
            TRIPLEOPUPPETELEMENTS = os.path.join(
                os.curdir, 'tripleo-puppet-elements', 'elements')

        self._env_var_or_set(
            'ELEMENTS_PATH',
            os.pathsep.join(
                TRIPLEOPUPPETELEMENTS,
                INSTACKUNDERCLOUDELEMENTS,
                os.path.join(
                    'usr', 'share', 'tripleo-image-elements'),
                os.path.join(
                    'usr', 'share', 'disimage-builder', 'elements'),
                os.path.join(
                    'usr', 'share', 'openstack-heat-templates',
                    'software-config', 'elements')))

        self._env_var_or_set('TMP_DIR', '/var/tmp')
        self._env_var_or_set('NODE_ARCH', 'amd64')

        self._env_var_or_set('DIB_INSTALLTYPE_puppet_modules', 'source')
        self._env_var_or_set(
            'DELOREAN_TRUNK_REPO',
            'http://trunk.rdoproject.org/kilo/centos7/latest-RDO-kilo-CI/')

        node_dist = os.environ.get('NODE_DIST', '')
        if not node_dist:
            f = open('/etc/redhat-release', 'r')
            release = f.readline()
            if re.match('Red Hat Enterprise Linux', release):
                node_dist = 'rhel7'
            elif re.match('CentOS', release):
                node_dist = 'centos7'
            elif re.match('Fedora', release):
                node_dist = 'fedora'
            else:
                # TODO(bcrochet): better exception than this
                raise Exception(
                    "Could not detect distribution from /etc/redhat-release!")
            os.environ['NODE_DIST'] = node_dist

        if re.match('rhel7', node_dist):
            self._env_var_or_set('REG_METHOD', 'disable')
            os.environ['RHOS'] = '0'
            self._env_var_or_set('RUN_RHOS_RELEASE', '0')
            if os.environ['RUN_RHOS_RELEASE'] == 1:
                self._env_var_or_set('RHOS_RELEASE', '6')
                os.environ['DIB_COMMON_ELEMENTS'] = 'rhos-release'
            else:
                os.environ['DIB_COMMON_ELEMENTS'] = 'selinux-permissive'
            os.environ['DELOREAN_REPO_URL'] = os.environ['DELOREAN_TRUNK_REPO']
        elif re.match('centos7', node_dist):
            os.environ['DELOREAN_REPO_URL'] = os.environ['DELOREAN_TRUNK_REPO']
            os.environ['DIB_COMMON_ELEMENTS'] = " ".join([
                'selinux-permissive',
                'centos-cloud-repo',
            ])
            os.environ['DISCOVERY_IMAGE_ELEMENT'] = " ".join([
                'delorean-rdo-management',
                'ironic-discoverd-ramdisk-instack',
                'centos-cr',
            ])
        self._env_var_or_set('DEPLOY_IMAGE_ELEMENT', 'deploy-ironic')
        self._env_var_or_set('DEPLOY_NAME', 'deploy-ramdisk-ironic')
        self._env_var_or_set('DISCOVERY_IMAGE_ELEMENT', " ".join([
            'ironic-discoverd-ramdisk-instack',
            'delorean-rdo-management',
        ]))
        self._env_var_or_set('DISCOVERY_NAME', 'discovery-ramdisk')

        self._env_var_or_set('DIB_COMMON_ELEMENTS', '')
        os.environ['DIB_COMMON_ELEMENTS'] = " ".join([
            os.environ.get('DIB_COMMON_ELEMENTS'),
            'element-manifest',
            'network-gateway',
        ]).strip()

        self._env_var_or_set('RHOS', '0')
        self._env_var_or_set('RHOS_RELEASE', '0')

        if os.environ.get('NODE_DIST') in ['rhel7', 'centos7']:
            self._env_var_or_set('FS_TYPE', 'xfs')

            if os.environ.get('RHOS') == '0':
                os.environ['RDO_RELEASE'] = 'kilo'
                os.environ['DIB_COMMON_ELEMENTS'] = " ".join([
                    os.environ.get('DIB_COMMON_ELEMENTS'),
                    'epel',
                    'rdo-juno',
                    'rdo-release',
                ]).strip()
            elif not os.environ.get('RHOS_RELEASE') == '0':
                os.environ['DIB_COMMON_ELEMENTS'] = " ".join([
                    os.environ.get('DIB_COMMON_ELEMENTS'),
                    'rhos-release',
                ]).strip()

        self._env_var_or_set('PACKAGES', '1')
        if os.environ.get('PACKAGES') == '1':
            os.environ['DIB_COMMON_ELEMENTS'] = " ".join([
                os.environ.get('DIB_COMMON_ELEMENTS'),
                'tripleo-image-elements',
                'undercloud-package-install',
                'pip-and-virtualenv-override',
            ]).strip()

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
            'delorean-repo',
            'stable-interface-names',
            'grub2',
            '-p python-psutil,python-debtcollector',
        ]

        OVERCLOUD_FULL_DIB_EXTRA_ARGS = [
            'overcloud-full',
            'overcloud-controller',
            'overcloud-compute',
            'overcloud-ceph-storage',
        ] + PUPPET_COMMON_ELEMENTS

        OVERCLOUD_CONTROL_DIB_EXTRA_ARGS = [
            'overcloud-controller',
        ] + PUPPET_COMMON_ELEMENTS

        OVERCLOUD_COMPUTE_DIB_EXTRA_ARGS = [
            'overcloud-compute',
        ] + PUPPET_COMMON_ELEMENTS

        OVERCLOUD_CEPHSTORAGE_DIB_EXTRA_ARGS = [
            'overcloud-ceph-storage',
        ] + PUPPET_COMMON_ELEMENTS

        OVERCLOUD_CINDER_DIB_EXTRA_ARGS = [
            'baremetal',
            'base',
            'cinder-lio',
            'common-venv',
            'dhcp-all-interfaces',
            'hosts',
            'ntp',
            'os-collect-config',
            'pip-cache',
            'pypi-openstack',
            'snmpd',
            'stable-interface-names',
            'use-ephemeral',
            'sysctl',
        ]

        OVERCLOUD_SWIFT_DIB_EXTRA_ARGS = [
            'pip-cache',
            'pypi-openstack',
            'swift-storage',
            'os-collect-config',
            'baremetal',
            'base',
            'common-venv',
            'dhcp-all-interfaces',
            'hosts',
            'ntp',
            'snmpd',
            'stable-interface-names',
            'use-ephemeral',
            'os-refresh-config-reboot',
            'sysctl',
        ]

        self._env_var_or_set('OVERCLOUD_FULL_DIB_EXTRA_ARGS',
                             " ".join(OVERCLOUD_FULL_DIB_EXTRA_ARGS))

        self._env_var_or_set('OVERCLOUD_CONTROL_DIB_EXTRA_ARGS',
                             " ".join(OVERCLOUD_CONTROL_DIB_EXTRA_ARGS))

        self._env_var_or_set('OVERCLOUD_COMPUTE_DIB_EXTRA_ARGS',
                             " ".join(OVERCLOUD_COMPUTE_DIB_EXTRA_ARGS))

        self._env_var_or_set('OVERCLOUD_CEPHSTORAGE_DIB_EXTRA_ARGS',
                             " ".join(OVERCLOUD_CEPHSTORAGE_DIB_EXTRA_ARGS))

        self._env_var_or_set('OVERCLOUD_CINDER_DIB_EXTRA_ARGS',
                             " ".join(OVERCLOUD_CINDER_DIB_EXTRA_ARGS))

        self._env_var_or_set('OVERCLOUD_SWIFT_DIB_EXTRA_ARGS',
                             " ".join(OVERCLOUD_SWIFT_DIB_EXTRA_ARGS))

    def _build_image_ramdisk(self, ramdisk_type):
        image_name = os.environ.get("%s_NAME" % ramdisk_type.upper())
        if (not os.path.isfile("%s.initramfs" % image_name) or
           not os.path.isfile("%s.kernel" % image_name)):
            cmdline = ("ramdisk-image-create -a %(arch)s -o %(name)s "
                       "--ramdisk-element dracut-ramdisk %(node_dist)s "
                       "%(image_element)s %(dib_common_elements)s "
                       "2>&1 | tee dib-%(ramdisk_type)s.log" %
                       {
                           'arch': os.environ.get('NODE_ARCH'),
                           'name': image_name,
                           'node_dist': os.environ.get('NODE_DIST'),
                           'image_element':
                               os.environ.get(
                                   "%s_IMAGE_ELEMENT" % ramdisk_type.upper()),
                           'dib_common_elements':
                               os.environ.get('DIB_COMMON_ELEMENTS'),
                           'ramdisk_type': ramdisk_type,
                       })
            subprocess.call(cmdline)

    def _build_image_ramdisks(self):
        for ramdisk in ['deploy', 'discovery']:
            self._build_image_ramdisk(ramdisk)

    def _build_image_overcloud(self, node_type):
        image_name = "overcloud-%s.qcow2" % node_type
        if not os.path.isfile(image_name):
            cmdline = ("disk-image-create -a %(arch)s -o %(name)s "
                       "%(node_dist)s %(overcloud_dib_extra_args)s "
                       "%(dib_common_elements)s 2>&1 | "
                       "tee dib-overcloud-%(image_type)s.log" %
                       {
                           'arch': os.environ.get('NODE_ARCH'),
                           'name': image_name,
                           'node_dist': os.environ.get('NODE_DIST'),
                           'overcloud_dib_extra_args':
                               os.environ.get(
                                   "OVERCLOUD_%s_DIB_EXTRA_ARGS" %
                                   node_type),
                           'dib_common_elements':
                                os.environ.get('DIB_COMMON_ELEMENTS'),
                           'image_type': node_type,
                       })
            subprocess.call(cmdline)

    def _build_image_os_disk_config(self):
        image_name = "os-disk-config.qcow2"
        if not os.path.isfile(image_name):
            cmdline = ("disk-image-create -a %(arch)s -o os-disk-config "
                       "%(node_dist)s os-disk-config baremetal 2>&1 | "
                       "tee dib-os-disk-config.log" %
                       {
                           'arch': os.environ.get('NODE_ARCH'),
                           'node_dist': os.environ.get('NODE_DIST'),
                       })
            subprocess.call(cmdline)

    def _build_image_overcloud_full(self):
        _build_image_overcloud('full')

    def _build_image_overcloud_control(self):
        _build_image_overcloud('control')

    def _build_image_overcloud_compute(self):
        _build_image_overcloud('compute')

    def _build_image_overcloud_cinder_volume(self):
        _build_image_overcloud('cinder-volume')

    def _build_image_overcloud_swift_storage(self):
        _build_image_overcloud('swift-storage')

    def _build_image_fedora_user(self):
        pass

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        self._prepare_env_variables()
        self.log.debug("Environment: %s" % os.environ)

        if parsed_args.all:
            self._build_image_ramdisks()
            self._build_image_openstack_all()
        else:
            self._disk_image_create(parsed_args.name)


class CreateOvercloud(command.Command):
    """Create overcloud glance images from existing image files."""
    auth_required = False
    log = logging.getLogger(__name__ + ".CreateOvercloud")

    def _env_variable_or_set(self, key_name, default_value):
        os.environ[key_name] = os.environ.get(key_name, default_value)

    def _delete_image_if_exists(self, image_client, name):
        try:
            image = utils.find_resource(image_client.images, name)
            image_client.images.delete(image.id)
        except exceptions.CommandError:
            self.log.debug('Image "%s" have already not existed, '
                           'no problem.' % name)

    def _check_file_exists(self, file_path):
        if not os.path.isfile(file_path):
            print('ERROR: Required file "%s" does not exist' % file_path)
            exit(1)

    def _read_image_file_pointer(self, dirname, filename):
        filepath = os.path.join(dirname, filename)
        self._check_file_exists(filepath)
        return open(filepath, 'rb')

    def _copy_file(self, src, dest):
        subprocess.call('sudo cp -f "{0}" "{1}"'.format(src, dest), shell=True)

    def _load_image(self, image_path, image_name, image_client):
        self.log.debug("uploading images to glance")

        kernel_id = image_client.images.create(
            name='%s-vmlinuz' % image_name,
            is_public=True,
            disk_format='aki',
            data=self._read_image_file_pointer(image_path,
                                               '%s.vmlinuz' % image_name)
        ).id

        ramdisk_id = image_client.images.create(
            name='%s-initrd' % image_name,
            is_public=True,
            disk_format='ari',
            data=self._read_image_file_pointer(image_path,
                                               '%s.initrd' % image_name)
        ).id

        image_client.images.create(
            name=image_name,
            is_public=True,
            disk_format='qcow2',
            container_format='bare',
            properties={'kernel_id': kernel_id, 'ramdisk_id': ramdisk_id},
            data=self._read_image_file_pointer(image_path,
                                               '%s.qcow2' % image_name)
        )

    def get_parser(self, prog_name):
        parser = super(CreateOvercloud, self).get_parser(prog_name)
        parser.add_argument(
            "--image-path",
            default='./',
            help="Path to directory containing image files",
        )
        parser.add_argument(
            "--os-image",
            default='overcloud-full.qcow2',
            help="OpenStack disk image filename",
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)
        image_client = self.app.client_manager.image

        self._env_variable_or_set('DEPLOY_NAME', 'deploy-ramdisk-ironic')
        self._env_variable_or_set('DISCOVERY_NAME', 'discovery-ramdisk')
        self._env_variable_or_set('TFTP_ROOT', '/tftpboot')

        self.log.debug("check image files")

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

        self.log.debug("prepare glance images")

        self._load_image(parsed_args.image_path,
                         parsed_args.os_image.split('.')[0],
                         image_client)

        self._delete_image_if_exists(image_client, 'bm_deploy_kernel')
        self._delete_image_if_exists(image_client, 'bm_deploy_ramdisk')

        image_client.images.create(
            name='bm-deploy-kernel',
            is_public=True,
            disk_format='aki',
            data=self._read_image_file_pointer(parsed_args.image_path,
                                               '%s.kernel' %
                                               os.environ['DEPLOY_NAME'])
        )

        image_client.images.create(
            name='bm-deploy-ramdisk',
            is_public=True,
            disk_format='ari',
            data=self._read_image_file_pointer(parsed_args.image_path,
                                               '%s.initramfs' %
                                               os.environ['DEPLOY_NAME'])
        )

        self.log.debug("copy discovery images to TFTP")

        self._copy_file(
            os.path.join(parsed_args.image_path,
                         '%s.kernel' % os.environ['DISCOVERY_NAME']),
            os.path.join(os.environ['TFTP_ROOT'], 'discovery.kernel')
        )

        self._copy_file(
            os.path.join(parsed_args.image_path,
                         '%s.initramfs' % os.environ['DISCOVERY_NAME']),
            os.path.join(os.environ['TFTP_ROOT'], 'discovery.ramdisk')
        )
