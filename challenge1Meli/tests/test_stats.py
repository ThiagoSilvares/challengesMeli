from app.stats import TrafficStats

def _pkt(src, dst, proto="TCP", size=100):
    return {"src_ip": src, "dst_ip": dst, "protocol": proto, "size_bytes": size}


def test_conta_total_e_por_protocolo():
    stats = TrafficStats()
    for p in [_pkt("a", "b", "TCP"), _pkt("a", "b", "TCP"), _pkt("c", "d", "UDP")]:
        stats.add(p)

    s = stats.summary()

    assert s["total_packets"] == 3
    assert s["total_bytes"] == 300
    assert s["by_protocol"] == {"TCP": 2, "UDP": 1}


def test_top_ips_ordenado_por_bytes_e_limitado_a_5():
    stats = TrafficStats()
    for _ in range(10):
        stats.add(_pkt("pequeno", "x", size=40))
    stats.add(_pkt("grande", "x", size=1500))
    for i in range(6):
        stats.add(_pkt(f"ip{i}", "x", size=10))
    top = stats.summary()["top_src"]

    assert len(top) == 5
    assert top[0] == {"ip": "grande", "bytes": 1500, "packets": 1}
    assert top[1] == {"ip": "pequeno", "bytes": 400, "packets": 10}
