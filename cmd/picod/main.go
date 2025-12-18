package main

import (
	"flag"
	"log"

	"github.com/volcano-sh/agentcube/pkg/picod"
)

func main() {
	port := flag.Int("port", 8080, "Port for the PicoD server to listen on")
	workspace := flag.String("workspace", "", "Root directory for file operations (default: current working directory)")
	certFile := flag.String("cert-file", "", "Path to TLS certificate file (optional)")
	keyFile := flag.String("key-file", "", "Path to TLS private key file (optional)")
	flag.Parse()

	config := picod.Config{
		Port:        *port,
		Workspace:   *workspace,
		TLSCertFile: *certFile,
		TLSKeyFile:  *keyFile,
	}

	// Create and start server
	server := picod.NewServer(config)

	if err := server.Run(); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
