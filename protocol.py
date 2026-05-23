"""Protocol header definitions for the mini network stack simulator.

This file contains the simple data containers used by Layer 2, Layer 3,
and Layer 4. Each class represents one layer wrapping the data from the
layer above it.
"""

from dataclasses import dataclass

ETHERNET_TYPE_IPV4 = 0x0800 # Ethernet-like type value for IPv4 payload.
IP_PROTOCOL_UDP = 17 # IP-like protocol value for UDP payload.

# Transport segment types.
SEGMENT_TYPE_DATA = 0
SEGMENT_TYPE_ACK = 1

# one transport segment can carry max 500 bytes of app data.
MAX_SEGMENT_DATA_SIZE = 500

def compute_checksum(data: bytes) -> int:
    """Compute a simple 16-bit checksum from bytes."""
    return sum(data) % 65536


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
        """Automatically compute checksum after the segment is created."""
        if self.checksum == 0:
            self.checksum = compute_checksum(self._checksum_bytes())

    def length(self) -> int:
        """Return total segment length: 10-byte header + data size."""
        return 10 + len(self.data)

    def _checksum_bytes(self) -> bytes:
        """Convert segment fields into bytes for checksum calculation."""
        text = (
            f"{self.source_port}|"
            f"{self.destination_port}|"
            f"{self.length()}|"
            f"{self.segment_type}|"
            f"{self.sequence_number}|"
        ).encode("utf-8")

        return text + self.data

    def verify_checksum(self) -> bool:
        """Return True if checksum still matches current segment contents."""
        return self.checksum == compute_checksum(self._checksum_bytes())

    def is_data(self) -> bool:
        """Return True if this segment carries application data."""
        return self.segment_type == SEGMENT_TYPE_DATA

    def is_ack(self) -> bool:
        """Return True if this segment is an ACK segment."""
        return self.segment_type == SEGMENT_TYPE_ACK


@dataclass
class Layer3Packet:
    """Network-layer IP-like packet."""
    source_ip: str
    destination_ip: str
    ttl: int
    protocol: int  # 17 = UDP-like payload
    payload: Layer4Segment

    def total_length(self) -> int:
        """Return total packet length: 12-byte IP-like header + Layer 4 segment size."""
        return 12 + self.payload.length()

    def decrement_ttl(self) -> None:
        """Decrease TTL by 1 when packet passes through a router."""
        self.ttl -= 1

    def is_expired(self) -> bool:
        """Return True if TTL has reached 0 or below."""
        return self.ttl <= 0

    def is_for_destination(self, ip_address: str) -> bool:
        """Return True if this packet is addressed to this host."""
        return self.destination_ip == ip_address
    

@dataclass
class Layer2Frame:
    """Data-link-layer Ethernet-like frame."""
    destination_mac: str
    source_mac: str
    frame_type: int  # 0x0800 = IPv4
    payload: Layer3Packet

    def is_ipv4(self) -> bool:
        """Return True if this frame carries an IPv4-like packet."""
        return self.frame_type == ETHERNET_TYPE_IPV4

    def is_for_mac(self, mac_address: str) -> bool:
        """Return True if this frame is addressed to this network interface."""
        return self.destination_mac == mac_address