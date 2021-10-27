# Copyright 2018 Microsoft Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requires Python 2.6+ and Openssl 1.0+
#
import subprocess

from mock.mock import patch

import azurelinuxagent.common.utils.networkutil as networkutil
from tests.tools import AgentTestCase


class TestNetworkOperations(AgentTestCase):
    def test_route_entry(self):
        interface = "eth0"
        mask = "C0FFFFFF"    # 255.255.255.192
        destination = "C0BB910A"    #
        gateway = "C1BB910A"
        flags = "1"
        metric = "0"

        expected = 'Iface: eth0\tDestination: 10.145.187.192\tGateway: 10.145.187.193\tMask: 255.255.255.192\tFlags: 0x0001\tMetric: 0'
        expected_json = '{"Iface": "eth0", "Destination": "10.145.187.192", "Gateway": "10.145.187.193", "Mask": "255.255.255.192", "Flags": "0x0001", "Metric": "0"}'

        entry = networkutil.RouteEntry(interface, destination, gateway, mask, flags, metric)

        self.assertEqual(str(entry), expected)
        self.assertEqual(entry.to_json(), expected_json)

    def test_nic_link_only(self):
        nic = networkutil.NetworkInterfaceCard("test0", "link info")
        self.assertEqual(str(nic), '{ "name": "test0", "link": "link info" }')

    def test_nic_ipv4(self):
        nic = networkutil.NetworkInterfaceCard("test0", "link info")
        nic.add_ipv4("ipv4-1")
        self.assertEqual(str(nic), '{ "name": "test0", "link": "link info", "ipv4": ["ipv4-1"] }')
        nic.add_ipv4("ipv4-2")
        self.assertEqual(str(nic), '{ "name": "test0", "link": "link info", "ipv4": ["ipv4-1","ipv4-2"] }')

    def test_nic_ipv6(self):
        nic = networkutil.NetworkInterfaceCard("test0", "link info")
        nic.add_ipv6("ipv6-1")
        self.assertEqual(str(nic), '{ "name": "test0", "link": "link info", "ipv6": ["ipv6-1"] }')
        nic.add_ipv6("ipv6-2")
        self.assertEqual(str(nic), '{ "name": "test0", "link": "link info", "ipv6": ["ipv6-1","ipv6-2"] }')

    def test_nic_ordinary(self):
        nic = networkutil.NetworkInterfaceCard("test0", "link INFO")
        nic.add_ipv6("ipv6-1")
        nic.add_ipv4("ipv4-1")
        self.assertEqual(str(nic), '{ "name": "test0", "link": "link INFO", "ipv4": ["ipv4-1"], "ipv6": ["ipv6-1"] }')


class TestAddFirewallRules(AgentTestCase):

    def test_it_should_add_firewall_rules(self):
        test_dst_ip = "1.2.3.4"
        test_uid = 9999
        test_wait = "-w"
        original_popen = subprocess.Popen
        commands_called = []

        def mock_popen(command, *args, **kwargs):
            if "iptables" in command:
                commands_called.append(command)
                command = ["echo", "iptables"]
            return original_popen(command, *args, **kwargs)

        with patch("azurelinuxagent.common.utils.shellutil.subprocess.Popen", side_effect=mock_popen):
            networkutil.AddFirewallRules.add_iptables_rules(test_wait, test_dst_ip, test_uid)

        self.assertTrue(all(test_dst_ip in cmd for cmd in commands_called), "Dest IP was not set correctly in iptables")
        self.assertTrue(all(test_wait in cmd for cmd in commands_called), "The wait was not set properly")
        self.assertTrue(all(str(test_uid) in cmd for cmd in commands_called if "ACCEPT" in cmd and "-A" in cmd),
                        "The UID is not set for the accept command")

    def test_it_should_raise_if_invalid_data(self):
        with self.assertRaises(Exception) as context_manager:
            networkutil.AddFirewallRules.add_iptables_rules(wait="", dst_ip="", uid=9999)
        self.assertIn("Destination IP should not be empty", str(context_manager.exception))

        with self.assertRaises(Exception) as context_manager:
            networkutil.AddFirewallRules.add_iptables_rules(wait="", dst_ip="1.2.3.4", uid="")
        self.assertIn("User ID should not be empty", str(context_manager.exception))
