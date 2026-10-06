// Package main is the entry point for the Hermes gRPC server.
package main

import (
	"context"
	"flag"
	"log"
	"net"
	"os"
	"os/signal"
	"syscall"

	"github.com/akatsuki333/vanguard/hermes/internal/agents"
	"github.com/akatsuki333/vanguard/hermes/internal/service"
)

func main() {
	port := flag.Int("port", 50051, "gRPC server port")
	host := flag.String("host", "0.0.0.0", "gRPC server host")
	flag.Parse()

	addr := fmt.Sprintf("%s:%d", *host, *port)

	// Create the agent registry
	registry := agents.NewRegistry()

	// Register a default agent for local execution
	registry.Register(&agents.Agent{
		ID:           "default",
		Name:         "Default Agent",
		Runtime:      "aurora",
		Endpoint:     "ws://aurora:8001",
		Capabilities: []string{"llm_completion", "voice_command"},
	})

	// Create the Hermes service
	svc := service.NewHermesAgentService(registry, service.DefaultHandler)

	// Start TCP listener
	lis, err := net.Listen("tcp", addr)
	if err != nil {
		log.Fatalf("Failed to listen on %s: %v", addr, err)
	}

	log.Printf("Hermes agent service starting on %s", addr)
	log.Printf("Registered %d agent(s)", registry.Count())

	// Health check info
	health := svc.Health()
	log.Printf("Health: status=%s version=%s", health.Status, health.Version)

	// Set up graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		sig := <-sigCh
		log.Printf("Received signal %s, shutting down...", sig)
		cancel()
	}()

	// Keep the server running until context is cancelled
	<-ctx.Done()
	log.Println("Hermes server stopped")
}
