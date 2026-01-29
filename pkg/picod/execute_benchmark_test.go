package picod

import (
	"fmt"
	"os"
	"testing"
)

func BenchmarkEnvAllocation(b *testing.B) {
	// Setup
	reqEnv := make(map[string]string)
	for i := 0; i < 100; i++ {
		reqEnv[fmt.Sprintf("VAR_%d", i)] = fmt.Sprintf("VALUE_%d", i)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		environ := os.Environ()
		currentEnv := make([]string, 0, len(environ)+len(reqEnv))
		currentEnv = append(currentEnv, environ...)
		for k, v := range reqEnv {
			currentEnv = append(currentEnv, fmt.Sprintf("%s=%s", k, v))
		}
		// Prevent compiler optimization
		if len(currentEnv) == 0 {
			b.Fatal("empty env")
		}
	}
}
