/*
Copyright The Volcano Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

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

func (m *mockStore) Ping(_ context.Context) error { return nil }
func (m *mockStore) GetSandboxBySessionID(_ context.Context, _ string) (*types.SandboxInfo, error) {
	return nil, nil
}
func (m *mockStore) StoreSandbox(_ context.Context, _ *types.SandboxInfo) error {
	return nil
}
func (m *mockStore) UpdateSandbox(_ context.Context, _ *types.SandboxInfo) error {
	return nil
}
func (m *mockStore) DeleteSandboxBySessionID(_ context.Context, _ string) error { return nil }
func (m *mockStore) ListExpiredSandboxes(_ context.Context, _ time.Time, _ int64) ([]*types.SandboxInfo, error) {
	return nil, nil
}
func (m *mockStore) ListInactiveSandboxes(_ context.Context, _ time.Time, _ int64) ([]*types.SandboxInfo, error) {
	return nil, nil
}
func (m *mockStore) UpdateSessionLastActivity(_ context.Context, _ string, _ time.Time) error {
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
	targetSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
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
