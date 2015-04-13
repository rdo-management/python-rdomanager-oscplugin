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

import hashlib
import six
import time
import uuid


def _generate_password():
    """Create a random password

    The password is made by taking a uuid and passing it though sha1sum.
    echo "We may change this in future to gain more entropy.

    This is based on the tripleo command os-make-password
    """
    uuid_str = six.text_type(uuid.uuid1()).encode("UTF-8")
    return hashlib.sha1(uuid_str).hexdigest()


def generate_overcloud_passwords():

    passwords = (
        "OVERCLOUD_ADMIN_PASSWORD",
        "OVERCLOUD_ADMIN_TOKEN",
        "OVERCLOUD_CEILOMETER_PASSWORD",
        "OVERCLOUD_CEILOMETER_SECRET",
        "OVERCLOUD_CINDER_PASSWORD",
        "OVERCLOUD_DEMO_PASSWORD",
        "OVERCLOUD_GLANCE_PASSWORD",
        "OVERCLOUD_HEAT_PASSWORD",
        "OVERCLOUD_HEAT_STACK_DOMAIN_PASSWORD",
        "OVERCLOUD_NEUTRON_PASSWORD",
        "OVERCLOUD_NOVA_PASSWORD",
        "OVERCLOUD_SWIFT_HASH",
        "OVERCLOUD_SWIFT_PASSWORD",
    )

    return dict((password, _generate_password()) for password in passwords)


def wait_for_hypervisor_stats(compute_client, nodes=1, memory=None, vcpu=None,
                              sleep=10):
    """Wait for the Hypervisor stats to meet a minimum value

    Wait for the hypervisor stats to match the required counts. This is an
    implementation of a command in TripleO with the same name.

    :param compute_client: Instance of Nova client
    :type  compute_client: novaclient.client.v2.Client

    :param nodes: The number of nodes to wait for, defaults to 1.
    :type  nodes: int

    :param memory: The amount of memory to wait for in MB, defaults to the
                   amount of memory for the baremetal flavor times the number
                   of nodes.
    :type  memory: int

    :param vcpu: The number of vcpus to wait for, defaults to the number of
                 vcpus for the baremtal flavor times the number of nodes.
    :type  vcpu: int
    """

    # TODO(dmatthews): These shouldn't default to 0 and should do what the
    # comment above says.
    if memory is None:
        memory = 0

    if vcpu is None:
        vcpu = 0

    while True:

        statistics = compute_client.hypervisors.statistics().to_dict()

        if all([statistics['count'] >= nodes,
                statistics['memory_mb'] >= memory,
                statistics['vcpus'] >= vcpu]):
            return statistics

        time.sleep(sleep)
