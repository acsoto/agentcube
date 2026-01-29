package picod

import (
	"os"
	"testing"
	"time"
)

// mockDirEntry implements os.DirEntry for benchmarking
type mockDirEntry struct {
	name string
}

func (m mockDirEntry) Name() string { return m.name }
func (m mockDirEntry) IsDir() bool { return false }
func (m mockDirEntry) Type() os.FileMode { return 0 }
func (m mockDirEntry) Info() (os.FileInfo, error) {
	return mockFileInfo{name: m.name}, nil
}

type mockFileInfo struct {
	name string
}

func (m mockFileInfo) Name() string { return m.name }
func (m mockFileInfo) Size() int64 { return 1024 }
func (m mockFileInfo) Mode() os.FileMode { return 0644 }
func (m mockFileInfo) ModTime() time.Time { return time.Now() }
func (m mockFileInfo) IsDir() bool { return false }
func (m mockFileInfo) Sys() any { return nil }

func BenchmarkLoop_Current(b *testing.B) {
	numEntries := 10000
	entries := make([]os.DirEntry, numEntries)
	for i := 0; i < numEntries; i++ {
		entries[i] = mockDirEntry{name: "test"}
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		var files []FileEntry // Current implementation: nil slice
		for _, entry := range entries {
			info, _ := entry.Info()
			files = append(files, FileEntry{
				Name:     entry.Name(),
				Size:     info.Size(),
				Modified: info.ModTime(),
				Mode:     info.Mode().String(),
				IsDir:    entry.IsDir(),
			})
		}
		_ = files // prevent compiler optimization
	}
}

func BenchmarkLoop_Optimized(b *testing.B) {
	numEntries := 10000
	entries := make([]os.DirEntry, numEntries)
	for i := 0; i < numEntries; i++ {
		entries[i] = mockDirEntry{name: "test"}
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		files := make([]FileEntry, 0, len(entries)) // Optimized: pre-allocated
		for _, entry := range entries {
			info, _ := entry.Info()
			files = append(files, FileEntry{
				Name:     entry.Name(),
				Size:     info.Size(),
				Modified: info.ModTime(),
				Mode:     info.Mode().String(),
				IsDir:    entry.IsDir(),
			})
		}
		_ = files
	}
}
