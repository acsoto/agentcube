package store

import (
	"context"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	redisv9 "github.com/redis/go-redis/v9"
	"github.com/volcano-sh/agentcube/pkg/common/types"
)

func BenchmarkUpdateSessionLastActivity(b *testing.B) {
	mr, err := miniredis.Run()
	if err != nil {
		b.Fatal(err)
	}
	defer mr.Close()

	rs := &redisStore{
		cli:                  redisv9.NewClient(&redisv9.Options{Addr: mr.Addr()}),
		sessionPrefix:        "session:",
		expiryIndexKey:       "session:expiry",
		lastActivityIndexKey: "session:last_activity",
	}

	ctx := context.Background()
	sessionID := "benchmark-session"

	// Setup session
	sb := &types.SandboxInfo{
		SessionID: sessionID,
		ExpiresAt: time.Now().Add(1 * time.Hour),
		Status:    "running",
	}
	if err := rs.StoreSandbox(ctx, sb); err != nil {
		b.Fatal(err)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		// Use a changing time to ensure updates happen
		at := time.Now().Add(time.Duration(i) * time.Second)
		if err := rs.UpdateSessionLastActivity(ctx, sessionID, at); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkUpdateSessionLastActivity_SameTime(b *testing.B) {
	mr, err := miniredis.Run()
	if err != nil {
		b.Fatal(err)
	}
	defer mr.Close()

	rs := &redisStore{
		cli:                  redisv9.NewClient(&redisv9.Options{Addr: mr.Addr()}),
		sessionPrefix:        "session:",
		expiryIndexKey:       "session:expiry",
		lastActivityIndexKey: "session:last_activity",
	}

	ctx := context.Background()
	sessionID := "benchmark-session-same"

	// Setup session
	sb := &types.SandboxInfo{
		SessionID: sessionID,
		ExpiresAt: time.Now().Add(1 * time.Hour),
		Status:    "running",
	}
	if err := rs.StoreSandbox(ctx, sb); err != nil {
		b.Fatal(err)
	}

	fixedTime := time.Now()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		// Use fixed time to simulate no-change
		if err := rs.UpdateSessionLastActivity(ctx, sessionID, fixedTime); err != nil {
			b.Fatal(err)
		}
	}
}
