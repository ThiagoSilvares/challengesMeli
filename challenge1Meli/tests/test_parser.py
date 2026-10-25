from scapy.layers.inet import ICMP, IP, TCP, UDP
from scapy.layers.inet6 import IPv6
from scapy.layers.l2 import ARP, Ether

from app.parser import parse_packet


def _eth():
    return Ether(src="00:11:22:33:44:55", dst="66:77:88:99:aa:bb")


def test_extrai_campos_de_pacote_tcp_ipv4():
    pkt = _eth() / IP(src="10.0.0.1", dst="8.8.8.8") / TCP(sport=51000, dport=443)
    doc = parse_packet(pkt, interface="eth0", session_id="s1")

    assert doc["src_ip"] == "10.0.0.1"
    assert doc["dst_ip"] == "8.8.8.8"
    assert doc["protocol"] == "TCP"
    assert doc["protocol_number"] == 6
    assert doc["size_bytes"] == len(pkt)
    assert (doc["src_port"], doc["dst_port"]) == (51000, 443)
    assert doc["ip_version"] == 4
    assert doc["session_id"] == "s1"


def test_extrai_campos_de_pacote_udp_ipv6():
    pkt = _eth() / IPv6(src="2001:db8::1", dst="2001:db8::2") / UDP(sport=5353, dport=53)
    doc = parse_packet(pkt)

    assert doc["protocol"] == "UDP"
    assert doc["ip_version"] == 6
    assert doc["dst_port"] == 53


def test_icmp_nao_tem_portas():
    doc = parse_packet(_eth() / IP(src="1.1.1.1", dst="2.2.2.2") / ICMP())

    assert doc["protocol"] == "ICMP"
    assert doc["src_port"] is None and doc["dst_port"] is None


def test_pacote_sem_ip_e_ignorado():
    assert parse_packet(_eth() / ARP()) is None