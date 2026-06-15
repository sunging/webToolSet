# Web Tool Set

A modern network diagnostic toolkit built with FastAPI, featuring ICMP Ping, TCP Ping, Wake On LAN, and more with a beautiful web interface.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-green)
![License](https://img.shields.io/badge/License-GPL%20v3-blue)

## ✨ Features

- 🔍 **ICMP Ping** - Test host reachability and network latency
- 🌐 **TCP Ping** - Test TCP port connectivity and response time
- 🔎 **NSLookup** - Resolve hostnames to addresses (and reverse PTR lookups)
- 📇 **Dig** - Query specific DNS record types (A, AAAA, MX, NS, TXT, ...)
- 🗺️ **Traceroute** - Trace the network path to a host
- 📜 **Whois** - Look up registration info for domains and IPs
- 💻 **Wake On LAN** - Remote wake up network devices
- 📋 **IP Query** - Get client's real IP address
- 🎨 **Modern Frontend** - Responsive UI with auto light/dark theme
- 🛡️ **Security** - Built-in rate limiting to prevent abuse
- 🐳 **Docker Support** - Ready-to-use containerized deployment

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Option 1: Run Directly

```bash
# Clone the repository
git clone https://github.com/sunging/webToolSet.git
cd webToolSet

# Install dependencies
uv sync

# Run the application
uv run python -m app.main

# Or use uvicorn
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Option 2: Docker Deployment

```bash
# Using docker-compose
docker-compose up -d

# Or build manually
docker build -t webtoolset .
docker run -d -p 8000:80 webtoolset
```

Visit http://localhost:8000 to use the application.

### Development Mode

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest tests/ -v

# Code linting
uv run flake8 app/ tests/
```

## 📖 API Documentation

After starting the server, visit:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Frontend page |
| `/api/health` | GET | Health check |
| `/api/ping` | GET | Ping client IP |
| `/api/ping/{address}` | GET | Ping specified address |
| `/api/tcping` | GET | TCP Ping client IP |
| `/api/tcping/{address}` | GET | TCP Ping specified address |
| `/api/nslookup/{address}` | GET | Resolve hostname/IP via DNS |
| `/api/dig/{address}` | GET | Query DNS records (`?type=A`) |
| `/api/traceroute/{address}` | GET | Trace network path to host |
| `/api/whois/{query}` | GET | WHOIS lookup for domain/IP |
| `/api/myip` | GET | Get client IP |
| `/api/wol/{mac_addr}` | GET | Send wake packet |

### Example Requests

```bash
# Ping test
curl http://localhost:8000/api/ping/8.8.8.8

# TCP Ping test
curl "http://localhost:8000/api/tcping/8.8.8.8?port=53&timeout=3"

# DNS lookup
curl http://localhost:8000/api/nslookup/example.com

# DNS record query (dig)
curl "http://localhost:8000/api/dig/example.com?type=MX"

# Traceroute
curl "http://localhost:8000/api/traceroute/8.8.8.8?max_hops=20"

# Whois lookup
curl http://localhost:8000/api/whois/example.com

# Get IP
curl http://localhost:8000/api/myip

# Wake On LAN
curl http://localhost:8000/api/wol/AA:BB:CC:DD:EE:FF
```

## 📁 Project Structure

```
webToolSet/
├── app/
│   ├── api/                 # API routes
│   │   └── network.py       # Network tools routes
│   ├── models/              # Data models
│   │   └── responses.py     # Response models
│   ├── services/            # Business logic
│   │   └── network.py       # Network services
│   ├── static/              # Static files
│   │   ├── css/
│   │   ├── img/
│   │   └── js/
│   ├── templates/           # HTML templates
│   │   └── index.html
│   ├── utils/               # Utility functions
│   │   ├── iputils.py       # IP utilities
│   │   └── tcping.py        # TCP Ping implementation
│   ├── config.py            # Configuration
│   ├── logging.yml          # Logging config
│   └── main.py              # Application entry
├── tests/                   # Test files
│   └── test_main.py
├── log/                     # Log directory
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TZ` | Timezone | `Asia/Shanghai` |

### Logging

Logging configuration is in `app/logging.yml`:

- Console output: INFO level
- File output: `log/app.log`, max 10MB, 5 backups

## 🔧 Development

### Install Dev Dependencies

```bash
uv sync --extra dev
```

### Run Tests

```bash
uv run pytest tests/ -v
```

### Code Linting

```bash
uv run flake8 app/ tests/
```

### Add New Dependencies

```bash
# Add runtime dependency
uv add package-name

# Add dev dependency
uv add --dev package-name
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 Changelog

### v1.0.0

- ✨ New modern frontend UI
- 🔧 Refactored project architecture (API/Service/Model separation)
- 🛡️ Added rate limiting and CORS configuration
- 🐳 Improved Docker configuration
- ✅ Enhanced test coverage
- 📚 Updated documentation

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [icmplib](https://github.com/ValentinBELYN/icmplib) - ICMP protocol implementation
- [wakeonlan](https://github.com/remcohaszing/pywakeonlan) - Wake On LAN implementation
