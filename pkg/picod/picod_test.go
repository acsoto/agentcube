package picod

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestPicoD_EndToEnd(t *testing.T) {
	// 1. Setup Server Environment
	tmpDir, err := os.MkdirTemp("", "picod_test")
	require.NoError(t, err)
	defer os.RemoveAll(tmpDir)

	originalWd, err := os.Getwd()
	require.NoError(t, err)
	err = os.Chdir(tmpDir)
	require.NoError(t, err)
	defer func() { require.NoError(t, os.Chdir(originalWd)) }()

	config := Config{
		Port:         0, // Test server handles port
		Workspace:    tmpDir, // Set workspace to temp dir
	}

	server := NewServer(config)
	ts := httptest.NewServer(server.engine)
	defer ts.Close()

	client := ts.Client()

	t.Run("Health Check", func(t *testing.T) {
		resp, err := client.Get(ts.URL + "/health")
		require.NoError(t, err)
		assert.Equal(t, http.StatusOK, resp.StatusCode)
	})

	t.Run("Unauthenticated Access", func(t *testing.T) {
		// Execute without auth
		execReq := ExecuteRequest{Command: []string{"echo", "hello"}}
		body, _ := json.Marshal(execReq)
		req, _ := http.NewRequest("POST", ts.URL+"/api/execute", bytes.NewBuffer(body))
		resp, err := client.Do(req)
		require.NoError(t, err)
		assert.Equal(t, http.StatusUnauthorized, resp.StatusCode) // Expecting Unauthorized
	})

	t.Run("Command Execution", func(t *testing.T) {
		// Helper to make authenticated execute requests
		doExec := func(cmd []string, env map[string]string, timeout string, expectStatus int) ExecuteResponse {
			reqBody := ExecuteRequest{
				Command: cmd,
				Env:     env,
				Timeout: timeout,
			}
			bodyBytes, _ := json.Marshal(reqBody)

			req, _ := http.NewRequest("POST", ts.URL+"/api/execute", bytes.NewBuffer(bodyBytes))
			req.Header.Set("Authorization", "Bearer "+AuthToken) // Use hardcoded token
			req.Header.Set("Content-Type", "application/json")

			resp, err := client.Do(req)
			require.NoError(t, err)
			assert.Equal(t, expectStatus, resp.StatusCode)

			var execResp ExecuteResponse
			if expectStatus == http.StatusOK {
				err = json.NewDecoder(resp.Body).Decode(&execResp)
				require.NoError(t, err)
			}
			return execResp
		}

		// 1. Basic Execution
		resp := doExec([]string{"echo", "hello"}, nil, "", http.StatusOK)
		assert.Equal(t, "hello\n", resp.Stdout)
		assert.Equal(t, 0, resp.ExitCode)
		assert.False(t, resp.StartTime.IsZero())
		assert.False(t, resp.EndTime.IsZero())

		// 2. Environment Variables
		resp = doExec([]string{"sh", "-c", "echo $TEST_VAR"}, map[string]string{"TEST_VAR": "picod_env"}, "", http.StatusOK)
		assert.Equal(t, "picod_env\n", resp.Stdout)

		// 3. Stderr and Exit Code
		resp = doExec([]string{"sh", "-c", "echo error_msg >&2; exit 1"}, nil, "", http.StatusOK)
		assert.Equal(t, "error_msg\n", resp.Stderr)
		assert.Equal(t, 1, resp.ExitCode)

		// 4. Timeout
		resp = doExec([]string{"sleep", "2"}, nil, "0.5s", http.StatusOK)
		assert.Equal(t, 124, resp.ExitCode)
		assert.Contains(t, resp.Stderr, "Command timed out")

		// 5. Working Directory Escape (Should Fail)
		doExec([]string{"ls"}, nil, "", http.StatusBadRequest)
	})

	t.Run("File Operations", func(t *testing.T) {
		// Helper to create auth headers
		getAuthHeaders := func() http.Header {
			h := make(http.Header)
			h.Set("Authorization", "Bearer "+AuthToken) // Use hardcoded token
			return h
		}

		// 1. JSON Upload
		content := "hello file"
		contentB64 := base64.StdEncoding.EncodeToString([]byte(content))
		uploadReq := UploadFileRequest{
			Path:    "test.txt",
			Content: contentB64,
			Mode:    "0644",
		}
		body, _ := json.Marshal(uploadReq)

		req, _ := http.NewRequest("POST", ts.URL+"/api/files", bytes.NewBuffer(body))
		req.Header = getAuthHeaders()
		req.Header.Set("Content-Type", "application/json")
		resp, err := client.Do(req)
		require.NoError(t, err)
		assert.Equal(t, http.StatusOK, resp.StatusCode)

		// Verify on disk
		fileContent, err := os.ReadFile("test.txt")
		require.NoError(t, err)
		assert.Equal(t, content, string(fileContent))

		// 2. Download File
		req, _ = http.NewRequest("GET", ts.URL+"/api/files/test.txt", nil)
		req.Header = getAuthHeaders()
		resp, err = client.Do(req)
		require.NoError(t, err)
		assert.Equal(t, http.StatusOK, resp.StatusCode)
		downloaded, _ := io.ReadAll(resp.Body)
		assert.Equal(t, content, string(downloaded))

		// 3. Download Directory (Should Fail)
		err = os.Mkdir("testdir", 0755)
		require.NoError(t, err)
		req, _ = http.NewRequest("GET", ts.URL+"/api/files/testdir", nil)
		req.Header = getAuthHeaders()
		resp, err = client.Do(req)
		require.NoError(t, err)
		assert.Equal(t, http.StatusBadRequest, resp.StatusCode)

		// 4. Multipart Upload
		bodyBuf := &bytes.Buffer{}
		writer := multipart.NewWriter(bodyBuf)
		part, _ := writer.CreateFormFile("file", "multipart.txt")
		_, err = part.Write([]byte("multipart content"))
		require.NoError(t, err)
		err = writer.WriteField("path", "multipart.txt")
		require.NoError(t, err)
		writer.Close()

		req, _ = http.NewRequest("POST", ts.URL+"/api/files", bodyBuf)
		req.Header.Set("Authorization", "Bearer "+AuthToken) // Use hardcoded token
		req.Header.Set("Content-Type", writer.FormDataContentType())
		resp, err = client.Do(req)
		require.NoError(t, err)
		assert.Equal(t, http.StatusOK, resp.StatusCode)

		// Verify multipart file
		fileContent, err = os.ReadFile("multipart.txt")
		require.NoError(t, err)
		assert.Equal(t, "multipart content", string(fileContent))

		// 5. List Files
		req, _ = http.NewRequest("GET", ts.URL+"/api/files?path=.", nil)
		req.Header = getAuthHeaders()
		resp, err = client.Do(req)
		require.NoError(t, err)
		assert.Equal(t, http.StatusOK, resp.StatusCode)

		var listResp ListFilesResponse
		err = json.NewDecoder(resp.Body).Decode(&listResp)
		require.NoError(t, err)
		assert.GreaterOrEqual(t, len(listResp.Files), 2)
		found := false
		for _, f := range listResp.Files {
			if f.Name == "test.txt" {
				found = true
				assert.Equal(t, int64(10), f.Size)
				break
			}
		}
		assert.True(t, found, "test.txt should be found in listing")

		// 6. Jail Escape Attempt (Should Fail)
		escapeReq := UploadFileRequest{
			Path:    "../outside.txt",
			Content: contentB64,
		}
		escapeBody, _ := json.Marshal(escapeReq)
		req, _ = http.NewRequest("POST", ts.URL+"/api/files", bytes.NewBuffer(escapeBody))
		req.Header = getAuthHeaders()
		req.Header.Set("Content-Type", "application/json")
		resp, err = client.Do(req)
		require.NoError(t, err)
		assert.Equal(t, http.StatusBadRequest, resp.StatusCode)

		absEscapeReq := UploadFileRequest{
			Path:    "/etc/passwd",
			Content: contentB64,
		}
		absEscapeBody, _ := json.Marshal(absEscapeReq)
		req, _ = http.NewRequest("POST", ts.URL+"/api/files", bytes.NewBuffer(absEscapeBody))
		req.Header = getAuthHeaders()
		req.Header.Set("Content-Type", "application/json")
		resp, err = client.Do(req)
		require.NoError(t, err)
		assert.Equal(t, http.StatusOK, resp.StatusCode)

		_, err = os.Stat(filepath.Join(tmpDir, "etc", "passwd"))
		assert.NoError(t, err, "File should be created inside workspace")
	})

	t.Run("Security Checks", func(t *testing.T) {
		// 1. Invalid Token
		reqBody := ExecuteRequest{Command: []string{"echo", "malicious"}}
		realBody, _ := json.Marshal(reqBody)

		req, _ := http.NewRequest("POST", ts.URL+"/api/execute", bytes.NewBuffer(realBody))
		req.Header.Set("Authorization", "Bearer "+"invalid-token") // Use invalid token
		req.Header.Set("Content-Type", "application/json")

		resp, err := client.Do(req)
		require.NoError(t, err)
		assert.Equal(t, http.StatusUnauthorized, resp.StatusCode)
	})
}

