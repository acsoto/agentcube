// Local single-node experiment. Run beside AgentCube Router on the same host.
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/google/uuid"
	"github.com/volcano-sh/agentcube/pkg/common/types"
	"github.com/volcano-sh/agentcube/pkg/store"
)

type adapter struct {
	api, apiKey, template, publicKey string
	proxy                            *url.URL
	client                           *http.Client
	store                            store.Store
	mu                               sync.Mutex
	active                           map[string]*http.Server
}

func (a *adapter) call(ctx context.Context, method, path string, body any, result any) (int, error) {
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			return 0, err
		}
	}
	req, err := http.NewRequestWithContext(ctx, method, a.api+path, &buf)
	if err != nil {
		return 0, err
	}
	req.Header.Set("X-API-Key", a.apiKey)
	req.Header.Set("Content-Type", "application/json")
	resp, err := a.client.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	if resp.StatusCode/100 != 2 {
		return resp.StatusCode, fmt.Errorf("conductor %s %s: HTTP %d", method, path, resp.StatusCode)
	}
	if result != nil {
		err = json.NewDecoder(io.LimitReader(resp.Body, 1<<20)).Decode(result)
	}
	return resp.StatusCode, err
}

func (a *adapter) remove(id string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	status, err := a.call(ctx, "DELETE", "/sandboxes/"+id, nil, nil)
	if err != nil && status != 404 {
		return err
	}
	for status != http.StatusNotFound {
		status, err = a.call(ctx, "GET", "/sandboxes/"+id, nil, nil)
		if status == http.StatusNotFound {
			break
		}
		if err != nil {
			return err
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(250 * time.Millisecond):
		}
	}
	if s := a.active[id]; s != nil {
		s.Close()
	}
	if err := a.store.DeleteSandboxBySessionID(ctx, id); err != nil {
		return err
	}
	delete(a.active, id)
	return nil
}

func (a *adapter) create(w http.ResponseWriter, r *http.Request) {
	var q types.CreateSandboxRequest
	if json.NewDecoder(http.MaxBytesReader(w, r.Body, 4096)).Decode(&q) != nil {
		http.Error(w, "invalid request", 400)
		return
	}
	if q.Name != "kuasar-picod" || q.Namespace != "kuasar-lab" {
		http.Error(w, "unknown lab template", 404)
		return
	}
	q.Kind = types.CodeInterpreterKind
	if err := q.Validate(); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	a.mu.Lock()
	defer a.mu.Unlock()
	if len(a.active) > 0 {
		http.Error(w, "single sandbox lab is busy", 409)
		return
	}
	ttl := q.RequestedTTL()
	if ttl <= 0 || ttl > 30*time.Minute {
		ttl = 30 * time.Minute
	}
	createdAt := time.Now()
	id := uuid.NewString()
	identity, _ := json.Marshal(map[string]string{"id": id})
	body := map[string]any{
		"templateID": a.template,
		"timeout":    int(ttl.Seconds()),
		"envVars":    map[string]string{"PICOD_AUTH_PUBLIC_KEY": a.publicKey},
		"metadata": map[string]string{
			"kuasar-sandbox.identity": string(identity),
			"kuasar-sandbox.launch":   `{"exec":"/usr/local/bin/picod","args":["-workspace","/workspace"]}`,
		},
	}
	var created struct {
		ID           string `json:"sandboxID"`
		ForwardToken string `json:"forwardAccessToken"`
	}
	log.Printf("create %s", id)
	a.active[id] = nil
	ready := false
	defer func() {
		if !ready {
			if err := a.remove(id); err != nil {
				log.Printf("cleanup %s: %v", id, err)
			}
		}
	}()
	if _, err := a.call(r.Context(), "POST", "/sandboxes", body, &created); err != nil {
		log.Print(err)
		http.Error(w, "conductor create failed", 502)
		return
	}
	if created.ID != id || created.ForwardToken == "" {
		http.Error(w, "unexpected conductor response", 502)
		return
	}
	// Each loopback port belongs to exactly one sandbox; clients cannot choose its upstream.
	p := &httputil.ReverseProxy{Rewrite: func(pr *httputil.ProxyRequest) {
		pr.SetURL(a.proxy)
		pr.Out.Host = a.proxy.Host
		pr.Out.Header.Del("E2b-Sandbox-Service")
		pr.Out.Header.Set("E2b-Sandbox-Id", id)
		pr.Out.Header.Set("E2b-Sandbox-Port", "8080")
		pr.Out.Header.Set("X-Access-Token", created.ForwardToken)
	}}
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		http.Error(w, "cannot bind lab endpoint", 500)
		return
	}
	srv := &http.Server{Handler: p, ReadHeaderTimeout: 5 * time.Second}
	a.active[id] = srv
	go func() {
		if err := srv.Serve(listener); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Print(err)
		}
	}()
	endpoint := listener.Addr().String()
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Minute)
	defer cancel()
	for {
		var sandbox struct{ State string }
		_, err := a.call(ctx, "GET", "/sandboxes/"+id, nil, &sandbox)
		if err != nil || sandbox.State == "dead" || sandbox.State == "deleting" {
			log.Printf("sandbox %s state=%s err=%v", id, sandbox.State, err)
			http.Error(w, "sandbox startup failed", 502)
			return
		}
		if sandbox.State == "running" {
			req, _ := http.NewRequestWithContext(ctx, "GET", "http://"+endpoint+"/health", nil)
			resp, e := a.client.Do(req)
			if e == nil {
				resp.Body.Close()
				if resp.StatusCode == 200 {
					break
				}
			}
		}
		select {
		case <-ctx.Done():
			http.Error(w, "PicoD readiness timed out", 504)
			return
		case <-time.After(time.Second):
		}
	}
	info := &types.SandboxInfo{
		SessionID: id, SandboxID: id, Kind: types.SandboxKind,
		Name: q.Name, SandboxNamespace: q.Namespace,
		CreatedAt: createdAt, ExpiresAt: createdAt.Add(ttl), Status: "ready",
		EntryPoints: []types.SandboxEntryPoint{{Path: "/", Protocol: "http", Endpoint: endpoint}},
	}
	if err := a.store.StoreSandbox(ctx, info); err != nil {
		http.Error(w, "cannot publish session", 500)
		return
	}
	ready = true
	time.AfterFunc(time.Until(info.ExpiresAt), func() {
		a.mu.Lock()
		defer a.mu.Unlock()
		if _, exists := a.active[id]; exists {
			if err := a.remove(id); err != nil {
				log.Printf("expire %s: %v", id, err)
			}
		}
	})
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(types.CreateSandboxResponse{SessionID: id, SandboxID: id, SandboxName: q.Name, Kind: info.Kind, EntryPoints: info.EntryPoints})
}

