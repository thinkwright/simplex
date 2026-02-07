# Multi-stage build for smaller final image
FROM golang:1.22-alpine AS builder

WORKDIR /app

# Copy lint module (dependency)
COPY lint/go.mod lint/go.sum ./lint/
COPY lint/ ./lint/

# Copy web module
COPY web/go.mod web/go.sum ./web/

WORKDIR /app/web

# Download dependencies
RUN go mod download

# Copy web source code
COPY web/ ./

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o simplex-web ./cmd/server

# Final stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Copy the binary from builder
COPY --from=builder /app/web/simplex-web .

# Set environment variables
ENV PORT=8080

# Expose port
EXPOSE 8080

# Run the binary
CMD ["./simplex-web"]
