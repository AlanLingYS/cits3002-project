# It simulates the network layers (L2, L3, L4)



# “take data → wrap it → send → unwrap it”

# where data gets wrapped into layers and unwrapped

"""Protocol header definitions for the mini network stack simulator.

This file contains the simple data containers used by Layer 2, Layer 3,
and Layer 4. Each class represents one layer wrapping the data from the
layer above it.
"""

from dataclasses import dataclass

# Ethernet-like type value for IPv4 payload.
ETHERNET_TYPE_IPV4 = 0x0800

# IP-like protocol value for UDP payload.
IP_PROTOCOL_UDP = 17

# Transport segment types.
SEGMENT_TYPE_DATA = 0
SEGMENT_TYPE_ACK = 1

# Project limit: one transport segment can carry max 500 bytes of app data.
MAX_SEGMENT_DATA_SIZE = 500


@dataclass
class Layer4Segment:
    """Transport-layer UDP-like segment with ACK support."""

    source_port: int
    destination_port: int
    segment_type: int  # 0 = DATA, 1 = ACK
    sequence_number: int  # alternating bit: 0 or 1
    data: bytes = b""
    checksum: int = 0

    def __post_init__(self):
        """Compute length and checksum after the object is created."""
        self.length = 9 + len(self.data)  # 2+2+2+2+1+1 simplified header/data idea
        if self.checksum == 0:
            self.checksum = compute_checksum(self._checksum_bytes())

    def _checksum_bytes(self):
        """Return bytes used to compute the checksum."""
        text = (
            f"{self.source_port}|{self.destination_port}|{self.length}|"
            f"{self.segment_type}|{self.sequence_number}|"
        ).encode("utf-8")
        return text + self.data

    def verify_checksum(self):
        """Return True if the current checksum matches the segment contents."""
        return self.checksum == compute_checksum(self._checksum_bytes())

    def is_ack(self):
        """Return True when this segment is an ACK segment."""
        return self.segment_type == SEGMENT_TYPE_ACK

    def is_data(self):
        """Return True when this segment is a DATA segment."""
        return self.segment_type == SEGMENT_TYPE_DATA


@dataclass
class Layer3Packet:
    """Network-layer IP-like packet."""

    source_ip: str
    destination_ip: str
    payload: Layer4Segment
    ttl: int = 100
    protocol: int = IP_PROTOCOL_UDP

    def __post_init__(self):
        """Compute total length after the packet is created."""
        self.total_length = 12 + self.payload.length  # simplified IP header + payload


@dataclass
class Layer2Frame:
    """Data-link-layer Ethernet-like frame."""

    source_mac: str
    destination_mac: str
    payload: Layer3Packet
    frame_type: int = ETHERNET_TYPE_IPV4


def compute_checksum(data):
    """Compute a small deterministic checksum for error detection.

    This is a simple 16-bit one's-complement-style checksum suitable for
    the logical simulation. It does not use external libraries.
    """
    total = 0
    for byte in data:
        total += byte
        total = (total & 0xFFFF) + (total >> 16)  # wrap carry around
    return (~total) & 0xFFFF

