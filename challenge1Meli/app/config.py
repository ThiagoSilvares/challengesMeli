from __future__ import annotations

import os
from dataclasses import dataclass


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Variável de ambiente {name} deve ser inteira, recebido: {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    interface: str | None      
    bpf_filter: str | None     
    packet_count: int        
    timeout: int               
    mongo_uri: str
    mongo_db: str
    batch_size: int            
    flush_interval: float     


def load_settings() -> Settings:
    return Settings(
        interface=os.getenv("CAPTURE_INTERFACE") or None,
        bpf_filter=os.getenv("CAPTURE_FILTER") or None,
        packet_count=_get_int("CAPTURE_COUNT", 0),
        timeout=_get_int("CAPTURE_TIMEOUT", 30),
        mongo_uri=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        mongo_db=os.getenv("MONGO_DB", "traffic_analyzer"),
        batch_size=_get_int("BATCH_SIZE", 200),
        flush_interval=float(os.getenv("FLUSH_INTERVAL", "2")),
    )
