from __future__ import annotations

from datetime import datetime, timezone

from scapy.layers.inet import ICMP, IP, TCP, UDP
from scapy.layers.inet6 import IPv6

PROTOCOL_NAMES = {
    1: "ICMP",
    2: "IGMP",
    6: "TCP",
    17: "UDP",
    47: "GRE",
    50: "ESP",
    58: "ICMPv6",
    132: "SCTP",
}


def parse_packet(pkt, interface: str | None = None, session_id: str | None = None) -> dict | None:
    if pkt.haslayer(IP):
        ip_layer = pkt[IP]
        ip_version = 4
        proto_number = int(ip_layer.proto)
    elif pkt.haslayer(IPv6):
        ip_layer = pkt[IPv6]
        ip_version = 6
        proto_number = int(ip_layer.nh)
    else:
        return None
    protocol = PROTOCOL_NAMES.get(proto_number, f"OTHER({proto_number})")
    src_port = dst_port = None
    if pkt.haslayer(TCP):
        src_port, dst_port = int(pkt[TCP].sport), int(pkt[TCP].dport)
    elif pkt.haslayer(UDP):
        src_port, dst_port = int(pkt[UDP].sport), int(pkt[UDP].dport)
    elif pkt.haslayer(ICMP):
        protocol = "ICMP" 
    captured_at = datetime.fromtimestamp(float(pkt.time), tz=timezone.utc)

    return {
        "session_id": session_id,
        "captured_at": captured_at,
        "interface": interface,
        "ip_version": ip_version,
        "src_ip": ip_layer.src,
        "dst_ip": ip_layer.dst,
        "protocol": protocol,
        "protocol_number": proto_number,
        "size_bytes": len(pkt),
        "src_port": src_port,
        "dst_port": dst_port,
    }
