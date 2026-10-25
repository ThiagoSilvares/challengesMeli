from __future__ import annotations

import logging

from scapy.all import sniff

from app.parser import parse_packet
from app.stats import TrafficStats

logger = logging.getLogger(__name__)


class PacketProcessor:
    def __init__(self, stats: TrafficStats, writer=None, interface: str | None = None, session_id: str | None = None):
        self.stats = stats
        self.writer = writer          
        self.interface = interface
        self.session_id = session_id
        self.ignored_non_ip = 0     

    def __call__(self, pkt) -> None:
        try:
            doc = parse_packet(pkt, interface=self.interface, session_id=self.session_id)
        except Exception:  
            logger.exception("Erro ao processar pacote; ignorando")
            return

        if doc is None:
            self.ignored_non_ip += 1
            return

        self.stats.add(doc)
        if self.writer is not None:
            self.writer.submit(doc)  


def run_capture(processor: PacketProcessor, interface: str | None, bpf_filter: str | None,
                count: int, timeout: int) -> None:
    logger.info(
        "Iniciando captura | interface=%s | filtro=%s | count=%s | timeout=%ss",
        interface or "(padrão)", bpf_filter or "(nenhum)", count or "∞", timeout or "∞",
    )
    try:
        sniff(
            iface=interface,
            filter=bpf_filter,
            prn=processor,
            store=False,
            count=count,
            timeout=timeout or None,
        )
    except KeyboardInterrupt:
        logger.info("Captura interrompida pelo usuário")
