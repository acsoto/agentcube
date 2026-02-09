package router

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/volcano-sh/agentcube/pkg/common/types"
)

// mockStore for benchmark
type mockStore struct {
	updateLatency time.Duration
}

func (m *mockStore) Ping(ctx context.Context) error { return nil }
func (m *mockStore) GetSandboxBySessionID(ctx context.Context, sessionID string) (*types.SandboxInfo, error) {
	return nil, nil
}
func (m *mockStore) StoreSandbox(ctx context.Context, sandboxStore *types.SandboxInfo) error {
	return nil
}
func (m *mockStore) UpdateSandbox(ctx context.Context, sandboxStore *types.SandboxInfo) error {
	return nil
}
func (m *mockStore) DeleteSandboxBySessionID(ctx context.Context, sessionID string) error { return nil }
func (m *mockStore) ListExpiredSandboxes(ctx context.Context, before time.Time, limit int64) ([]*types.SandboxInfo, error) {
	return nil, nil
}
func (m *mockStore) ListInactiveSandboxes(ctx context.Context, before time.Time, limit int64) ([]*types.SandboxInfo, error) {
	return nil, nil
}
func (m *mockStore) UpdateSessionLastActivity(ctx context.Context, sessionID string, at time.Time) error {
	if m.updateLatency > 0 {
		time.Sleep(m.updateLatency)
	}
	return nil
}

// benchmarkResponseWriter implements http.CloseNotifier to satisfy ReverseProxy
type benchmarkResponseWriter struct {
	*httptest.ResponseRecorder
}

func (w *benchmarkResponseWriter) CloseNotify() <-chan bool {
	return make(chan bool)
}

// BenchmarkHandleInvoke benchmarks the handleInvoke method
func BenchmarkHandleInvoke(b *testing.B) {
	gin.SetMode(gin.ReleaseMode)

	// 1. Setup Mock Sandbox Target
	targetSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer targetSrv.Close()

	// 2. Setup Server
	ms := &mockStore{updateLatency: 1 * time.Millisecond} // Simulate 1ms Redis latency

	// Mock Session Manager
	sm := &mockSessionManager{
		sandbox: &types.SandboxInfo{
			SandboxID: "bench-sandbox",
			SessionID: "bench-session",
			EntryPoints: []types.SandboxEntryPoint{
				{Endpoint: targetSrv.URL, Path: "/"},
			},
		},
	}

	server := &Server{
		config: &Config{
			MaxConcurrentRequests: 100, // Avoid concurrency limit
		},
		storeClient:    ms,
		sessionManager: sm,
		httpTransport:  &http.Transport{}, // Simple transport
	}
	server.setupRoutes() // Initialize engine

	// 3. Prepare Request
	url := "/v1/namespaces/default/agent-runtimes/test/invocations/path"

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		w := &benchmarkResponseWriter{httptest.NewRecorder()}
		req, _ := http.NewRequest("GET", url, nil)
		req.Header.Set("x-agentcube-session-id", "bench-session")
		server.engine.ServeHTTP(w, req)
	}
}
