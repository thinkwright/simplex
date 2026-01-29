# Simplex Specification Makefile

VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
BINARY := simplex-lint
BUILD_DIR := ./build
LINT_DIR := ./lint
GO_MODULE := github.com/brannn/simplex/lint

.PHONY: all build test lint clean release gh-pages help

all: build test lint

## build: Compile the linter binary
build:
	@echo "Building $(BINARY) $(VERSION)..."
	@mkdir -p $(BUILD_DIR)
	cd $(LINT_DIR) && go build -ldflags "-X main.version=$(VERSION)" -o ../$(BUILD_DIR)/$(BINARY) ./cmd/simplex-lint

## test: Run all Go tests
test:
	@echo "Running tests..."
	cd $(LINT_DIR) && go test -v ./...

## lint: Run static analysis on linter code
lint:
	@echo "Linting Go code..."
	cd $(LINT_DIR) && go vet ./...
	@if command -v golangci-lint >/dev/null 2>&1; then \
		cd $(LINT_DIR) && golangci-lint run; \
	else \
		echo "golangci-lint not installed, skipping"; \
	fi

## clean: Remove build artifacts
clean:
	@echo "Cleaning..."
	rm -rf $(BUILD_DIR)

## release: Create a tagged release (usage: make release VERSION=0.5.0)
release: test lint build
	@if [ "$(VERSION)" = "dev" ] || [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION must be specified (e.g., make release VERSION=0.5.0)"; \
		exit 1; \
	fi
	@echo "Creating release v$(VERSION)..."
	@if git diff --quiet && git diff --cached --quiet; then \
		git tag -a "v$(VERSION)" -m "Release v$(VERSION)"; \
		echo "Tagged v$(VERSION). Push with: git push origin v$(VERSION)"; \
	else \
		echo "Error: Working directory not clean. Commit changes first."; \
		exit 1; \
	fi

## gh-pages: Deploy to GitHub Pages (switches branch, builds, commits)
gh-pages:
	@echo "Deploying to gh-pages..."
	@CURRENT_BRANCH=$$(git branch --show-current); \
	git stash push -m "gh-pages deploy stash"; \
	git checkout gh-pages && \
	git pull origin gh-pages && \
	echo "gh-pages branch ready. Make changes and commit manually." && \
	echo "Return to previous branch with: git checkout $$CURRENT_BRANCH && git stash pop"

## help: Show this help
help:
	@echo "Simplex Makefile targets:"
	@echo ""
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'
