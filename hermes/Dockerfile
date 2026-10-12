FROM golang:1.22-alpine AS builder

WORKDIR /app

COPY go.mod go.sum* ./
RUN go mod download 2>/dev/null || true

COPY . .
RUN go build -o /hermes-server ./cmd/server

FROM alpine:3.20

WORKDIR /app

COPY --from=builder /hermes-server /app/hermes-server

EXPOSE 50051

CMD ["sh", "-c", "/app/hermes-server --port ${PORT:-50051}"]
