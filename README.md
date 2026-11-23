<div align="center">

# Data Courier

Reliable one-way file transfer through a data diode.

![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![UDP](https://img.shields.io/badge/transport-UDP-0EA5E9)
![Reed-Solomon](https://img.shields.io/badge/FEC-Reed--Solomon-8B5CF6)
![Docker](https://img.shields.io/badge/Docker-amd64%20%7C%20arm64-2496ED?logo=docker&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-optional-FF6600?logo=rabbitmq&logoColor=white)

</div>

Data Courier moves files across a one-way link reliably. Drop a file into a folder on the
sending side and it appears, whole, in the matching folder on the receiving side: as fast as the
link allows, recovering lost packets on its own, with every part of the transfer configurable.

## Why use it

- **Reliable**: error correction rebuilds lost packets on arrival, so nothing ever needs a resend.
- **Fast and steady**: sends at the speed you set, evenly, and delivers a first full copy as early as possible.
- **Configurable**: redundancy, speed, packet size and timings are all settings.
- **Many channels**: every folder is its own channel, sending in parallel and sharing the bandwidth fairly.
- **Handles the edge cases**: half-written files, restarts, tiny files, incomplete deliveries and crashes.
- **Light**: bounded memory, cleans up after itself, runs anywhere Docker does.
- **Easy to connect**: optionally announces every received file on RabbitMQ.

## How it works

![The pipeline: folders, processes, threads and classes on each side of the diode](pipeline.svg)

## Running it

One image runs either side, chosen by `ENV_FOR_DYNACONF`:

```sh
docker compose -f receive.yml up -d   # on the receiving machine
docker compose -f send.yml up -d      # on the sending machine
```

Create one subfolder per channel under `external/input` before starting the sender; files dropped
into `external/input/<channel>` arrive in `external/output/<channel>`.

Without Docker (Python 3.11):

```sh
pip install -r requirements.txt
ENV_FOR_DYNACONF=receive python -m src.common.main
ENV_FOR_DYNACONF=send python -m src.common.main
```

## Configuration

All settings live in `resources/` and are commented in place; any of them can be overridden with
a `COURIER_` environment variable.

| Setting | Side | What it controls |
|---|---|---|
| `ip`, `port` | both | The receiver's address |
| `payload_size` | both | File bytes per packet |
| `encoder.packets_multiplier` | send | Redundancy: `2` sends twice the data |
| `pacer.speed_limit` | send | Total bytes per second across all channels |
| `scanner.file_ready_delay` | send | Seconds a file must stay unchanged before it is sent |
| `socket.buffer_size` | both | Kernel socket buffer size |
| `shm.size` | receive | Memory for packets waiting to be processed |
| `cleaner.partial_file_expiry` | receive | Seconds before an incomplete file is dropped |
| `rabbitmq.*` | receive | Where to announce received files |

Large socket buffers need the OS limit raised too (on Linux, `net.core.rmem_max` and
`net.core.wmem_max`).