func main() {
	for _, key := range []string{"CONDUCTOR_URL", "NODE_PROXY_URL", "KUASAR_API_KEY", "KUASAR_TEMPLATE", "PICOD_PUBLIC_KEY_FILE"} {
		if os.Getenv(key) == "" {
			log.Fatalf("missing %s", key)
		}
	}
	pub, err := os.ReadFile(os.Getenv("PICOD_PUBLIC_KEY_FILE"))
	if err != nil {
		log.Fatal(err)
	}
	proxy, err := url.ParseRequestURI(os.Getenv("NODE_PROXY_URL"))
	if err != nil {
		log.Fatal(err)
	}
	a := &adapter{
		api:    strings.TrimRight(os.Getenv("CONDUCTOR_URL"), "/"),
		apiKey: os.Getenv("KUASAR_API_KEY"), template: os.Getenv("KUASAR_TEMPLATE"),
		proxy: proxy, publicKey: string(pub),
		client: &http.Client{Timeout: 10 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }},
		store:  store.Storage(), active: make(map[string]*http.Server),
	}
	mux := http.NewServeMux()
	mux.HandleFunc("POST /v1/code-interpreter", a.create)
	mux.HandleFunc("DELETE /v1/code-interpreter/sessions/{id}", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		a.mu.Lock()
		defer a.mu.Unlock()
		if _, ok := a.active[id]; !ok {
			http.NotFound(w, r)
			return
		}
		if err := a.remove(id); err != nil {
			http.Error(w, "cleanup failed", 502)
			return
		}
		w.WriteHeader(http.StatusNoContent)
	})
	srv := &http.Server{Addr: "127.0.0.1:18090", Handler: mux, ReadHeaderTimeout: 5 * time.Second}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	go func() { <-ctx.Done(); srv.Close() }()
	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
	a.mu.Lock()
	defer a.mu.Unlock()
	for id := range a.active {
		if err := a.remove(id); err != nil {
			log.Print(err)
		}
	}
}
