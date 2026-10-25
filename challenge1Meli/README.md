# challenge1Meli - Analisador de Tráfego de Rede

Aplicação em Python que captura pacotes de uma interface de rede, grava cada pacote no MongoDB e exibe estatísticas do tráfego. Roda em Docker.

## Stack e justificativas

| Item | Escolha | Por quê |

| Linguagem | Python 3.12 | Sugerido no desafio |
| Captura | Scapy | Sugerido no desafio; acesso simples a cada camada do pacote |
| Banco | MongoDB 7 | Cada pacote é um documento independente, gravado uma vez e lido em agregações |
| Driver | PyMongo | Driver oficial; `insert_many` para gravação em lote |
| Execução | Docker Compose | Sobe banco e aplicação com um comando |
| Testes | pytest + mongomock | Testes rodam sem rede, sem root e sem Mongo real |

## Pré-requisitos

- Docker com Docker Compose

## Como executar

1. `cp .env.example .env`
2. `docker compose up --build --attach sniffer`

O Mongo sobe, a captura roda por 30 segundos, grava os pacotes no banco e exibe as estatísticas.

Para ver as estatísticas calculadas a partir do banco: `docker compose run --rm sniffer report`

Para desligar: `docker compose down`

## Comandos

| Comando | O que faz |

| `docker compose up --build --attach sniffer` | Sobe o Mongo e executa uma captura com os valores do `.env` |
| `docker compose run --rm sniffer capture --interface eth0 --count 500` | Captura 500 pacotes da interface `eth0` |
| `docker compose run --rm sniffer report` | Estatísticas calculadas a partir dos pacotes gravados no banco |

## Testes

`python3 -m venv .venv`
`source .venv/bin/activate`
`pip install -r requirements-dev.txt`
`pytest -q`

## Configuração (`.env`)

| Variável | Padrão | Descrição |
|---|---|---|
| `CAPTURE_INTERFACE` | interface padrão | Interface de rede a capturar |
| `CAPTURE_TIMEOUT` | `30` | Segundos de captura |
| `CAPTURE_COUNT` | `0` | Nº de pacotes |
| `CAPTURE_FILTER` | vazio | Filtro BPF opcional |
| `MONGO_PORT` | `27017` | Porta do Mongo no host |
| `BATCH_SIZE` / `FLUSH_INTERVAL` | `200` / `2` | Grava no banco a cada 200 pacotes ou a cada 2 segundos |

## Schema do banco

Coleção `packets`, um documento por pacote:

| Campo | Tipo | Descrição |
|---|---|---|
| `src_ip` | string | IP de origem |
| `dst_ip` | string | IP de destino |
| `protocol` | string | `TCP`, `UDP`, `ICMP` ou `OTHER(n)` |
| `size_bytes` | int | Tamanho do pacote |
| `protocol_number` | int | Número IANA do protocolo |
| `src_port` / `dst_port` | int \| null | Portas |
| `ip_version` | int | 4 ou 6 |
| `captured_at` | Date | Momento da captura |
| `interface` | string | Interface capturada |
| `session_id` | string | Identifica a execução |

Índices: `{session_id, captured_at}`, `{src_ip}`, `{dst_ip}` e `{protocol}`.

Coleção `capture_sessions`, um documento por execução: parâmetros, início/fim, resumo das estatísticas, pacotes gravados e perdidos.

## Decisões

| Decisão | Por quê |

| Fila + thread separada para gravar no banco | A captura não espera o banco |
| Gravação em lote (`insert_many`) | Menos idas ao banco; o limite de tempo evita dados parados com tráfego baixo |
| `store=False` no Scapy | Não acumula pacotes em memória durante capturas longas |
| Top 5 ordenado por bytes | Bytes mede o volume real. A contagem de pacotes também é exibida |
| Pacotes sem IP ignorados | Não têm IP de origem/destino |
| `network_mode: host` + `NET_RAW`/`NET_ADMIN` | O container precisa ver as interfaces reais |
| Encerramento | `Ctrl+C` e `docker stop` gravam o que está no buffer e exibem as estatísticas |

## Dados reais do Mac

`docker compose up -d mongo`
`python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
`sudo .venv/bin/python challenge1Meli.py capture --interface en0`
