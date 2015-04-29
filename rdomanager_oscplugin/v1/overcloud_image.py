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

    TRIPLEOPUPPETELEMENTS = "/usr/share/tripleo-puppet-elements"
    INSTACKUNDERCLOUDELEMENTS = "/usr/share/instack-undercloud-elements"
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

    DISCOVERY_IMAGE_ELEMENT = [
        'ironic-discoverd-ramdisk-instack',
        'delorean-rdo-management',
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
            "--name",
            dest="image_name",
            metavar='<image name>',
            help="Build image by name"
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
            help="Use RHOS release for repo management (debug only)"
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
            "--overcloud-full-dib-extra-args",
            dest="overcloud_full_dib_extra_args",
            default=os.environ.get(
                "OVERCLOUD_FULL_DIB_EXTRA_ARGS",
                " ".join(self.OVERCLOUD_FULL_DIB_EXTRA_ARGS)),
            help="Extra args for Overcloud Full",
        )
        parser.add_argument(
            "--overcloud-control-dib-extra-args",
            dest="overcloud_control_dib_extra_args",
            default=os.environ.get(
                "OVERCLOUD_CONTROL_DIB_EXTRA_ARGS",
                " ".join(self.OVERCLOUD_CONTROL_DIB_EXTRA_ARGS)),
            help="Extra args for Overcloud Control",
        )
        parser.add_argument(
            "--overcloud-compute-dib-extra-args",
            dest="overcloud_compute_dib_extra_args",
            default=os.environ.get(
                "OVERCLOUD_COMPUTE_DIB_EXTRA_ARGS",
                " ".join(self.OVERCLOUD_COMPUTE_DIB_EXTRA_ARGS)),
            help="Extra args for Overcloud Compute",
        )
        parser.add_argument(
            "--overcloud-cephstorage-dib-extra-args",
            dest="overcloud_cephstorage_dib_extra_args",
            default=os.environ.get(
                "OVERCLOUD_CEPHSTORAGE_DIB_EXTRA_ARGS",
                " ".join(self.OVERCLOUD_CEPHSTORAGE_DIB_EXTRA_ARGS)),
            help="Extra args for Overcloud Ceph Storage",
        )
        parser.add_argument(
            "--overcloud-cinder-dib-extra-args",
            dest="overcloud_cinder_dib_extra_args",
            default=os.environ.get(
                "OVERCLOUD_CINDER_DIB_EXTRA_ARGS",
                " ".join(self.OVERCLOUD_CINDER_DIB_EXTRA_ARGS)),
            help="Extra args for Overcloud Cinder",
        )
        parser.add_argument(
            "--overcloud-swift-dib-extra-args",
            dest="overcloud_swift_dib_extra_args",
            default=os.environ.get(
                "OVERCLOUD_SWIFT_DIB_EXTRA_ARGS",
                " ".join(self.OVERCLOUD_SWIFT_DIB_EXTRA_ARGS)),
            help="Extra args for Overcloud Swift",
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
            default=os.environ.get('DEPLOY_IMAGE_ELEMENT', 'deploy-ironic'),
            help="DIB elements for deploy image",
        )
        parser.add_argument(
            "--discovery-image-element",
            dest="discovery_image_element",
            default=os.environ.get(
                'DISCOVERY_IMAGE_ELEMENT',
                self.DISCOVERY_IMAGE_ELEMENT),
            help="DIB elements for discovery image",
        )
        return parser

    def _disk_image_create(self, args):
        subprocess.call('disk-image-create {0}'.format(args), shell=True)

    def _env_variable_or_set(self, key_name, default_value):
        os.environ[key_name] = os.environ.get(key_name, default_value)

    def _shell_source(self, path):
        pass    # TODO(bcrochet) custom load, no subprocess

    def _prepare_env_variables(self, parsed_args):
        os.environ['DIB_REPOREF_puppetlabs_concat'] = (
            '15ecb98dc3a551024b0b92c6aafdefe960a4596f')

        self._env_var_or_set('DIB_INSTALLTYPE_puppet_modules', 'source')

        # Attempt to detect host distribution if not specified
        if not parsed_args.node_dist:
            f = open('/etc/redhat-release', 'r')
            release = f.readline()
            if re.match('Red Hat Enterprise Linux', release):
                parsed_args.node_dist = 'rhel7'
            elif re.match('CentOS', release):
                parsed_args.node_dist = 'centos7'
            elif re.match('Fedora', release):
                parsed_args.node_dist = 'fedora'
            else:
                raise Exception(
                    "Could not detect distribution from /etc/redhat-release!")

        dib_common_elements = []
        if re.match('rhel7', parsed_args.node_dist):
            os.environ['REG_METHOD'] = parsed_args.reg_method
            os.environ['RHOS'] = '0'

            if parsed_args.run_rhos_release:
                self._env_var_or_set('RHOS_RELEASE', '6')
                dib_common_elements.append('rhos-release')
            else:
                dib_common_elements.append('selinux-permissive')
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
                    'rdo-juno',
                    'rdo-release',
                ])
            elif not os.environ.get('RHOS_RELEASE') == '0':
                dib_common_elements.append('rhos-release')

        self._env_var_or_set('PACKAGES', '1')
        if os.environ.get('PACKAGES') == '1':
            dib_common_elements.extend([
                'tripleo-image-elements',
                'undercloud-package-install',
                'pip-and-virtualenv-override',
            ])

        parsed_args.dib_common_elements = " ".join(dib_common_elements)

    def _build_image_ramdisk(self, parsed_args, ramdisk_type):
        image_name = os.environ.get("%s_NAME" % ramdisk_type.upper())
        if (not os.path.isfile("%s.initramfs" % image_name) or
           not os.path.isfile("%s.kernel" % image_name)):
            cmdline = ("ramdisk-image-create -a %(arch)s -o %(name)s "
                       "--ramdisk-element dracut-ramdisk %(node_dist)s "
                       "%(image_element)s %(dib_common_elements)s "
                       "2>&1 | tee dib-%(ramdisk_type)s.log" %
                       {
                           'arch': parsed_args.node_arch,
                           'name': image_name,
                           'node_dist': parsed_args.node_dist,
                           'image_element':
                               parsed_args["%s_IMAGE_ELEMENT" %
                                           ramdisk_type.upper()],
                           'dib_common_elements':
                               parsed_args.dib_common_elements,
                           'ramdisk_type': ramdisk_type,
                       })
            subprocess.call(cmdline)

    def _build_image_ramdisks(self, parsed_args):
        for ramdisk in ['deploy', 'discovery']:
            self._build_image_ramdisk(parsed_args, ramdisk)

    def _build_image_overcloud(self, parsed_args, node_type):
        image_name = "overcloud-%s.qcow2" % node_type
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
                            parsed_args["OVERCLOUD_%s_DIB_EXTRA_ARGS" %
                                        node_type],
                        'dib_common_elements':
                            parsed_args.dib_common_elements,
                        'image_type': node_type,
                    })
            self._disk_image_create(args)

    def _build_image_os_disk_config(self, parsed_args):
        image_name = "os-disk-config.qcow2"
        if not os.path.isfile(image_name):
            args = ("disk-image-create -a %(arch)s -o os-disk-config "
                    "%(node_dist)s os-disk-config baremetal 2>&1 | "
                    "tee dib-os-disk-config.log" %
                    {
                        'arch': parsed_args.node_arch,
                        'node_dist': parsed_args.node_dist,
                    })
            self._disk_image_create(args)

    def _build_image_overcloud_full(self, parsed_args):
        self._build_image_overcloud(parsed_args, 'full')

    def _build_image_overcloud_control(self, parsed_args):
        self._build_image_overcloud(parsed_args, 'control')

    def _build_image_overcloud_compute(self, parsed_args):
        self._build_image_overcloud(parsed_args, 'compute')

    def _build_image_overcloud_cinder_volume(self, parsed_args):
        self._build_image_overcloud(parsed_args, 'cinder-volume')

    def _build_image_overcloud_swift_storage(self, parsed_args):
        self._build_image_overcloud(parsed_args, 'swift-storage')

    def _build_image_openstack_all(self, parsed_args):
        self._build_image_overcloud_control(parsed_args)
        self._build_image_overcloud_compute(parsed_args)

    def _build_image_fedora_user(self):
        pass

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        self._prepare_env_variables(parsed_args)
        self.log.debug("Environment: %s" % os.environ)

        if parsed_args.all:
            self._build_image_ramdisks(parsed_args)
            self._build_image_openstack_all(parsed_args)
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
