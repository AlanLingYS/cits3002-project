from dataclasses import dataclass
from typing import Optional

import config
from protocol import (
    ETHERNET_TYPE_IPV4,
    IP_PROTOCOL_UDP,
    MAX_SEGMENT_DATA_SIZE,
    SEGMENT_TYPE_ACK,
    SEGMENT_TYPE_DATA,
    Layer2Frame,
    Layer3Packet,
    Layer4Segment,
)


# one network card / interface
@dataclass
class Interface:
    name: str
    ip_address: str
    mac_address: str
    owner: "Device"
    connected_to: Optional["Interface"] = None


class DataLinkLayer:
    # layer 2 handles frames and mac addresses
    def __init__(self, device):
        self.device = device
        self.learned_mac_table = {}

    def send_packet(self, packet, next_hop_ip, interface_name):
        self.device.log(2, "Packet received from Network Layer")

        interface = self.device.interfaces[interface_name]
        dst_mac = self.device.mac_resolution_table.get(next_hop_ip)

        if dst_mac is None:
            self.device.log(2, f"Frame dropped: no MAC address for next-hop IP ({next_hop_ip})")
            return None

        self.device.log(
            2,
            f"Destination MAC lookup for next-hop IP ({next_hop_ip}) -> {dst_mac}",
        )

        frame = Layer2Frame(
            destination_mac=dst_mac,
            source_mac=interface.mac_address,
            frame_type=ETHERNET_TYPE_IPV4,
            payload=packet,
        )

        self.device.log(
            2,
            f"Frame created: SRC_MAC={frame.source_mac}, DST_MAC={frame.destination_mac}",
        )

        if self.device.is_router:
            self.device.log(2, f"Frame forwarded on {interface_name}")
        else:
            self.device.log(2, "Frame sent")

        return self.device.simulator.transmit(interface, frame)

    def receive_frame(self, frame, interface_name):
        interface = self.device.interfaces[interface_name]

        # learn where the sender is from the incoming frame
        self.learned_mac_table[frame.source_mac] = interface_name

        if self.device.is_router:
            self.device.log(2, f"Frame received on {interface_name}")
            self.device.log(2, f"Source MAC learned: {frame.source_mac} on {interface_name}")
        else:
            self.device.log(2, "Frame received")
            self.device.log(2, f"Source MAC learned: {frame.source_mac}")

        if not frame.is_for_mac(interface.mac_address):
            return self.forward_or_drop(frame, interface_name)

        if not frame.is_ipv4():
            self.device.log(2, "Frame dropped: not IPv4")
            return None

        self.device.log(2, "Packet delivered to Network Layer")
        return self.device.network_layer.receive_packet(frame.payload)

    def forward_or_drop(self, frame, incoming_interface):
        outgoing_interface = self.learned_mac_table.get(frame.destination_mac)

        if outgoing_interface and outgoing_interface != incoming_interface:
            self.device.log(2, f"Frame forwarded on {outgoing_interface}")
            return self.device.simulator.transmit(
                self.device.interfaces[outgoing_interface],
                frame,
            )

        self.device.log(2, "Frame dropped: destination MAC is not local")
        return None


