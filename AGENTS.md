# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Web Tool Set is a FastAPI app exposing network diagnostic tools (ICMP ping, TCP
ping, port check, DNS nslookup/dig, traceroute, WHOIS, Wake-On-LAN, client IP)
over a JSON API plus a single-page web frontend.

## Commands

This project uses [uv](https://docs.astral.sh/uv/) for dependency and env
management. Targets Python 3.11+; CI runs on 3.12.

```bash
uv sync --extra dev                      # install with dev deps
uv run python -m app.main                # run the app (http://localhost:8000)
uv run uvicorn app.main:app --reload     # run with autoreload for development

uv run pytest tests/ -v                  # run all tests
uv run pytest tests/test_main.py::TestPingEndpoint -v   # run a single test class
uv run pytest tests/test_main.py::TestPingEndpoint::test_ping_localhost -v  # single test

uv run flake8 app/ tests/                # lint
```

Lint config is in `.flake8` (max line length 127, max complexity 10). CI
(`.github/workflows/python-app.yml`) fails the build only on syntax/undefined-name
errors (`E9,F63,F7,F82`); other flake8 findings are warnings.

## Architecture

Strict three-layer separation — keep these boundaries when adding tools:

- **`app/api/network.py`** — route handlers under the `/api` prefix. Handlers are
  thin: parse/validate input, call a service, and **map the service's error
  string to an HTTP status code** by substring matching (e.g. `"Name lookup"` →
  404, `"not reachable"` → 400). They never contain network logic.
- **`app/services/network.py`** — all business logic, as classes with
  `@staticmethod` methods (`PingService`, `TcpPingService`, `DnsService`,
  `TracerouteService`, `WhoisService`, `PortCheckService`, `WakeOnLanService`).
  Every service method returns a `(result, error)` tuple (or
  `(bool, latency, error)` for port checks) — **services never raise to the
  caller and never know about HTTP**. They catch library exceptions and return a
  human-readable error string instead.
- **`app/models/responses.py`** — Pydantic response models referenced by each
  route's `response_model`. Error responses use a shared `ErrorResponse`.

Supporting modules:
- **`app/main.py`** — app factory, middleware (CORS, slowapi rate limiting),
  static/template mounts, the `/` HTML root, and **legacy unprefixed endpoints**
  (`/ping`, `/tcping`, `/myip`, `/wol/...`) kept for backward compatibility.
  Don't remove these without reason.
- **`app/config.py`** — paths and app constants. All paths derive from
  `APP_DIR`/`BASE_DIR`; reuse these rather than hardcoding paths.
- **`app/utils/iputils.py`** — `get_real_ip()` resolves the client IP honoring
  `X-Real-IP` / `X-Forwarded-For` (app is meant to run behind a proxy;
  `--proxy-headers` is set in the Dockerfile).
- **`app/templates/index.html`** + `app/static/{css,js}` — the frontend; `app.js`
  calls the `/api/*` endpoints.

### Adding a new network tool

1. Add a service class/method in `services/network.py` returning `(result, error)`.
2. Add a Pydantic response model in `models/responses.py`.
3. Add a route in `api/network.py` that calls the service and maps error
   substrings to status codes.
4. Wire it into the frontend (`templates/index.html`, `static/js/app.js`).

## Notes

- ICMP ping and traceroute use raw sockets (`icmplib`) which **require elevated
  privileges**; they may fail in restricted CI/container environments. Tests for
  these skip gracefully when ICMP is unavailable.
- Rate limiting is global via slowapi keyed on remote address; `RATE_LIMIT_PER_MINUTE`
  lives in `config.py`.
- Docker exposes port **80** (mapped to 8000 in `docker-compose.yml`); running
  directly serves on **8000**.
