package picod

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"log"
	"math/big"
	"net"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

// Config defines server configuration
type Config struct {
	Port        int    `json:"port"`
	Workspace   string `json:"workspace"`
	TLSCertFile string `json:"tls_cert_file"`
	TLSKeyFile  string `json:"tls_key_file"`
}

// Hardcoded authentication token
const AuthToken = "agentcube-secret-token" // This token is for direct SDK-PicoD communication only

// Server defines the PicoD HTTP server
type Server struct {
	engine       *gin.Engine
	config       Config
	startTime    time.Time
	workspaceDir string
}

// NewServer creates a new PicoD server instance
func NewServer(config Config) *Server {
	s := &Server{
		config:    config,
		startTime: time.Now(),
	}

	// Initialize workspace directory
	if config.Workspace != "" {
		s.setWorkspace(config.Workspace)
	} else {
		// Default to current working directory if not specified
		cwd, err := os.Getwd()
		if err != nil {
			log.Fatalf("Failed to get current working directory: %v", err)
		}
		s.setWorkspace(cwd)
	}

	// Disable Gin debug output in production mode
	gin.SetMode(gin.ReleaseMode)

	engine := gin.New()

	// Global middleware
	engine.Use(gin.Logger())   // Request logging
	engine.Use(gin.Recovery()) // Crash recovery

	// API route group (Authenticated)
	api := engine.Group("/api")
	api.Use(s.AuthMiddleware()) // Use the new AuthMiddleware
	{
		api.POST("/execute", s.ExecuteHandler)
		api.POST("/files", s.UploadFileHandler)
		api.GET("/files", s.ListFilesHandler)
		api.GET("/files/*path", s.DownloadFileHandler)
	}

	// Health check (no authentication required)
	engine.GET("/health", s.HealthCheckHandler)

	s.engine = engine
	return s
}

// Run starts the server with TLS
func (s *Server) Run() error {
	addr := fmt.Sprintf(":%d", s.config.Port)
	log.Printf("PicoD server starting on %s (HTTPS)", addr)

	server := &http.Server{
		Addr:              addr,
		Handler:           s.engine,
		ReadHeaderTimeout: 10 * time.Second, // Prevent Slowloris attacks
	}

	// Determine TLS configuration
	if s.config.TLSCertFile != "" && s.config.TLSKeyFile != "" {
		// Use provided certificate
		log.Printf("Using provided TLS certificate: %s", s.config.TLSCertFile)
		return server.ListenAndServeTLS(s.config.TLSCertFile, s.config.TLSKeyFile)
	}

	// Generate self-signed certificate
	log.Printf("No TLS certificate provided. Generating self-signed certificate...")
	tlsConfig, err := generateSelfSignedCert()
	if err != nil {
		return fmt.Errorf("failed to generate self-signed certificate: %v", err)
	}
	server.TLSConfig = tlsConfig

	// ListenAndServeTLS with empty filenames uses the server.TLSConfig
	// However, server.ListenAndServeTLS ignores TLSConfig.Certificates and tries to load files if filenames are provided.
	// So we use server.Serve(listener) instead.

	ln, err := net.Listen("tcp", addr)
	if err != nil {
		return err
	}

	tlsListener := tls.NewListener(ln, tlsConfig)
	return server.Serve(tlsListener)
}

// generateSelfSignedCert generates a self-signed TLS certificate
func generateSelfSignedCert() (*tls.Config, error) {
	// Generate private key
	priv, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return nil, err
	}

	// Create template
	notBefore := time.Now()
	notAfter := notBefore.Add(365 * 24 * time.Hour) // Valid for 1 year

	serialNumberLimit := new(big.Int).Lsh(big.NewInt(1), 128)
	serialNumber, err := rand.Int(rand.Reader, serialNumberLimit)
	if err != nil {
		return nil, err
	}

	template := x509.Certificate{
		SerialNumber: serialNumber,
		Subject: pkix.Name{
			Organization: []string{"AgentCube PicoD"},
		},
		NotBefore: notBefore,
		NotAfter:  notAfter,

		KeyUsage:              x509.KeyUsageKeyEncipherment | x509.KeyUsageDigitalSignature,
		ExtKeyUsage:           []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
		BasicConstraintsValid: true,
		IPAddresses:           []net.IP{net.ParseIP("127.0.0.1"), net.ParseIP("0.0.0.0")},
		DNSNames:              []string{"localhost"},
	}

	// Create certificate
	derBytes, err := x509.CreateCertificate(rand.Reader, &template, &template, &priv.PublicKey, priv)
	if err != nil {
		return nil, err
	}

	// Encode to PEM
	certPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: derBytes})
	keyPEM := pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(priv)})

	// Load X509 key pair
	cert, err := tls.X509KeyPair(certPEM, keyPEM)
	if err != nil {
		return nil, err
	}

	return &tls.Config{
		Certificates: []tls.Certificate{cert},
	}, nil
}

// HealthCheckHandler handles health check requests
func (s *Server) HealthCheckHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":  "ok",
		"service": "PicoD",
		"version": "0.0.1",
		"uptime":  time.Since(s.startTime).String(),
	})
}

// AuthMiddleware creates authentication middleware with hardcoded token verification
func (s *Server) AuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error":  "Missing Authorization header",
				"code":   http.StatusUnauthorized,
				"detail": "Request requires Bearer token authentication",
			})
			c.Abort()
			return
		}

		parts := strings.Split(authHeader, " ")
		if len(parts) != 2 || parts[0] != "Bearer" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error":  "Invalid Authorization header format",
				"code":   http.StatusUnauthorized,
				"detail": "Use Bearer <token>",
			})
			c.Abort()
			return
		}

		token := parts[1]

		if token != AuthToken {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error":  "Invalid token",
				"code":   http.StatusUnauthorized,
				"detail": "Provided token does not match the hardcoded authentication token",
			})
			c.Abort()
			return
		}

		c.Next()
	}
}
