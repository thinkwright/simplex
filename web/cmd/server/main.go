package main

import (
	"embed"
	"encoding/json"
	"flag"
	"io"
	"io/fs"
	"log"
	"net/http"
	"os"
	"strings"

	"github.com/brannn/simplex/lint"
)

//go:embed all:static
var staticFiles embed.FS

func main() {
	port := flag.String("port", getEnv("PORT", "8080"), "Port to listen on")
	apiURL := flag.String("api-url", getEnv("API_URL", "https://api.together.xyz"), "Together AI API base URL")
	flag.Parse()

	mux := http.NewServeMux()

	// Health check endpoint
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	})

	// Lint API endpoint (must be registered before the /api/ catch-all proxy)
	linter := lint.DefaultLinter()
	mux.HandleFunc("/api/lint", lintHandler(linter))

	// Proxy API requests to the LLM server (optional, for planner functionality)
	if *apiURL != "" {
		mux.HandleFunc("/api/", apiProxyHandler(*apiURL))
	}

	// Serve static files with SPA routing
	staticFS, err := fs.Sub(staticFiles, "static")
	if err != nil {
		log.Fatal(err)
	}
	mux.Handle("/", spaHandler(http.FS(staticFS)))

	log.Printf("Simplex Website listening on :%s", *port)
	if *apiURL != "" {
		log.Printf("API proxy: /api/* → %s/v1/*", *apiURL)
	}
	if os.Getenv("TOGETHER_API_KEY") == "" {
		log.Printf("Warning: TOGETHER_API_KEY not set — planner AI features will not work")
	}

	// Wrap with www redirect middleware
	handler := wwwRedirect(mux)

	if err := http.ListenAndServe(":"+*port, handler); err != nil {
		log.Fatal(err)
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

// spaHandler serves static files with SPA routing
// - / serves index.html (landing page)
// - /planner, /spec, /examples, /quickstart serve respective HTML files
// - static assets (css, js) served directly with cache headers
func spaHandler(fsys http.FileSystem) http.Handler {
	fileServer := http.FileServer(fsys)

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		path := r.URL.Path

		// Root serves landing page
		if path == "/" {
			serveFile(w, r, fsys, "/index.html")
			return
		}

		// Routes without extensions serve HTML files
		if !strings.Contains(path, ".") {
			// Try the exact path
			htmlPath := path + ".html"
			if fileExists(fsys, htmlPath) {
				serveFile(w, r, fsys, htmlPath)
				return
			}
		}

		// Try to open the file directly
		f, err := fsys.Open(path)
		if err != nil {
			// File doesn't exist, serve index.html for SPA routing
			serveFile(w, r, fsys, "/index.html")
			return
		}
		f.Close()

		// Set cache headers for static assets
		if strings.HasSuffix(path, ".css") || strings.HasSuffix(path, ".js") {
			w.Header().Set("Cache-Control", "public, max-age=3600")
		} else if strings.HasSuffix(path, ".html") {
			w.Header().Set("Cache-Control", "no-cache")
		}

		fileServer.ServeHTTP(w, r)
	})
}

// serveFile serves a specific file from the filesystem with proper headers
func serveFile(w http.ResponseWriter, r *http.Request, fsys http.FileSystem, name string) {
	f, err := fsys.Open(name)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	defer f.Close()

	stat, err := f.Stat()
	if err != nil {
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}

	// Set content type based on file extension
	if strings.HasSuffix(name, ".html") {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Header().Set("Cache-Control", "no-cache")
	} else if strings.HasSuffix(name, ".css") {
		w.Header().Set("Content-Type", "text/css; charset=utf-8")
		w.Header().Set("Cache-Control", "public, max-age=3600")
	} else if strings.HasSuffix(name, ".js") {
		w.Header().Set("Content-Type", "application/javascript; charset=utf-8")
		w.Header().Set("Cache-Control", "public, max-age=3600")
	} else if strings.HasSuffix(name, ".svg") {
		w.Header().Set("Content-Type", "image/svg+xml; charset=utf-8")
		w.Header().Set("Cache-Control", "public, max-age=3600")
	}

	// Serve the file content
	http.ServeContent(w, r, name, stat.ModTime(), f.(io.ReadSeeker))
}

// fileExists checks if a file exists in the filesystem
func fileExists(fsys http.FileSystem, name string) bool {
	f, err := fsys.Open(name)
	if err != nil {
		return false
	}
	f.Close()
	return true
}

// wwwRedirect redirects www.simplex-spec.org to simplex-spec.org
func wwwRedirect(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.HasPrefix(r.Host, "www.") {
			target := "https://" + strings.TrimPrefix(r.Host, "www.") + r.URL.RequestURI()
			http.Redirect(w, r, target, http.StatusMovedPermanently)
			return
		}
		next.ServeHTTP(w, r)
	})
}

// lintHandler handles POST /api/lint requests using the canonical Go linter.
func lintHandler(linter *lint.Linter) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		body, err := io.ReadAll(io.LimitReader(r.Body, 1<<20)) // 1MB limit
		if err != nil {
			http.Error(w, "Failed to read request body", http.StatusBadRequest)
			return
		}

		var req struct {
			Spec string `json:"spec"`
		}
		if err := json.Unmarshal(body, &req); err != nil {
			http.Error(w, "Invalid JSON", http.StatusBadRequest)
			return
		}
		if req.Spec == "" {
			http.Error(w, `{"error":"spec field is required"}`, http.StatusBadRequest)
			return
		}

		result := linter.Lint("input", req.Spec)

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(result)
	}
}

// apiProxyHandler forwards requests to the LLM API server (for planner functionality)
func apiProxyHandler(baseURL string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// Build target URL: map /api/* to /v1/*
		apiPath := strings.TrimPrefix(r.URL.Path, "/api")
		targetURL := strings.TrimSuffix(baseURL, "/") + "/v1" + apiPath
		if r.URL.RawQuery != "" {
			targetURL += "?" + r.URL.RawQuery
		}

		proxyReq, err := http.NewRequest(r.Method, targetURL, r.Body)
		if err != nil {
			http.Error(w, "Failed to create proxy request", http.StatusInternalServerError)
			return
		}

		// Copy headers
		for key, values := range r.Header {
			for _, value := range values {
				proxyReq.Header.Add(key, value)
			}
		}

		// Forward auth header for Together AI
		if apiKey := os.Getenv("TOGETHER_API_KEY"); apiKey != "" {
			proxyReq.Header.Set("Authorization", "Bearer "+apiKey)
		}

		// Make request
		client := &http.Client{}
		resp, err := client.Do(proxyReq)
		if err != nil {
			http.Error(w, "Failed to reach API server", http.StatusBadGateway)
			return
		}
		defer resp.Body.Close()

		// Copy response headers
		for key, values := range resp.Header {
			for _, value := range values {
				w.Header().Add(key, value)
			}
		}

		// Copy status and body
		w.WriteHeader(resp.StatusCode)
		buf := make([]byte, 32*1024)
		for {
			n, err := resp.Body.Read(buf)
			if n > 0 {
				w.Write(buf[:n])
			}
			if err != nil {
				break
			}
		}
	}
}