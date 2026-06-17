# Web Tool Set

Web Tool Set is a FastAPI application that exposes common network diagnostic
tools through a JSON API and a single-page web interface.

It includes ICMP ping, TCP ping, DNS lookups, reverse DNS, DNS record queries,
traceroute, WHOIS, TCP port checks, Wake-On-LAN, and client IP detection.

## Features

- Web UI served from `/`
- JSON API under `/api`
- ICMP ping and TCP ping
- DNS `nslookup`, reverse PTR lookup, and `dig`-style record queries
- Traceroute with configurable hop and timeout limits
- WHOIS lookup for domains and IP addresses
- TCP port availability checks
- Wake-On-LAN magic packet support
- Client IP detection with proxy header support
- Global request rate limiting
- Docker and uv-based local development workflows

## Requirements

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/) for dependency and environment management
- Elevated privileges for ICMP ping and traceroute in some environments

The Docker image uses Python 3.12.

## Quick Start

Install dependencies:

```bash
uv sync
```

Run the app:

```bash
uv run python -m app.main
```

Open:

```text
http://localhost:8000
```

For autoreload during development:

```bash
uv run uvicorn app.main:app --reload
```

## Development

Install runtime and development dependencies:

```bash
uv sync --extra dev
```

Run tests:

```bash
uv run pytest tests/ -v
```

Run a single test class:

```bash
uv run pytest tests/test_main.py::TestPingEndpoint -v
```

Run a single test:

```bash
uv run pytest tests/test_main.py::TestPingEndpoint::test_ping_localhost -v
```

Run lint:

```bash
uv run flake8 app/ tests/
```

Add dependencies:

```bash
uv add package-name
uv add --dev package-name
```

## Docker

Run with Compose:

```bash
docker-compose up -d
```

Build and run manually:

```bash
docker build -t webtoolset .
docker run -d -p 8000:80 webtoolset
```

The container listens on port 80. The Compose file maps host port 8000 to the
container.

## API Documentation

When the application is running, FastAPI serves interactive API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/health` | GET | Health check |
| `/api/ping` | GET | ICMP ping the detected client IP |
| `/api/ping/{address}` | GET | ICMP ping an address or hostname |
| `/api/tcping` | GET | TCP ping the detected client IP |
| `/api/tcping/{address}` | GET | TCP ping an address or hostname |
| `/api/nslookup/{address}` | GET | Resolve A/AAAA records for a name |
| `/api/dig/{address}` | GET | Query DNS records |
| `/api/reverse-ip` | GET | Reverse lookup the detected client IP |
| `/api/reverse-ip/{address}` | GET | Reverse lookup an IP address |
| `/api/traceroute/{address}` | GET | Trace the network path to a host |
| `/api/whois/{query}` | GET | WHOIS lookup for a domain or IP |
| `/api/myip` | GET | Return the detected client IP |
| `/api/port/{address}/{port}` | GET | Check whether a TCP port is open |
| `/api/wol/{mac_addr}` | GET | Send a Wake-On-LAN magic packet |

Legacy unprefixed endpoints are kept for backward compatibility:

- `/ping`
- `/ping/{address}`
- `/tcping`
- `/tcping/{address}`
- `/myip`
- `/wol/{mac_addr}`

## Example Requests

```bash
# Ping
curl http://localhost:8000/api/ping/8.8.8.8

# TCP ping
curl "http://localhost:8000/api/tcping/8.8.8.8?port=53&timeout=3"

# DNS lookup
curl http://localhost:8000/api/nslookup/example.com

# DNS record query
curl "http://localhost:8000/api/dig/example.com?type=MX"

# Reverse DNS lookup
curl http://localhost:8000/api/reverse-ip/8.8.8.8

# Traceroute
curl "http://localhost:8000/api/traceroute/8.8.8.8?max_hops=20&timeout=2"

# WHOIS lookup
curl "http://localhost:8000/api/whois/example.com?timeout=5"

