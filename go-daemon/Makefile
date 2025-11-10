# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
#
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>

.PHONY: all build clean install test deps

BINARY=ukabu-trackerd
VERSION=1.0.0-phase2
BUILD_DIR=build
INSTALL_DIR=/usr/local/bin

all: build

build:
	@echo "Building $(BINARY) $(VERSION)..."
	@mkdir -p $(BUILD_DIR)
	CGO_ENABLED=1 go build -ldflags="-s -w" -o $(BUILD_DIR)/$(BINARY) .
	@echo "Build complete: $(BUILD_DIR)/$(BINARY)"

install: build
	@echo "Installing $(BINARY) to $(INSTALL_DIR)..."
	@install -m 755 $(BUILD_DIR)/$(BINARY) $(INSTALL_DIR)/
	@echo "Installation complete"

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf $(BUILD_DIR)
	@echo "Clean complete"

test:
	@echo "Running tests..."
	@go test -v ./...

deps:
	@echo "Downloading dependencies..."
	@go mod download
	@go mod verify
	@echo "Dependencies ready"
