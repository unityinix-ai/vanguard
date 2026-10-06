// Package agents provides agent registration and lookup for Hermes.
package agents

import (
	"errors"
	"sync"
)

// Agent represents a registered agent in the Vanguard system.
type Agent struct {
	ID           string
	Name         string
	Runtime      string
	Endpoint     string
	Capabilities []string
}

// Registry manages agent registration with thread-safe access.
type Registry struct {
	mu     sync.RWMutex
	agents map[string]*Agent
}

// ErrAgentNotFound is returned when a requested agent is not registered.
var ErrAgentNotFound = errors.New("agent not found")

// ErrAgentAlreadyRegistered is returned when registering a duplicate agent ID.
var ErrAgentAlreadyRegistered = errors.New("agent already registered")

// NewRegistry creates a new agent registry.
func NewRegistry() *Registry {
	return &Registry{
		agents: make(map[string]*Agent),
	}
}

// Register adds or updates an agent in the registry.
func (r *Registry) Register(a *Agent) (*Agent, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	if existing, ok := r.agents[a.ID]; ok {
		// Update existing agent
		existing.Name = a.Name
		existing.Runtime = a.Runtime
		existing.Endpoint = a.Endpoint
		existing.Capabilities = a.Capabilities
		return existing, nil
	}

	// Store a copy to prevent external mutation
	agent := &Agent{
		ID:           a.ID,
		Name:         a.Name,
		Runtime:      a.Runtime,
		Endpoint:     a.Endpoint,
		Capabilities: append([]string{}, a.Capabilities...),
	}
	r.agents[a.ID] = agent
	return agent, nil
}

// Get retrieves an agent by ID.
func (r *Registry) Get(id string) (*Agent, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	agent, ok := r.agents[id]
	if !ok {
		return nil, ErrAgentNotFound
	}
	return agent, nil
}

// List returns all registered agents.
func (r *Registry) List() []*Agent {
	r.mu.RLock()
	defer r.mu.RUnlock()

	result := make([]*Agent, 0, len(r.agents))
	for _, a := range r.agents {
		result = append(result, &Agent{
			ID:           a.ID,
			Name:         a.Name,
			Runtime:      a.Runtime,
			Endpoint:     a.Endpoint,
			Capabilities: append([]string{}, a.Capabilities...),
		})
	}
	return result
}

// Remove deletes an agent from the registry.
func (r *Registry) Remove(id string) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	if _, ok := r.agents[id]; !ok {
		return ErrAgentNotFound
	}
	delete(r.agents, id)
	return nil
}

// Count returns the number of registered agents.
func (r *Registry) Count() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.agents)
}
