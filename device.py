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