class NetworkLayer:
    # layer 3 handles IP packets, routing and TTL
    def __init__(self, device):
        self.device = device

    def send_segment(self, segment, dst_ip):
        route = self.device.routing_table.get(dst_ip)

        if route is None:
            self.device.log(3, f"No route to destination IP {dst_ip}")
            return None

        next_hop_ip, interface_name = route
        interface = self.device.interfaces[interface_name]

        packet = Layer3Packet(
            source_ip=interface.ip_address,
            destination_ip=dst_ip,
            ttl=config.TTL,
            protocol=IP_PROTOCOL_UDP,
            payload=segment,
        )

        self.device.log(
            3,
            f"Segment received from Transport Layer: SRC_IP={packet.source_ip}, "
            f"DST_IP={packet.destination_ip}, TTL={packet.ttl}",
        )
        self.device.log(3, f"Destination IP read: {packet.destination_ip}")
        self.device.log(3, "Routing table lookup performed")
        self.device.log(3, f"Next-hop IP determined: {next_hop_ip}")

        if self.device.is_router:
            self.device.log(3, f"Outgoing interface selected ({interface_name})")
        else:
            self.device.log(3, "Outgoing interface selected")

        self.device.log(3, "Packet forwarded to Data Link Layer")
        return self.device.data_link_layer.send_packet(packet, next_hop_ip, interface_name)

    def receive_packet(self, packet):
        self.device.log(
            3,
            f"Packet received from Data Link Layer: SRC_IP={packet.source_ip}, "
            f"DST_IP={packet.destination_ip}, TTL={packet.ttl}",
        )
        self.device.log(3, f"Destination IP read: {packet.destination_ip}")

        # if the packet is for this host, send it up to layer 4
        if self.device.has_ip(packet.destination_ip):
            self.device.log(3, "Packet identified as local delivery")
            self.device.log(3, "Segment delivered to Transport Layer")

            if self.device.transport_layer is None:
                self.device.log(3, "Packet dropped: no local transport layer")
                return None

            return self.device.transport_layer.receive_segment(
                packet.payload,
                packet.source_ip,
            )

        # hosts should not forward packets
        if not self.device.is_router:
            self.device.log(3, "Packet dropped: host is not a router")
            return None

        old_ttl = packet.ttl
        packet.decrement_ttl()
        self.device.log(3, f"TTL decremented: {old_ttl} -> {packet.ttl}")

        if packet.is_expired():
            self.device.log(3, "Packet dropped due to TTL expiry")
            return None

        route = self.device.routing_table.get(packet.destination_ip)

        if route is None:
            self.device.log(3, f"Packet dropped: no route to {packet.destination_ip}")
            return None

        next_hop_ip, interface_name = route

        self.device.log(3, "Routing table lookup performed")
        self.device.log(3, f"Next-hop IP determined: {next_hop_ip}")
        self.device.log(3, f"Outgoing interface selected ({interface_name})")
        self.device.log(3, "Packet forwarded to Data Link Layer")

        return self.device.data_link_layer.send_packet(packet, next_hop_ip, interface_name)


class TransportLayer:
    # layer 4 handles the message, checksum and ack
    def __init__(self, device):
        self.device = device
        self.send_sequence_number = 0
        self.expected_sequence_number = 0
        self.last_ack_segment = None

    def send_application_data(self, dst_ip, data):
        data = bytes(data)

        self.device.log(4, f"Data received from Application Layer. Data size={len(data)}")

        parts = self.split_data(data)

        if len(parts) > 1:
            self.device.log(4, f"Application data segmented into {len(parts)} segment(s)")

        for part in parts:
            got_ack = False

            # stop and wait: keep sending this segment until the right ack returns
            while not got_ack:
                seq = self.send_sequence_number

                segment = Layer4Segment(
                    source_port=config.DEFAULT_SOURCE_PORT,
                    destination_port=config.DEFAULT_DESTINATION_PORT,
                    segment_type=SEGMENT_TYPE_DATA,
                    sequence_number=seq,
                    data=part,
                )

                self.device.log(4, "Checksum computed")
                self.device.log(
                    4,
                    f"Segment created by adding transport layer header "
                    f"(DATA, seq={seq}) (encapsulation)",
                )
                self.device.log(4, "Segment sent to Network Layer")

                ack = self.device.network_layer.send_segment(segment, dst_ip)

                if self.correct_ack(ack, seq):
                    self.send_sequence_number = 1 - self.send_sequence_number
                    got_ack = True
                else:
                    self.device.log(4, f"Segment retransmitted due to incorrect ACK (seq={seq})")

    def receive_segment(self, segment, source_ip):
        self.device.log(4, "Segment received from Network Layer")

        if not segment.verify_checksum():
            self.device.log(4, "Checksum verification failed")
            self.device.log(4, "Segment discarded due to checksum error")
            return self.resend_last_ack(source_ip)

        self.device.log(4, "Checksum verified")

        if segment.is_ack():
            self.device.log(4, f"ACK received: seq={segment.sequence_number}")
            return segment

        return self.receive_data_segment(segment, source_ip)

    def receive_data_segment(self, segment, source_ip):
        # duplicate segment, so do not deliver it again
        if segment.sequence_number != self.expected_sequence_number:
            self.device.log(4, f"Duplicate DATA segment discarded: seq={segment.sequence_number}")
            return self.resend_last_ack(source_ip)

        self.device.application_data += segment.data
        self.device.log(
            4,
            f"DATA segment delivered to Application Layer. Data size={len(segment.data)}",
        )

        ack = Layer4Segment(
            source_port=segment.destination_port,
            destination_port=segment.source_port,
            segment_type=SEGMENT_TYPE_ACK,
            sequence_number=segment.sequence_number,
        )

        self.last_ack_segment = ack
        self.expected_sequence_number = 1 - self.expected_sequence_number

        self.device.log(4, "Checksum computed")
        self.device.log(
            4,
            f"Segment created by adding transport layer header (ACK, seq={ack.sequence_number})",
        )
        self.device.log(4, f"ACK sent: seq={ack.sequence_number}")
        self.device.log(4, "Segment sent to Network Layer")

        return self.device.network_layer.send_segment(ack, source_ip)

    def split_data(self, data):
        if not data:
            return [b""]

        chunks = []
        for i in range(0, len(data), MAX_SEGMENT_DATA_SIZE):
            chunks.append(data[i:i + MAX_SEGMENT_DATA_SIZE])
        return chunks

    def resend_last_ack(self, dst_ip):
        if self.last_ack_segment is None:
            self.device.log(4, "No previous ACK available to resend")
            return None

        self.device.log(4, f"ACK sent: seq={self.last_ack_segment.sequence_number}")
        self.device.log(4, "Segment sent to Network Layer")
        return self.device.network_layer.send_segment(self.last_ack_segment, dst_ip)

    def correct_ack(self, ack, seq):
        return (
            ack is not None
            and ack.is_ack()
            and ack.sequence_number == seq
            and ack.verify_checksum()
        )


