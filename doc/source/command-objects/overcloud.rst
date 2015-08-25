=========
overcloud
=========

Overcloud v1

overcloud deploy stack
----------------------

Deploy an overcloud stack

.. program:: overcloud deploy stack
.. code:: bash

    openstack overcloud deploy stack
        (--plan PLAN | --templates [TEMPLATES])
        [-t <TIMEOUT>]
        [--control-scale CONTROL_SCALE]
        [--compute-scale COMPUTE_SCALE]
        [--ceph-storage-scale CEPH_STORAGE_SCALE]
        [--block-storage-scale BLOCK_STORAGE_SCALE]
        [--swift-storage-scale SWIFT_STORAGE_SCALE]
        [--control-flavor CONTROL_FLAVOR]
        [--compute-flavor COMPUTE_FLAVOR]
        [--ceph-storage-flavor CEPH_STORAGE_FLAVOR]
        [--block-storage-flavor BLOCK_STORAGE_FLAVOR]
        [--swift-storage-flavor SWIFT_STORAGE_FLAVOR]
        [--neutron-flat-networks NEUTRON_FLAT_NETWORKS]
        [--neutron-physical-bridge NEUTRON_PHYSICAL_BRIDGE]
        [--neutron-bridge-mappings NEUTRON_BRIDGE_MAPPINGS]
        [--neutron-public-interface NEUTRON_PUBLIC_INTERFACE]
        [--hypervisor-neutron-public-interface HYPERVISOR_NEUTRON_PUBLIC_INTERFACE]
        [--neutron-network-type NEUTRON_NETWORK_TYPE]
        [--neutron-tunnel-types NEUTRON_TUNNEL_TYPES]
        [--neutron-disable-tunneling]
        [--neutron-network-vlan-ranges NEUTRON_NETWORK_VLAN_RANGES]
        [--neutron-mechanism-drivers NEUTRON_MECHANISM_DRIVERS]
        [--libvirt-type LIBVIRT_TYPE]
        [--ntp-server NTP_SERVER] [--cinder-lvm]
        [--tripleo-root TRIPLEO_ROOT]
        [--nodes-json NODES_JSON]
        [--no-proxy NO_PROXY] [-O <OUTPUT DIR>]
        [-e <HEAT ENVIRONMENT FILE>] [--rhel-reg]
        [--reg-method {satellite,portal}]
        [--reg-org REG_ORG] [--reg-force]
        [--reg-sat-url REG_SAT_URL]
        [--reg-activation-key REG_ACTIVATION_KEY]

.. option:: --plan <name or UUID>

    The Name or UUID of the Tuskar plan to deploy.

.. option:: --templates <directory>

    The directory containing the Heat templates to deploy.

.. option:: -t <timeout>, --timeout <timeout>

    Deployment timeout in minutes (default: 240)

.. option:: --control-scale <scale-amount>

    New number of control nodes.

.. option:: --compute-scale <scale-amount>

    New number of compute nodes.

.. option:: --ceph-storage-scale <scale-amount>

    New number of ceph storage nodes.

.. option:: --block-storage-scale <scale-amount>

    New number of block storage nodes.

.. option:: --swift-storage-scale <scale-amount>

    New number of swift storage nodes.

.. option:: --control-flavor <flavor-name>

    Nova flavor to use for control nodes.

.. option:: --compute-flavor <flavor-name>

    Nova flavor to use for compute nodes.

.. option:: --ceph-storage-flavor <flavor-name>

    Nova flavor to use for ceph storage nodes.

.. option:: --block-storage-flavor <flavor-name>

    Nova flavor to use for cinder storage nodes.

.. option:: --swift-storage-flavor <flavor-name>

    Nova flavor to use for swift storage nodes.

.. option:: --neutron-flat-networks <networks>

    Comma separated list of physical_network names with which flat networks
    can be created. Use * to allow flat networks with arbitrary
    physical_network names. (default: 'datacentre')

.. option:: --neutron-physical-bridge <bridge>

    Deprecated.

.. option:: --neutron-bridge-mappings <mappings>

    Comma separated list of bridge mappings. (default: datacentre:br-ex)

.. option:: --neutron-public-interface <interface>

    Deprecated.

.. option:: --hypervisor-neutron-public-interface <interface>

    Deprecated.

.. option:: --neutron-network-type <type>

    The network type for the tenant networks.

.. option:: --neutron-tunnel-types <type>

    Network types supported by the agent (gre and/or vxlan).

.. option:: --neutron-disable-tunneling

    Disables tunneling.

.. option:: --neutron-network-vlan-ranges <ranges>

    Comma separated list of <physical_network>:<vlan_min>:<vlan_max> or
    <physical_network> specifying physical_network names usable for VLAN
    provider and tenant networks, as well as ranges of VLAN tags on each
    available for allocation to tenant networks. (ex: datacentre:1:1000)

.. option:: --neutron-mechanism-drivers <drivers>

    An ordered list of extension driver entrypoints to be loaded from the
    neutron.ml2.extension_drivers namespace.

.. option:: --libvirt-type [kvm|lxc|qemu|uml|xen|parallels]

    Libvirt domain type. (default: qemu)

.. option:: --ntp-server <ip-address>

    The NTP for overcloud nodes.

.. option:: --cinder-lvm

    Enables the cinder lvm/iscsi backend.

.. option:: --tripleo-root <directory>

    The root directory for TripleO templates.

.. option:: --nodes-json <file>

    A file containing node definitions. (default: instackenv.json)

.. option:: --no-proxy <hosts>

    A comma separated list of hosts that should not be proxied.

.. option:: -O <directory>, --output-dir <directory>

    Directory to write Tuskar template files into. It will be created if it
    does not exist. If not provided a temporary directory will be used.

.. option:: -e <file>, --environment-file <file>

    Environment files to be passed to the heat stack-create or heat
    stack-update command. (Can be specified more than once.)

.. option:: --rhel-reg

    Register overcloud nodes to the customer portal or a satellite.

.. option:: --reg-method [sattelite|portal]

    RHEL registration method to use for the overcloud nodes.

.. option:: --reg-org <organization>

    Organization key to use for registration.

.. option:: --reg-force

    Register the system even if it is already registered.

.. option:: --reg-sat-url <url>

    Satellite server to register overcloud nodes.

.. option:: --reg-activation-key <key>

    Activation key to use for registration.
