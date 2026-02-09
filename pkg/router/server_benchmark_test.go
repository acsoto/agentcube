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
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
)

// BenchmarkTransportConcurrency measures the performance of the Server's HTTP transport
// with concurrent requests.
func BenchmarkTransportConcurrency(b *testing.B) {
	// 1. Setup Miniredis
	mr, err := miniredis.Run()
	if err != nil {
		b.Fatalf("failed to start miniredis: %v", err)
	}
	defer mr.Close()

	// 2. Setup Environment Variables for Store
	os.Setenv("REDIS_ADDR", mr.Addr())
	os.Setenv("REDIS_PASSWORD", "dummy")
	os.Setenv("WORKLOAD_MANAGER_URL", "http://localhost:8080")
	defer os.Unsetenv("REDIS_ADDR")
	defer os.Unsetenv("REDIS_PASSWORD")
	defer os.Unsetenv("WORKLOAD_MANAGER_URL")

	// 3. Create Server instance to get the transport
	config := &Config{
		Port: "0",
	}
	// Note: NewServer calls store.Storage() which initializes the singleton.
	// Make sure this is the first test/benchmark running in this process
	// or use -run=^$ to skip other tests.
	server, err := NewServer(config)
	if err != nil {
		b.Fatalf("failed to create server: %v", err)
	}

	// 4. Create a dummy backend server
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// simulate minimal work
		w.WriteHeader(http.StatusOK)
	}))
	defer backend.Close()

	client := &http.Client{
		Transport: server.httpTransport,
		Timeout:   2 * time.Second,
	}

	b.ResetTimer()

	// 5. Run benchmark
	b.RunParallel(func(pb *testing.PB) {
		for pb.Next() {
			resp, err := client.Get(backend.URL)
			if err != nil {
				// In high concurrency, we might hit limits, but we want to measure successful requests or see errors
				// b.Logf("request failed: %v", err)
				continue
			}
			resp.Body.Close()
		}
	})
}
