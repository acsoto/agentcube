package workloadmanager

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/volcano-sh/agentcube/pkg/common/types"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/client-go/dynamic/fake"
)

type BenchmarkStore struct {
	sandboxes          []*types.SandboxInfo
	originalSandboxes  []*types.SandboxInfo
}

func NewBenchmarkStore(count int) *BenchmarkStore {
	sandboxes := make([]*types.SandboxInfo, count)
	for i := 0; i < count; i++ {
		sandboxes[i] = &types.SandboxInfo{
			Kind:             types.SandboxKind,
			SandboxNamespace: "default",
			Name:             fmt.Sprintf("sandbox-%d", i),
			SessionID:        fmt.Sprintf("session-%d", i),
		}
	}
	// Copy to originalSandboxes
	original := make([]*types.SandboxInfo, count)
	copy(original, sandboxes)

	return &BenchmarkStore{
		sandboxes:         sandboxes,
		originalSandboxes: original,
	}
}

func (s *BenchmarkStore) Reset() {
	s.sandboxes = make([]*types.SandboxInfo, len(s.originalSandboxes))
	copy(s.sandboxes, s.originalSandboxes)
}

func (s *BenchmarkStore) Ping(ctx context.Context) error { return nil }
func (s *BenchmarkStore) GetSandboxBySessionID(ctx context.Context, sessionID string) (*types.SandboxInfo, error) { return nil, nil }
func (s *BenchmarkStore) StoreSandbox(ctx context.Context, sandboxStore *types.SandboxInfo) error { return nil }
func (s *BenchmarkStore) UpdateSandbox(ctx context.Context, sandboxStore *types.SandboxInfo) error { return nil }
func (s *BenchmarkStore) DeleteSandboxBySessionID(ctx context.Context, sessionID string) error { return nil }
func (s *BenchmarkStore) ListExpiredSandboxes(ctx context.Context, before time.Time, limit int64) ([]*types.SandboxInfo, error) { return []*types.SandboxInfo{}, nil }

func (s *BenchmarkStore) ListInactiveSandboxes(ctx context.Context, before time.Time, limit int64) ([]*types.SandboxInfo, error) {
	l := int(limit)
	if len(s.sandboxes) < l {
		l = len(s.sandboxes)
	}
	if l == 0 {
		return []*types.SandboxInfo{}, nil
	}
	ret := s.sandboxes[:l]
	s.sandboxes = s.sandboxes[l:]
	return ret, nil
}

func (s *BenchmarkStore) UpdateSessionLastActivity(ctx context.Context, sessionID string, at time.Time) error { return nil }

func BenchmarkGarbageCollector_Once(b *testing.B) {
	// Setup K8s Client
	scheme := runtime.NewScheme()
	dynamicClient := fake.NewSimpleDynamicClient(scheme)
	k8sClient := &K8sClient{
		dynamicClient: dynamicClient,
	}

	totalItems := 1000
	store := NewBenchmarkStore(totalItems)

	gc := newGarbageCollector(k8sClient, store, time.Minute, 16)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		b.StopTimer() // Pause timer while resetting
		store.Reset()
		b.StartTimer() // Resume timer

		for {
			// Check if we are done
			// We can peek into store.sandboxes directly since it's our struct
			if len(store.sandboxes) == 0 {
				break
			}
			gc.once()
		}
	}
}

func BenchmarkGarbageCollector_Once_LargeBatch(b *testing.B) {
	// Setup K8s Client
	scheme := runtime.NewScheme()
	dynamicClient := fake.NewSimpleDynamicClient(scheme)
	k8sClient := &K8sClient{
		dynamicClient: dynamicClient,
	}

	totalItems := 1000
	store := NewBenchmarkStore(totalItems)

	gc := newGarbageCollector(k8sClient, store, time.Minute, 100)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		b.StopTimer() // Pause timer while resetting
		store.Reset()
		b.StartTimer() // Resume timer

		for {
			// Check if we are done
			if len(store.sandboxes) == 0 {
				break
			}
			gc.once()
		}
	}
}
