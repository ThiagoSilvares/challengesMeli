import mongomock

from app.storage import BatchWriter, PacketRepository


def _doc(src, dst, proto, size, session="s1"):
    return {"session_id": session, "src_ip": src, "dst_ip": dst, "protocol": proto, "size_bytes": size}


def test_batch_writer_grava_tudo_ao_parar():
    repo = PacketRepository(mongomock.MongoClient()["test"])
    writer = BatchWriter(repo, batch_size=2, flush_interval=10)
    writer.start()
    for i in range(5):
        writer.submit(_doc(f"10.0.0.{i}", "8.8.8.8", "TCP", 100))
    writer.stop()

    assert writer.stored == 5
    assert repo.packets.count_documents({}) == 5


def test_aggregate_stats_no_banco_bate_com_o_esperado():
    repo = PacketRepository(mongomock.MongoClient()["test"])
    repo.save_packets([
        _doc("10.0.0.1", "8.8.8.8", "TCP", 1000),
        _doc("10.0.0.1", "8.8.8.8", "TCP", 500),
        _doc("10.0.0.2", "1.1.1.1", "UDP", 100),
        _doc("9.9.9.9", "1.1.1.1", "UDP", 999, session="outra"),
    ])

    s = repo.aggregate_stats(session_id="s1")

    assert s["total_packets"] == 3
    assert s["total_bytes"] == 1600
    assert s["by_protocol"] == {"TCP": 2, "UDP": 1}
    assert s["top_src"][0] == {"ip": "10.0.0.1", "bytes": 1500, "packets": 2}
