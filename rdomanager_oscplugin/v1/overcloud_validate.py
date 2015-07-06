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

from cliff import command
from six.moves import configparser

from rdomanager_oscplugin import utils


class GenerateTempestDeployerInput(command.Command):
    """Validates the functionality of an overcloud using Tempest"""

    auth_required = False
    log = logging.getLogger(__name__ + ".GenerateTempestDeployerInput")
    tempest_run_dir = os.path.join(os.path.expanduser("~"), "tempest")
    generated_partial_config_path = os.path.join(tempest_run_dir,
                                                 'overcloud.config')

    def _setup_dir(self):
        if not os.path.isdir(self.tempest_run_dir):
            os.mkdir(self.tempest_run_dir)

    def _generate_partial_config(self):
        config = configparser.ConfigParser()

        config.add_section('compute-feature-enabled')

        # Does the test environment support changing the admin password?
        # (default: false)
        # config.set('compute-feature-enabled', 'change_password', 'false')

        # Does the test environment support obtaining instance serial console
        # output? (default: true)
        # set in [nova.serial_console]->enabled
        config.set('compute-feature-enabled', 'console_output', 'false')

        # Does the test environment support resizing? (default: false)
        # http://post-office.corp.redhat.com/archives/openstack-management-team-list/2015-August/msg00307.html
        # config.set('compute-feature-enabled', 'resize', 'false')

        # Does the test environment support pausing? (default: true)
        # config.set('compute-feature-enabled', 'pause', 'true')

        # Does the test environment support shelving/unshelving?
        # (default: true)
        # config.set('compute-feature-enabled', 'shelve', 'true')

        # Does the test environment support suspend/resume? (default: true)
        # http://docs.openstack.org/developer/nova/support-matrix.html
        # config.set('compute-feature-enabled', 'suspend', 'true')

        # Does the test environment support live migration available?
        # (default: true)
        # http://docs.openstack.org/developer/nova/support-matrix.html
        # config.set('compute-feature-enabled', 'live_migration', 'true')

        # Does the test environment use block devices for live migration
        # (default: false)
        # config.set('compute-feature-enabled',
        #            'block_migration_for_live_migration', 'false')

        # Does the test environment block migration support cinder iSCSI
        # volumes. Note, libvirt doesn't support this, see
        # https://bugs.launchpad.net/nova/+bug/1398999 (default: false)
        # config.set('compute-feature-enabled', 'block_migrate_cinder_iscsi',
        #            'false')

        # Does the test system allow live-migration of paused instances? Note,
        # this is more than just the ANDing of paused and live_migrate, but
        # all 3 should be set to True to run those tests (default: false)
        # config.set('compute-feature-enabled',
        #            'live_migrate_paused_instances', 'false')

        # Enable VNC console. This configuration value should be same as
        # [nova.vnc]->vnc_enabled in nova.conf (default: false)
        # config.set('compute-feature-enabled', 'vnc_console', 'false')

        # Enable Spice console. This configuration value should be same as
        # [nova.spice]->enabled in nova.conf (default: false)
        # config.set('compute-feature-enabled', 'spice_console', 'false')

        # Enable RDP console. This configuration value should be same as
        # [nova.rdp]->enabled in nova.conf (default: false)
        # config.set('compute-feature-enabled', 'rdp_console', 'false')

        # Does the test environment support instance rescue mode?
        # (default: true)
        # http://docs.openstack.org/developer/nova/support-matrix.html
        # config.set('compute-feature-enabled', 'rescue', 'true')

        # Enables returning of the instance password by the relevant server
        # API calls such as create, rebuild or rescue. (default: true)
        # set in [nova]->enable_instance_password
        # config.set('compute-feature-enabled', 'enable_instance_password',
        #            'true')

        # Does the test environment support dynamic network interface
        # attachment? (default: true)
        # config.set('compute-feature-enabled', 'interface_attach', 'true')

        # Does the test environment support creating snapshot images of
        # running instances? (default: true)
        # http://docs.openstack.org/developer/nova/support-matrix.html
        # config.set('compute-feature-enabled', 'snapshot', 'true')

        # Does the test environment have the ec2 api running? (default: true)
        # set in [nova]->enabled_apis
        # config.set('compute-feature-enabled', 'ec2_api', 'true')

        # Does Nova preserve preexisting ports from Neutron when deleting an
        # instance? This should be set to True if testing Kilo+ Nova.
        # (default: false)
        # config.set('compute-feature-enabled', 'preserve_ports', 'false')


        # config.add_section('identity-feature-enabled')

        # Does the identity service have delegation and impersonation enabled
        # (default: true)
        # set in [keystone.trust]->enabled
        # config.set('identity-feature-enabled', 'trust', 'true')

        # Is the v2 identity API enabled (default: true)
        # curl -g -i -X GET http://192.0.2.8:5000/ lists both versions
        # config.set('identity-feature-enabled', 'api_v2', 'true')

        # Is the v3 identity API enabled (default: true)
        # curl -g -i -X GET http://192.0.2.8:5000/ lists both versions
        # config.set('identity-feature-enabled', 'api_v3', 'true')


        # config.add_section('image-feature-enabled')

        # Is the v2 image API enabled (default: true)
        # curl -g -i -X GET http://192.0.2.8:9292/ lists both versions
        # config.set('image-feature-enabled', 'api_v2', 'true')

        # Is the v1 image API enabled (default: true)
        # curl -g -i -X GET http://192.0.2.8:9292/ lists both versions
        # config.set('image-feature-enabled', 'api_v1', 'true')


        # config.add_section('network-feature-enabled')

        # Allow the execution of IPv6 tests (default: true)
        # config.set('network-feature-enabled', 'ipv6', 'true')

        # A list of enabled network extensions with a special entry all which
        # indicates every extension is enabled. Empty list indicates all
        # extensions are disabled (default: all)
        # config.set('network-feature-enabled', 'api_extensions', 'all')

        # Allow the execution of IPv6 subnet tests that use the extended IPv6
        # attributes ipv6_ra_mode and ipv6_address_mode (default: false)
        # config.set('network-feature-enabled', 'ipv6_subnet_attributes',
        #            'false')

        # Does the test environment support changing port admin state
        # (default: true)
        # config.set('network-feature-enabled', 'port_admin_state_change',
        #            'true')


        config.add_section('volume')

        # Name of the backend1 (must be declared in cinder.conf)
        # (default: 'BACKEND_1')
        # set in [cinder]->enabled_backends
        config.set('volume', 'backend1_name', 'tripleo_iscsi')

        # Name of the backend2 (must be declared in cinder.conf)
        # (default: 'BACKEND_2')
        # config.set('volume', 'backend2_name', 'BACKEND_2')

        # Backend protocol to target when creating volume types
        # (default: 'iSCSI')
        # config.set('volume', 'storage_protocol', 'iSCSI')

        # Backend vendor to target when creating volume types
        # (default: 'Open Source')
        # config.set('volume', 'vendor_name', 'Open Source')


        config.add_section('volume-feature-enabled')
        # Runs Cinder multi-backend test (requires 2 backends) (default: false)
        # single backend listed under [cinder]->enabled_backends
        # config.set('volume-feature-enabled', 'multi_backend', 'false')

        # Runs Cinder volumes backup test (default: true)
        # config.set('volume-feature-enabled', 'backup', 'true')

        # Runs Cinder volume snapshot test (default: true)
        # config.set('volume-feature-enabled', 'snapshot', 'true')

        # Is the v1 volume API enabled (default: true)
        # curl -g -i -X GET http://192.0.2.8:8776/ lists both versions
        # config.set('volume-feature-enabled', 'api_v1', 'true')

        # Is the v2 volume API enabled (default: true)
        # curl -g -i -X GET http://192.0.2.8:8776/ lists both versions
        # config.set('volume-feature-enabled', 'api_v2', 'true')

        # Update bootable status of a volume Not implemented on icehouse
        # (default: false)
        # python-cinderclient supports set-bootable
        config.set('volume-feature-enabled', 'bootable', 'true')


        config.add_section('object-storage')

        # Role to add to users created for swift tests to enable creating
        # containers (default: 'Member')
        # keystone role-list returns this role
        config.set('object-storage', 'operator_role', 'swiftoperator')

        # User role that has reseller admin (default: 'ResellerAdmin')
        # keystone role-list returns this role
        # config.set('object-storage', 'reseller_admin_role', 'ResellerAdmin')

        # Name of sync realm. A sync realm is a set of clusters that have
        # agreed to allow container syncing with each other. Set the same
        # realm name as Swift's container-sync-realms.conf (default: 'realm1')
        # container-sync-realms.conf doesn't exist
        # config.set('object-storage', 'realm_name', 'realm1')

        # One name of cluster which is set in the realm whose name is set in
        # 'realm_name' item in this file. Set the same cluster name as Swift's
        # container-sync-realms.conf (default: 'name1')
        # container-sync-realms.conf doesn't exist
        # config.set('object-storage', 'cluster_name', 'name1')


        # config.add_section('network')
        # network is not configured by RDO-Manager

        # The cidr block to allocate tenant ipv4 subnets from
        # (default: '10.100.0.0/16')
        # config.set('network', 'tenant_network_cidr', '192.168.0.0/24')

        # The mask bits for tenant ipv4 subnets (default: 28)
        # config.set('network', 'tenant_network_mask_bits', '28')

        # The cidr block to allocate tenant ipv6 subnets from
        # (default: '2003::/48')
        # config.set('network', 'tenant_network_v6_cidr', '2003::/48')

        # The mask bits for tenant ipv6 subnets (default: 64)
        # config.set('network', 'tenant_network_v6_mask_bits', '64')

        # Default floating network name. Used to allocate floating IPs when
        # neutron is enabled. (default: <None>)
        # config.set('network', 'floating_network_name', '<None>')

        # List of dns servers which should be used for subnet creation
        # (default: '8.8.8.8,8.8.4.4')
        # config.set('network', 'dns_servers', '8.8.8.8,8.8.4.4')

        # vnic_type to use when Launching instances with pre-configured ports.
        # Supported ports are: ['normal','direct','macvtap']
        # Allowed values: <None>, normal, direct, macvtap
        # (default: '<None>')
        # config.set('network', 'port_vnic_type', '<None>')

        config.add_section('orchestration')
        config.set('orchestration', 'stack_owner_role', 'heat_stack_user')

        with open(self.generated_partial_config_path, 'w+') as config_file:
            config.write(config_file)

    def _run_tempest(self, overcloud_auth_url, overcloud_admin_password,
                     network_id, deployer_input, tempest_args, skipfile):
        os.chdir(self.tempest_run_dir)

        if not deployer_input:
            self._generate_partial_config()
            deployer_input = self.generated_partial_config_path

        utils.run_shell('/usr/share/openstack-tempest-kilo/tools/'
                        'configure-tempest-directory')
        utils.run_shell('./tools/config_tempest.py --out etc/tempest.conf '
                        '--network-id %(network_id)s '
                        '--deployer-input %(partial_config_file)s '
                        '--debug --create '
                        'identity.admin_password %(admin_password)s '
                        'identity.uri %(auth_url)s '
                        'compute.image_ssh_user cirros '
                        'compute.ssh_user cirros '
                        'object-storage.operator_role swiftoperator '
                        'orchestration.stack_owner_role heat_stack_user ' %
                        {'network_id': network_id,
                         'partial_config_file': deployer_input,
                         'auth_url': overcloud_auth_url,
                         'admin_password': overcloud_admin_password})

        # args = ['./tools/run-tests.sh', ]

        # if tempest_args is not None:
        #     args.append(tempest_args)
        # if skipfile is not None:
        #     args.extend(['--skip-file', skipfile])

        # utils.run_shell(' '.join(args))

    def get_parser(self, prog_name):
        parser = super(GenerateTempestDeployerInput,
                       self).get_parser(prog_name)

        parser.add_argument('--overcloud-auth-url', required=True)
        parser.add_argument('--overcloud-admin-password', required=True)
        # parser.add_argument('--network-id', required=True)
        # parser.add_argument('--deployer-input')
        # parser.add_argument('--tempest-args')
        # parser.add_argument('--skipfile')

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

        self._setup_dir()
        self._run_tempest(parsed_args.overcloud_auth_url,
                          parsed_args.overcloud_admin_password,
                          parsed_args.network_id,
                          parsed_args.deployer_input,
                          parsed_args.tempest_args,
                          parsed_args.skipfile)
