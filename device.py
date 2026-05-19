# Should contain:
# Host class
# Router class

# Host should:
# send data
# receive data
# send ACK

# Output example:
# [HOST A] Sending message
# [HOST B] Received message: Hello

# Router should:
# receive frame
# remove MAC
# forward based on IP

# Output example:
# [ROUTER] Received frame
# [ROUTER] Forwarding packet to Host B

from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from typing import Dict, List, Optional

@dataclass
class Interface:
#Network interface with an IP address, MAC address, and link peer.

    name: str
    ip_address: str
    mac_address: str
    owner: "Device"
    connected_to: Optional["Interface"] = None


class NetworkSimulator:
    class Device:
        """Base class shared by hosts and routers."""

        def __init__(
                self,
                name,
                routing_table,
                mac_resolution_table,
                is_router,
        ):
            self.name = name
            self.routing_table = routing_table
            self.mac_resolution_table = mac_resolution_table
            self.is_router = is_router
            self.interfaces = {}
            self.simulator = None
            self.data_link_layer = DataLinkLayer(self)
            self.network_layer = NetworkLayer(self)
            self.transport_layer = None
            self.application_data = b""

        def add_interface(self, name, ip, mac):
            """Create and attach an interface to this device."""

            interface = Interface(name, ip, mac, self)
            self.interfaces[name] = interface
            return interface

        def has_ip(self, address):
            """Return True if the IP address belongs to this device."""

            return any(interface.ip_address == address for interface in self.interfaces.values())

        def log(self, layer, message):
            """Print a structured layer log message."""

            print(f"{self.name}: Layer {layer}: {message}")

class DataLinkLayer:


class NetworkLayer: