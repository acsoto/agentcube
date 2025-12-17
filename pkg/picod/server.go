package picod

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

// Config defines server configuration
type Config struct {
	Port int `json:"port"`
	// BootstrapKey []byte `json:"bootstrap_key"` // Removed
	Workspace string `json:"workspace"`
}

// Hardcoded authentication token
const AuthToken = "agentcube-secret-token" // This token is for direct SDK-PicoD communication only

// Server defines the PicoD HTTP server
type Server struct {
	engine *gin.Engine
	config Config
	// authManager  *AuthManager // Removed
	startTime    time.Time
	workspaceDir string
}

// NewServer creates a new PicoD server instance
func NewServer(config Config) *Server {
	s := &Server{
		config: config,
		startTime: time.Now(),
		// authManager: NewAuthManager(), // Removed
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

	// Removed: Bootstrap key loading
	// if len(config.BootstrapKey) == 0 {
	// 	log.Fatal("Bootstrap key is missing. Please ensure the bootstrap public key file is correctly mounted or provided.")
	// }
	// if err := s.authManager.LoadBootstrapKey(config.BootstrapKey); err != nil {
	// 	log.Fatalf("Failed to load bootstrap key: %v", err)
	// }
	// log.Printf("Bootstrap key loaded successfully")

	// Removed: Loading existing public key
	// if err := s.authManager.LoadPublicKey(); err != nil {
	// 	log.Printf("Server not initialized: %v", err)
	// }

	// API route group (Authenticated)
	api := engine.Group("/api")
	api.Use(s.AuthMiddleware()) // Use the new AuthMiddleware
	{
		api.POST("/execute", s.ExecuteHandler)
		api.POST("/files", s.UploadFileHandler)
		api.GET("/files", s.ListFilesHandler)
		api.GET("/files/*path", s.DownloadFileHandler)
	}

	// Removed: Initialization endpoint
	// engine.POST("/init", s.authManager.InitHandler)

	// Health check (no authentication required)
	engine.GET("/health", s.HealthCheckHandler)

	s.engine = engine
	return s
}

// Run starts the server
func (s *Server) Run() error {
	addr := fmt.Sprintf(":%d", s.config.Port)
	log.Printf("PicoD server starting on %s", addr)

	server := &http.Server{
		Addr:              addr,
		Handler:           s.engine,
		ReadHeaderTimeout: 10 * time.Second, // Prevent Slowloris attacks
	}

	return server.ListenAndServe()
}

// HealthCheckHandler handles health check requests
func (s *Server) HealthCheckHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status": "ok",
		"service": "PicoD",
		"version": "0.0.1",
		"uptime": time.Since(s.startTime).String(),
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

		// Enforce maximum body size to prevent memory exhaustion (if needed, this was from original auth.go)
		// Assuming MaxBodySize constant is defined elsewhere or will be moved/removed as well
		// For now, removing this as it was tied to the old AuthManager
		// c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, MaxBodySize)

		c.Next()
	}
}