package agents

import (
	"testing"
)

func TestRegisterAndGet(t *testing.T) {
	r := NewRegistry()

	agent := &Agent{
		ID:       "agent-1",
		Name:     "Test Agent",
		Runtime:  "aurora",
		Endpoint: "ws://localhost:8001",
	}
	r.Register(agent)

	got, err := r.Get("agent-1")
	if err != nil {
		t.Fatalf("expected agent, got error: %v", err)
	}
	if got.Name != "Test Agent" {
		t.Errorf("expected name 'Test Agent', got '%s'", got.Name)
	}
}

func TestGetNotFound(t *testing.T) {
	r := NewRegistry()

	_, err := r.Get("nonexistent")
	if err != ErrAgentNotFound {
		t.Errorf("expected ErrAgentNotFound, got %v", err)
	}
}

func TestListAgents(t *testing.T) {
	r := NewRegistry()

	r.Register(&Agent{ID: "a1", Name: "Agent 1"})
	r.Register(&Agent{ID: "a2", Name: "Agent 2"})

	list := r.List()
	if len(list) != 2 {
		t.Errorf("expected 2 agents, got %d", len(list))
	}
}

func TestUpdateExisting(t *testing.T) {
	r := NewRegistry()

	r.Register(&Agent{ID: "a1", Name: "Original", Endpoint: "old"})
	r.Register(&Agent{ID: "a1", Name: "Updated", Endpoint: "new"})

	got, _ := r.Get("a1")
	if got.Name != "Updated" {
		t.Errorf("expected updated name, got '%s'", got.Name)
	}
	if got.Endpoint != "new" {
		t.Errorf("expected updated endpoint, got '%s'", got.Endpoint)
	}
}

func TestRemove(t *testing.T) {
	r := NewRegistry()

	r.Register(&Agent{ID: "a1", Name: "Test"})
	err := r.Remove("a1")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}

	_, err = r.Get("a1")
	if err != ErrAgentNotFound {
		t.Errorf("expected not found after removal, got %v", err)
	}
}

func TestCount(t *testing.T) {
	r := NewRegistry()

	if r.Count() != 0 {
		t.Error("expected 0 agents initially")
	}

	r.Register(&Agent{ID: "a1"})
	r.Register(&Agent{ID: "a2"})

	if r.Count() != 2 {
		t.Errorf("expected 2 agents, got %d", r.Count())
	}
}
