from __future__ import annotations

import argparse
import logging
import signal
import sys
import uuid
from datetime import datetime, timezone

from pymongo.errors import ServerSelectionTimeoutError
from scapy.all import conf, get_if_list
from scapy.arch.common import compile_filter
from scapy.error import Scapy_Exception

from app.capture import PacketProcessor, run_capture
from app.config import load_settings
from app.stats import TrafficStats, format_summary
from app.storage import BatchWriter, PacketRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("challenge1Meli")


def build_parser(settings) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analisador de tráfego de rede")
    sub = parser.add_subparsers(dest="command")

    cap = sub.add_parser("capture", help="Captura pacotes, grava no MongoDB e exibe estatísticas")
    cap.add_argument("--interface", "-i", default=settings.interface, help="Interface de rede")
    cap.add_argument("--count", "-c", type=int, default=settings.packet_count, help="Nº de pacotes")
    cap.add_argument("--timeout", "-t", type=int, default=settings.timeout, help="Segundos de captura")
    cap.add_argument("--filter", "-f", default=settings.bpf_filter, help='Filtro BPF')
    cap.add_argument("--no-db", action="store_true", help="Não grava no banco")

    rep = sub.add_parser("report", help="Exibe estatísticas calculadas a partir do MongoDB")
    rep.add_argument("--session", "-s", default=None, help="ID da sessão")
    return parser


def _sigterm_to_keyboard_interrupt(signum, frame):
    raise KeyboardInterrupt


def validate_capture_args(args) -> str | None:
    available = get_if_list()
    if args.interface not in available:
        return f"Interface '{args.interface}' não encontrada. Disponíveis: {', '.join(available)}"

    if args.filter:
        try:
            compile_filter(args.filter, iface=args.interface)
        except ImportError:
            return "Filtro BPF exige a libpcap instalada. No Docker ela já vem instalada."
        except Scapy_Exception as exc:
            return f"Filtro BPF inválido '{args.filter}': {exc}"
    return None


def cmd_capture(args, settings) -> int:
    if not args.interface:
        args.interface = str(conf.iface)
    error = validate_capture_args(args)
    if error:
        logger.error(error)
        return 1

    session_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    stats = TrafficStats()
    repository = writer = None

    if not args.no_db:
        repository = PacketRepository.from_uri(settings.mongo_uri, settings.mongo_db)
        repository.ensure_indexes()
        repository.start_session(session_id, {
            "interface": args.interface, "filter": args.filter,
            "count": args.count, "timeout": args.timeout,
        })
        writer = BatchWriter(repository, settings.batch_size, settings.flush_interval)
        writer.start()

    processor = PacketProcessor(stats, writer, interface=args.interface, session_id=session_id)
    logger.info("Sessão de captura: %s", session_id)

    try:
        run_capture(processor, args.interface, args.filter, args.count, args.timeout)
    finally:
        summary = stats.summary()
        if writer is not None:
            writer.stop()
            repository.finish_session(session_id, summary, writer.stored, writer.failed)
            logger.info("Gravados no MongoDB: %d | falhas: %d", writer.stored, writer.failed)
        logger.info("Pacotes não-IP ignorados: %d", processor.ignored_non_ip)
        print(format_summary(summary, title=f"ESTATÍSTICAS - sessão {session_id}"))
    return 0


def cmd_report(args, settings) -> int:
    repository = PacketRepository.from_uri(settings.mongo_uri, settings.mongo_db)
    summary = repository.aggregate_stats(session_id=args.session)
    title = f"RELATÓRIO - sessão {args.session}" if args.session else "RELATÓRIO - todas as capturas"
    print(format_summary(summary, title=title))
    return 0


def main(argv: list[str] | None = None) -> int:
    settings = load_settings()
    parser = build_parser(settings)
    argv = sys.argv[1:] if argv is None else argv
    if not argv or (argv[0].startswith("-") and argv[0] not in ("-h", "--help")):
        argv = ["capture", *argv]
    args = parser.parse_args(argv)

    signal.signal(signal.SIGTERM, _sigterm_to_keyboard_interrupt)

    try:
        if args.command == "report":
            return cmd_report(args, settings)
        return cmd_capture(args, settings)
    except ServerSelectionTimeoutError:
        logger.error("Não foi possível conectar ao MongoDB em %s. O banco está rodando?", settings.mongo_uri)
        return 1
    except PermissionError:
        logger.error("Sem permissão para capturar pacotes. Rode como root/sudo ou no Docker.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
