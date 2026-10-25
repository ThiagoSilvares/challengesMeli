from __future__ import annotations
from collections import Counter

TOP_N = 5

class TrafficStats:
    def __init__(self) -> None:
        self.total_packets = 0
        self.total_bytes = 0
        self.by_protocol: Counter[str] = Counter()
        self.src_bytes: Counter[str] = Counter()
        self.src_packets: Counter[str] = Counter()
        self.dst_bytes: Counter[str] = Counter()
        self.dst_packets: Counter[str] = Counter()

    def add(self, packet: dict) -> None:
        size = packet["size_bytes"]
        self.total_packets += 1
        self.total_bytes += size
        self.by_protocol[packet["protocol"]] += 1
        self.src_bytes[packet["src_ip"]] += size
        self.src_packets[packet["src_ip"]] += 1
        self.dst_bytes[packet["dst_ip"]] += size
        self.dst_packets[packet["dst_ip"]] += 1

    @staticmethod
    def _top(bytes_counter: Counter, packets_counter: Counter, n: int = TOP_N) -> list[dict]:
        return [
            {"ip": ip, "bytes": total_bytes, "packets": packets_counter[ip]}
            for ip, total_bytes in bytes_counter.most_common(n)
        ]

    def summary(self) -> dict:
        return {
            "total_packets": self.total_packets,
            "total_bytes": self.total_bytes,
            "by_protocol": dict(self.by_protocol.most_common()),
            "top_src": self._top(self.src_bytes, self.src_packets),
            "top_dst": self._top(self.dst_bytes, self.dst_packets),
        }


def format_summary(summary: dict, title: str = "ESTATÍSTICAS DE TRÁFEGO") -> str:
    lines = ["", "=" * 60, f" {title}", "=" * 60]
    lines.append(f"Total de pacotes capturados : {summary['total_packets']}")
    lines.append(f"Total de bytes              : {summary['total_bytes']}")

    lines.append("\nPacotes por protocolo:")
    if not summary["by_protocol"]:
        lines.append("  (nenhum)")
    for proto, count in summary["by_protocol"].items():
        lines.append(f"  {proto:<12} {count:>8}")

    for key, label in (("top_src", "ORIGEM"), ("top_dst", "DESTINO")):
        lines.append(f"\nTop {TOP_N} IPs de {label} (ordenado por bytes):")
        if not summary[key]:
            lines.append("  (nenhum)")
        for pos, row in enumerate(summary[key], start=1):
            lines.append(f"  {pos}. {row['ip']:<40} {row['bytes']:>10} bytes  {row['packets']:>6} pacotes")

    lines.append("=" * 60)
    return "\n".join(lines)