func TestPicoD_DefaultWorkspace(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "picod_default_workspace_test")
	require.NoError(t, err)
	defer os.RemoveAll(tmpDir)

	originalWd, err := os.Getwd()
	require.NoError(t, err)
	err = os.Chdir(tmpDir)
	require.NoError(t, err)
	defer func() { require.NoError(t, os.Chdir(originalWd)) }()

	// Initialize server with empty workspace
	config := Config{
		Port:         0,
		Workspace:    "", // Empty workspace to trigger default behavior
	}

	server := NewServer(config)

	cwd, err := os.Getwd()
	require.NoError(t, err)

	absCwd, err := filepath.Abs(cwd)
	require.NoError(t, err)

	assert.Equal(t, absCwd, server.workspaceDir)
}

func TestPicoD_SetWorkspace(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "picod_setworkspace_test")
	require.NoError(t, err)
	defer os.RemoveAll(tmpDir)

	realDir := filepath.Join(tmpDir, "real")
	err = os.Mkdir(realDir, 0755)
	require.NoError(t, err)

	linkDir := filepath.Join(tmpDir, "link")
	err = os.Symlink(realDir, linkDir)
	require.NoError(t, err)

	server := &Server{}

	resolve := func(p string) string {
		path, err := filepath.EvalSymlinks(p)
		if err != nil {
			return p
		}
		path, err = filepath.Abs(path)
		if err != nil {
			return path
		}
		return path
	}

	absPath, err := filepath.Abs(realDir)
	require.NoError(t, err)
	server.setWorkspace(realDir)
	assert.Equal(t, resolve(absPath), resolve(server.workspaceDir))

	originalWd, err := os.Getwd()
	require.NoError(t, err)
	err = os.Chdir(tmpDir)
	require.NoError(t, err)
	defer func() { require.NoError(t, os.Chdir(originalWd)) }()

	server.setWorkspace("real")
	assert.Equal(t, resolve(absPath), resolve(server.workspaceDir))

	absLinkPath, err := filepath.Abs(linkDir)
	require.NoError(t, err)
	server.setWorkspace(linkDir)
	assert.Equal(t, resolve(absLinkPath), resolve(server.workspaceDir))
}