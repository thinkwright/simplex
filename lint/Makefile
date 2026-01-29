.PHONY: build install test test-cover test-cover-enforce test-cover-internal test-live lint clean fmt vet check deps ci

VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
LDFLAGS := -ldflags "-X main.version=$(VERSION)"

# Coverage requirements:
# - Overall: 90% (CLI entry points with os.Exit are hard to unit test)
# - Internal packages: 98% (all business logic must be thoroughly tested)
MIN_COVERAGE := 90
MIN_INTERNAL_COVERAGE := 98

# Internal packages (business logic - must be 98%+ covered)
INTERNAL_PACKAGES := ./internal/...

# Build binary
build:
	go build $(LDFLAGS) -o bin/simplex-lint ./cmd/simplex-lint

# Install to GOPATH/bin
install:
	go install $(LDFLAGS) ./cmd/simplex-lint

# Run all tests
test:
	go test -v ./...

# Run tests with coverage report
test-cover:
	go test -v -coverprofile=coverage.out -covermode=atomic ./...
	go tool cover -html=coverage.out -o coverage.html
	@echo ""
	@echo "Coverage report generated: coverage.html"
	@go tool cover -func=coverage.out | tail -1

# Run tests and enforce minimum coverage for internal packages
test-cover-internal:
	@echo "Testing internal packages with coverage enforcement (minimum: $(MIN_INTERNAL_COVERAGE)%)..."
	@go test -coverprofile=coverage-internal.out -covermode=atomic $(INTERNAL_PACKAGES) > /dev/null 2>&1 || (go test -v $(INTERNAL_PACKAGES) && exit 1)
	@COVERAGE=$$(go tool cover -func=coverage-internal.out | grep total | awk '{print $$3}' | sed 's/%//'); \
	echo "Internal packages coverage: $$COVERAGE%"; \
	if [ $$(echo "$$COVERAGE < $(MIN_INTERNAL_COVERAGE)" | bc -l) -eq 1 ]; then \
		echo "ERROR: Internal coverage $$COVERAGE% is below minimum required $(MIN_INTERNAL_COVERAGE)%"; \
		echo ""; \
		echo "Uncovered code in internal packages:"; \
		go tool cover -func=coverage-internal.out | grep -v "100.0%" | grep -v "total:"; \
		exit 1; \
	else \
		echo "OK: Internal package coverage meets minimum requirement"; \
	fi

# Run tests and enforce minimum overall coverage
test-cover-enforce:
	@echo "Running tests with coverage enforcement..."
	@echo ""
	@# First check internal packages (must be $(MIN_INTERNAL_COVERAGE)%)
	@$(MAKE) test-cover-internal
	@echo ""
	@# Then check overall (must be $(MIN_COVERAGE)%)
	@echo "Testing overall coverage (minimum: $(MIN_COVERAGE)%)..."
	@go test -coverprofile=coverage.out -covermode=atomic ./... > /dev/null 2>&1 || (go test -v ./... && exit 1)
	@COVERAGE=$$(go tool cover -func=coverage.out | grep total | awk '{print $$3}' | sed 's/%//'); \
	echo "Overall coverage: $$COVERAGE%"; \
	if [ $$(echo "$$COVERAGE < $(MIN_COVERAGE)" | bc -l) -eq 1 ]; then \
		echo "ERROR: Overall coverage $$COVERAGE% is below minimum required $(MIN_COVERAGE)%"; \
		echo ""; \
		echo "Uncovered code:"; \
		go tool cover -func=coverage.out | grep -v "100.0%" | grep -v "total:"; \
		exit 1; \
	else \
		echo "OK: Overall coverage meets minimum requirement"; \
	fi
	@echo ""
	@echo "All coverage requirements met!"

# Show uncovered lines
test-cover-uncovered:
	@go test -coverprofile=coverage.out -covermode=atomic ./... > /dev/null 2>&1
	@echo "Functions with less than 100% coverage:"
	@go tool cover -func=coverage.out | grep -v "100.0%" | grep -v "total:"

# Run live tests (requires API keys)
test-live:
	go test -v -tags=live ./...

# Run linter
lint:
	golangci-lint run

# Format code
fmt:
	go fmt ./...

# Vet code
vet:
	go vet ./...

# Clean build artifacts
clean:
	rm -rf bin/
	rm -f coverage.out coverage-internal.out coverage.html

# Download dependencies
deps:
	go mod download
	go mod tidy

# Run all checks before commit (with coverage enforcement)
check: fmt vet test-cover-enforce lint

# CI target - strict checks
ci: deps fmt vet test-cover-enforce lint build
	@echo ""
	@echo "========================================="
	@echo "All CI checks passed!"
	@echo "========================================="
