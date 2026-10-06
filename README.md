# Vanguard Multi-Agent System

A multi-agent framework with three coordinated services for asynchronous execution pipelines, agent runtime communication, and multi-modal LLM routing.

## Architecture

```
Client → Caddy → Gedo API → Hermes gRPC runtime
                              ↓
                      Aurora routing service
                              ↓
                       Configured LLM provider
```

| Framework | Responsibility | Stack | Port |
|-----------|---------------|-------|------|
| **Gedo** | Async execution pipelines, job state, voice command dispatch | Python, FastAPI, Pydantic | 8000 |
| **Hermes** | Agent execution runtime and gRPC communication | Go, gRPC, Protocol Buffers | 50051 |
| **Aurora** | Multi-modal LLM execution, routing, compliance logging, runtime guard | Python, WebSockets | 8001 |
| **Caddy** | Reverse proxy and routing | Caddy | 8080 |

## Project layout

```
vanguard/
├── contracts/
│   └── vanguard.proto          # Shared protobuf definitions
├── gedo/
│   ├── app/
│   │   ├── api.py              # FastAPI endpoints
│   │   ├── orchestrator.py     # AsyncSynchronizedVanguard
│   │   ├── state.py            # SystemState job lifecycle
│   │   └── commands.py         # VoiceCommandDispatcher
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── hermes/
│   ├── cmd/server/main.go      # gRPC server entry point
│   ├── internal/
│   │   ├── agents/registry.go  # Agent registration
│   │   └── service/service.go  # HermesAgentService
│   ├── go.mod
│   └── Dockerfile
├── aurora/
│   ├── app/
│   │   ├── server.py           # WebSocket server
│   │   ├── routing.py         # Model routing & proxy config
│   │   ├── guard.py            # SoulRuntimeGuard
│   │   └── compliance.py      # RuntimeComplianceLogs
│   ├── tests/
│   └── Dockerfile
├── deployment/
│   ├── Caddyfile               # Reverse proxy config
│   └── vanguard.service        # systemd unit
├── compose.yaml
├── .env.example
└── README.md
```

## Quick start

### Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Services will be available at:
- Caddy (entry point): http://localhost:8080
- Gedo API: http://localhost:8000
- Aurora WebSocket: ws://localhost:8001/ws
- Hermes gRPC: localhost:50051

### API examples

Submit a job:
```bash
curl -X POST http://localhost:8080/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"task_type": "llm_completion", "payload": {"prompt": "hello"}}'
```

Voice command:
```bash
curl -X POST http://localhost:8080/api/voice \
  -H "Content-Type: application/json" \
  -d '{"text": "run llm_completion"}'
```

Check job status:
```bash
curl http://localhost:8080/api/jobs/{job_id}
```

## Development

### Gedo (Python)

```bash
cd gedo
pip install -e ".[dev]"
pytest
```

### Hermes (Go)

```bash
cd hermes
go test ./...
go run ./cmd/server
```

### Aurora (Python)

```bash
cd aurora
pip install -e ".[dev]"
pytest
```

## Configuration

LLM execution runs in mock mode by default. To use a real provider, set environment variables in `.env`:

```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4
```

## License

Organization: akatsuki333
