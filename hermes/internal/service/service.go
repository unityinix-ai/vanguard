// Package service implements the HermesAgentService gRPC server.
package service

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/unityinix-ai/vanguard/hermes/internal/agents"
)

// ExecutionRequest is a request to execute a task on a target agent.
type ExecutionRequest struct {
	AgentID  string
	TaskID  string
	TaskType string
	Payload  []byte
	Metadata map[string]string
}

// ExecutionResult is the result of an execution.
type ExecutionResult struct {
	TaskID    string
	Success   bool
	Output    []byte
	Error     string
	DurationMs int64
}

// CancelRequest is a request to cancel a running task.
type CancelRequest struct {
	TaskID string
	Reason string
}

// CancelResponse is the response to a cancellation request.
type CancelResponse struct {
	TaskID   string
	Cancelled bool
	Message  string
}

// HealthResponse is the health check response.
type HealthResponse struct {
	Status  string
	Version string
}

// ExecutionHandler is a function that processes execution requests.
type ExecutionHandler func(ctx context.Context, req *ExecutionRequest) (*ExecutionResult, error)

// HermesAgentService implements the agent execution runtime and communication service.
type HermesAgentService struct {
	Registry   *agents.Registry
	mu         sync.Mutex
	executing  map[string]context.CancelFunc
	handler    ExecutionHandler
	version    string
}

// NewHermesAgentService creates a new HermesAgentService.
func NewHermesAgentService(registry *agents.Registry, handler ExecutionHandler) *HermesAgentService {
	return &HermesAgentService{
		Registry:  registry,
		executing: make(map[string]context.CancelFunc),
		handler:   handler,
		version:   "1.0.0",
	}
}

// RegisterAgent registers or updates an agent.
func (s *HermesAgentService) RegisterAgent(agent *agents.Agent) (*agents.Agent, error) {
	log.Printf("Registering agent %s (%s) at %s", agent.ID, agent.Name, agent.Endpoint)
	return s.Registry.Register(agent)
}

// ListAgents returns all registered agents.
func (s *HermesAgentService) ListAgents() []*agents.Agent {
	return s.Registry.List()
}

// Execute dispatches an execution request to the configured handler.
func (s *HermesAgentService) Execute(ctx context.Context, req *ExecutionRequest) (*ExecutionResult, error) {
	// Verify agent exists
	_, err := s.Registry.Get(req.AgentID)
	if err != nil {
		return &ExecutionResult{
			TaskID:  req.TaskID,
			Success: false,
			Error:   fmt.Sprintf("agent %s not found", req.AgentID),
		}, nil
	}

	// Create cancellable context
	execCtx, cancel := context.WithCancel(ctx)
	s.mu.Lock()
	s.executing[req.TaskID] = cancel
	s.mu.Unlock()
	defer func() {
		s.mu.Lock()
		delete(s.executing, req.TaskID)
		s.mu.Unlock()
	}()

	if s.handler == nil {
		return &ExecutionResult{
			TaskID: req.TaskID,
			Success: false,
			Error:   "no execution handler configured",
		}, nil
	}

	start := time.Now()
	result, err := s.handler(execCtx, req)
	if result == nil {
		result = &ExecutionResult{}
	}
	result.TaskID = req.TaskID
	result.DurationMs = time.Since(start).Milliseconds()

	if err != nil {
		result.Success = false
		result.Error = err.Error()
	} else {
		result.Success = true
	}

	return result, nil
}

// Cancel cancels a running task.
func (s *HermesAgentService) Cancel(req *CancelRequest) *CancelResponse {
	s.mu.Lock()
	cancel, ok := s.executing[req.TaskID]
	s.mu.Unlock()

	if !ok {
		return &CancelResponse{
			TaskID:    req.TaskID,
			Cancelled: false,
			Message:   "task not found or already completed",
		}
	}

	cancel()
	return &CancelResponse{
		TaskID:    req.TaskID,
		Cancelled: true,
		Message:   req.Reason,
	}
}

// Health returns the service health status.
func (s *HermesAgentService) Health() *HealthResponse {
	return &HealthResponse{
		Status:  "ok",
		Version: s.version,
	}
}

// DefaultHandler is a mock execution handler that returns a predefined response.
func DefaultHandler(ctx context.Context, req *ExecutionRequest) (*ExecutionResult, error) {
	return &ExecutionResult{
		TaskID: req.TaskID,
		Output: []byte(fmt.Sprintf(`{"status":"completed","task_type":"%s","agent":"%s"}`, req.TaskType, req.AgentID)),
	}, nil
}
