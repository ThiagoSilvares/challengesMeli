from __future__ import annotations

import logging
import queue
import threading
import time
from datetime import datetime, timezone

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


class PacketRepository:
    def __init__(self, db) -> None:
        self.packets = db["packets"]
        self.sessions = db["capture_sessions"]

    @classmethod
    def from_uri(cls, uri: str, db_name: str) -> "PacketRepository":
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")  
        return cls(client[db_name])

    def ensure_indexes(self) -> None:
        self.packets.create_index([("session_id", ASCENDING), ("captured_at", DESCENDING)])
        self.packets.create_index([("src_ip", ASCENDING)])
        self.packets.create_index([("dst_ip", ASCENDING)])
        self.packets.create_index([("protocol", ASCENDING)])

    def save_packets(self, docs: list[dict]) -> int:
        if not docs:
            return 0
        result = self.packets.insert_many([dict(d) for d in docs], ordered=False)
        return len(result.inserted_ids)

    def start_session(self, session_id: str, params: dict) -> None:
        self.sessions.insert_one({
            "_id": session_id,
            "started_at": datetime.now(timezone.utc),
            "params": params,
            "status": "running",
        })

    def finish_session(self, session_id: str, summary: dict, stored: int, failed: int) -> None:
        self.sessions.update_one(
            {"_id": session_id},
            {"$set": {
                "finished_at": datetime.now(timezone.utc),
                "status": "finished",
                "summary": summary,
                "stored_packets": stored,
                "failed_packets": failed,
            }},
        )

    def aggregate_stats(self, session_id: str | None = None, top_n: int = 5) -> dict:
        match = {"$match": {"session_id": session_id} if session_id else {}}

        totals = next(self.packets.aggregate([
            match,
            {"$group": {"_id": None, "packets": {"$sum": 1}, "bytes": {"$sum": "$size_bytes"}}},
        ]), {})

        by_protocol = self.packets.aggregate([
            match,
            {"$group": {"_id": "$protocol", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ])

        def top_by(field: str) -> list[dict]:
            rows = self.packets.aggregate([
                match,
                {"$group": {"_id": f"${field}", "bytes": {"$sum": "$size_bytes"}, "packets": {"$sum": 1}}},
                {"$sort": {"bytes": -1}},
                {"$limit": top_n},
            ])
            return [{"ip": r["_id"], "bytes": r["bytes"], "packets": r["packets"]} for r in rows]

        return {
            "total_packets": totals.get("packets", 0),
            "total_bytes": totals.get("bytes", 0),
            "by_protocol": {row["_id"]: row["count"] for row in by_protocol},
            "top_src": top_by("src_ip"),
            "top_dst": top_by("dst_ip"),
        }


class BatchWriter:

    _STOP = object() 

    def __init__(self, repository: PacketRepository, batch_size: int = 200, flush_interval: float = 2.0) -> None:
        self.repository = repository
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._queue: queue.Queue = queue.Queue(maxsize=100_000)
        self._thread = threading.Thread(target=self._run, name="batch-writer", daemon=True)
        self.stored = 0        
        self.db_errors = 0    
        self.dropped = 0      

    def start(self) -> None:
        self._thread.start()

    def submit(self, doc: dict) -> None:
        try:
            self._queue.put_nowait(doc)
        except queue.Full:
            self.dropped += 1

    @property
    def failed(self) -> int:
        return self.db_errors + self.dropped

    def stop(self) -> None:
        self._queue.put(self._STOP)
        self._thread.join()

    def _flush(self, buffer: list[dict]) -> None:
        if not buffer:
            return
        try:
            self.stored += self.repository.save_packets(buffer)
        except PyMongoError as exc:
            self.db_errors += len(buffer)
            logger.error("Falha ao gravar lote de %d pacotes: %s", len(buffer), exc)
        buffer.clear()

    def _run(self) -> None:
        buffer: list[dict] = []
        last_flush = time.monotonic() 
        while True:
            try:
                item = self._queue.get(timeout=self.flush_interval)
            except queue.Empty:
                item = None  

            if item is self._STOP:
                self._flush(buffer) 
                return

            if item is not None:
                buffer.append(item)

            if len(buffer) >= self.batch_size or time.monotonic() - last_flush >= self.flush_interval:
                self._flush(buffer)
                last_flush = time.monotonic()
