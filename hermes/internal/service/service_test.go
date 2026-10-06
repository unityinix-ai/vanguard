package service

import (
	"context"
	"testing"

	"github.com/akatsuki333/vanguard/hermes/internal/agents"
)

func TestExecuteSuccess(t *testing.T) {
	r := agents.NewRegistry()
	r.Register(&agents.Agent{
		ID:       "test-agent",
		Name:     "Test",
		Runtime:  "aurora",
		Endpoint: "ws://test",
	})

	handler := func(ctx context.Context, req *ExecutionRequest) (*ExecutionResult, error) {
		return &ExecutionResult{
			Output: []byte("executed"),
		}, nil
	}

	svc := NewHermesAgentService(r, handler)

	result, err := svc.Execute(context.Background(), &ExecutionRequest{
		AgentID:  "test-agent",
		TaskID:   "task-1",
		TaskType: "llm_completion",
		Payload:  []byte("{}"),
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !result.Success {
		t.Error("expected success=true")
	}
	if result.TaskID != "task-1" {
		t.Errorf("expected task-1, got %s", result.TaskID)
	}
	if result.DurationMs < 0 {
		t.Error("expected non-negative duration")
	}
}

func TestExecuteAgentNotFound(t *testing.T) {
	r := agents.NewRegistry()
	svc := NewHermesAgentService(r, DefaultHandler)

	result, _ := svc.Execute(context.Background(), &ExecutionRequest{
		AgentID:  "nonexistent",
		TaskID:   "task-1",
		TaskType:  "test",
	})

	if result.Success {
		t.Error("expected success=false for missing agent")
	}
}

func TestCancelNonExistent(t *testing.T) {
	r := agents.NewRegistry()
	svc := NewHermesAgentService(r, DefaultHandler)

	resp := svc.Cancel(&CancelRequest{
		TaskID: "nonexistent",
		Reason: "test",
	})

	if resp.Cancelled {
		t.Error("expected cancelled=false for non-existent task")
	}
}

func TestHealth(t *testing.T) {
	r := agents.NewRegistry()
	svc := NewHermesAgentService(r, DefaultHandler)

	health := svc.Health()
	if health.Status != "ok" {
		t.Errorf("expected status 'ok', got '%s'", health.Status)
	}
	if health.Version != "1.0.0" {
		t.Errorf("expected version '1.0.0', got '%s'", health.Version)
	}
}

func TestDefaultHandler(t *testing.T) {
	handler := DefaultHandler
	result, err := handler(context.Background(), &ExecutionRequest{
		AgentID:  "test",
		TaskID:   "task-1",
		TaskType: "llm_completion",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(result.Output) == 0 {
		t.Error("expected non-empty output from default handler")
	}
}