class Device:
    # common stuff for Host and Router
    def __init__(self, name, routing_table, mac_table, is_router):
        self.name = name
        self.routing_table = routing_table
        self.mac_resolution_table = mac_table
        self.is_router = is_router
        self.interfaces = {}
        self.simulator = None
        self.data_link_layer = DataLinkLayer(self)
        self.network_layer = NetworkLayer(self)
        self.transport_layer = None
        self.application_data = b""

    def add_interface(self, name, ip, mac):
        interface = Interface(name, ip, mac, self)
        self.interfaces[name] = interface
        return interface

    def has_ip(self, ip):
        for interface in self.interfaces.values():
            if interface.ip_address == ip:
                return True
        return False

    def log(self, layer, message):
        print(f"{self.name}: Layer {layer}: {message}")


class Host(Device):
    def __init__(self, name, ip, mac, routing_table, mac_table):
        super().__init__(name, routing_table, mac_table, is_router=False)
        self.add_interface(config.HOST_INTERFACE, ip, mac)
        self.transport_layer = TransportLayer(self)

    def send_application_data(self, dst_ip, data):
        return self.transport_layer.send_application_data(dst_ip, data)


class Router(Device):
    def __init__(self):
        super().__init__(
            config.ROUTER_NAME,
            config.ROUTER_ROUTING_TABLE,
            config.ROUTER_MAC_TABLE,
            is_router=True,
        )

        self.add_interface(
            config.ROUTER_INTERFACE_1,
            config.ROUTER_IF1_IP,
            config.ROUTER_IF1_MAC,
        )
        self.add_interface(
            config.ROUTER_INTERFACE_2,
            config.ROUTER_IF2_IP,
            config.ROUTER_IF2_MAC,
        )


class NetworkSimulator:
    # fixed topology: Host A -- Router R1 -- Host B
    def __init__(self):
        self.host_a = Host(
            config.HOST_A_NAME,
            config.HOST_A_IP,
            config.HOST_A_MAC,
            config.HOST_A_ROUTING_TABLE,
            config.HOST_A_MAC_TABLE,
        )

        self.router = Router()

        self.host_b = Host(
            config.HOST_B_NAME,
            config.HOST_B_IP,
            config.HOST_B_MAC,
            config.HOST_B_ROUTING_TABLE,
            config.HOST_B_MAC_TABLE,
        )

        self.devices = [self.host_a, self.router, self.host_b]

        for device in self.devices:
            device.simulator = self

        self.connect_topology()

    def connect_topology(self):
        self.connect(
            self.host_a.interfaces[config.HOST_INTERFACE],
            self.router.interfaces[config.ROUTER_INTERFACE_1],
        )
        self.connect(
            self.router.interfaces[config.ROUTER_INTERFACE_2],
            self.host_b.interfaces[config.HOST_INTERFACE],
        )

    def connect(self, left, right):
        left.connected_to = right
        right.connected_to = left

    def transmit(self, outgoing_interface, frame):
        peer = outgoing_interface.connected_to

        if peer is None:
            outgoing_interface.owner.log(2, "Frame dropped: interface is not connected")
            return None

        return peer.owner.data_link_layer.receive_frame(frame, peer.name)

    def send_from_a_to_b(self, message_size):
        message = b"x" * message_size
        return self.host_a.send_application_data(config.HOST_B_IP, message)
