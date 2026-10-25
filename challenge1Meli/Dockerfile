# ---------------------------------------------------------------
# Imagem da aplicação de captura.
# python:3.12-slim = imagem pequena (menos tamanho e menos superfície de ataque).
# ---------------------------------------------------------------
FROM python:3.12-slim

# libpcap: biblioteca de captura usada pelo Scapy para compilar filtros BPF (--filter).
# --no-install-recommends + limpar cache do apt = imagem menor.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpcap0.8 \
    && rm -rf /var/lib/apt/lists/*

# PYTHONUNBUFFERED=1: logs aparecem na hora no "docker logs" (sem buffer).
# PYTHONDONTWRITEBYTECODE=1: não gera arquivos .pyc dentro do container.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copiamos o requirements ANTES do código: o Docker faz cache por camada.
# Se só o código mudar, ele reaproveita a camada do pip install (build bem mais rápido).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY challenge1Meli.py .

# Roda como root DE PROPÓSITO: captura em raw socket exige privilégio.
# Em vez de "privileged: true" (acesso total ao host), o compose concede só
# as capabilities necessárias: NET_RAW e NET_ADMIN (princípio do menor privilégio).
ENTRYPOINT ["python", "challenge1Meli.py"]
CMD ["capture"]
