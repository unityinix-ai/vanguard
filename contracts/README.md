# Vanguard protocol contracts

Shared Protocol Buffers definitions for the Vanguard Multi-Agent System.

## Services

- **HermesAgentService** — gRPC service for agent registration, execution dispatch, and cancellation.
- **Health** — health check endpoint.

## Generating stubs

### Go (Hermes)

```bash
protoc --go_out=. --go-grpc_out=. \
  --go_opt=module=github.com/unityinix-ai/vanguard \
  --go-grpc_opt=module=github.com/unityinix-ai/vanguard \
  contracts/vanguard.proto
```

### Python (Gedo / Aurora)

```bash
python -m grpc_tools.protoc -I contracts \
  --python_out=gedo/gen --grpc_python_out=gedo/gen \
  contracts/vanguard.proto
```