# Client IP
curl http://localhost:8000/api/myip

# TCP port check
curl "http://localhost:8000/api/port/127.0.0.1/8000?timeout=1"

# Wake-On-LAN
curl http://localhost:8000/api/wol/AA:BB:CC:DD:EE:FF
```

## Query Parameters

| Endpoint | Parameter | Range / Default | Description |
| --- | --- | --- | --- |
| `/api/tcping/{address}` | `port` | 1-65535, default 80 | TCP port to connect to |
| `/api/tcping/{address}` | `timeout` | 1-30, default 2 | Connection timeout in seconds |
| `/api/dig/{address}` | `type` | default `A` | DNS record type, such as `A`, `AAAA`, `MX`, `TXT`, `CNAME`, or `NS` |
| `/api/traceroute/{address}` | `max_hops` | 1-64, default 30 | Maximum hop count |
| `/api/traceroute/{address}` | `timeout` | 1-30, default 2 | Per-hop timeout in seconds |
| `/api/whois/{query}` | `timeout` | 1-30, default 5 | WHOIS connection timeout in seconds |
| `/api/port/{address}/{port}` | `timeout` | 0.1-30.0, default 2.0 | TCP connection timeout in seconds |

## Configuration

Configuration is read from environment variables.

| Variable | Default | Description |
| --- | --- | --- |
| `RATE_LIMIT_PER_MINUTE` | `60` | Global request limit per client per minute |

Example:

```bash
RATE_LIMIT_PER_MINUTE=120 uv run python -m app.main
```

On Windows PowerShell:

```powershell
$env:RATE_LIMIT_PER_MINUTE = "120"
uv run python -m app.main
```

## Project Structure

```text
app/
  api/
    network.py          API route handlers under /api
  models/
    responses.py        Pydantic response models
  services/
    network.py          Network tool business logic
  static/
    css/
    img/
    js/
  templates/
    index.html          Single-page frontend
  utils/
    iputils.py          Client IP detection
    tcping.py           TCP ping helper
  config.py             Paths and app constants
  main.py               FastAPI app, middleware, frontend, legacy routes
tests/
  test_main.py
```

## Architecture

The application keeps a strict three-layer separation:

- `app/api/network.py` contains thin route handlers. Handlers validate request
  parameters, call a service, and translate service error strings into HTTP
  status codes.
- `app/services/network.py` contains network and business logic. Service methods
  return result/error tuples and do not raise application errors to callers.
- `app/models/responses.py` contains Pydantic response models used by route
  `response_model` declarations.

Supporting modules:

- `app/main.py` creates the FastAPI app, configures CORS and rate limiting,
  serves static/templates, and keeps legacy unprefixed endpoints.
- `app/config.py` centralizes paths and constants.
- `app/utils/iputils.py` detects the real client IP using `X-Real-IP` and
  `X-Forwarded-For` headers when present.

## Adding a Network Tool

1. Add a service class or method in `app/services/network.py`.
2. Return `(result, error)` from service methods, or the existing tuple shape for
   related tools.
3. Add a response model in `app/models/responses.py`.
4. Add a thin route in `app/api/network.py`.
5. Map service error strings to HTTP status codes in the route.
6. Wire the tool into `app/templates/index.html` and `app/static/js/app.js` if it
   should appear in the web UI.
7. Add focused tests in `tests/test_main.py`.

## Notes

- ICMP ping and traceroute use raw sockets through `icmplib`; they may require
  elevated privileges or fail in restricted containers and CI environments.
- Tests that depend on ICMP availability skip gracefully when raw socket support
  is unavailable.
- The app is designed to run behind a proxy. The Dockerfile starts uvicorn with
  proxy header support.
- CI treats syntax and undefined-name flake8 errors as build failures; other
  flake8 findings are reported as warnings.

## License

This project is licensed under GPL-3.0-or-later. See [LICENSE](LICENSE).
