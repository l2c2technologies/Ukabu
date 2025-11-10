// Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
//
// For licensing inquiries, contact:
// Indranil Das Gupta <indradg@l2c2.co.in>

package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"ukabu-trackerd/pkg/config"
	"ukabu-trackerd/pkg/ipset"
	"ukabu-trackerd/pkg/metrics"
	"ukabu-trackerd/pkg/socket"
	"ukabu-trackerd/pkg/strikes"
)

const version = "1.0.0-phase2"

var (
	configPath  = flag.String("config", "/etc/ukabu/config/domains.json", "Path to domains.json configuration")
	socketPath  = flag.String("socket", "/var/run/ukabu/tracker.sock", "Unix socket path")
	dbPath      = flag.String("db", "/var/lib/ukabu/strikes.db", "SQLite database path")
	metricsPort = flag.Int("metrics-port", 9090, "Prometheus metrics port")
	logPath     = flag.String("log", "/var/log/ukabu/trackerd.log", "Log file path")
	versionFlag = flag.Bool("version", false, "Show version and exit")
)

type Logger struct {
	file *os.File
}

func NewLogger(path string) (*Logger, error) {
	file, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0640)
	if err != nil {
		return nil, err
	}
	return &Logger{file: file}, nil
}

func (l *Logger) Log(level, event string, fields map[string]interface{}) {
	entry := map[string]interface{}{
		"timestamp": time.Now().UTC().Format(time.RFC3339Nano),
		"level":     level,
		"event":     event,
	}
	for k, v := range fields {
		entry[k] = v
	}
	data, _ := json.Marshal(entry)
	l.file.Write(append(data, '\n'))
}

func (l *Logger) Close() {
	if l.file != nil {
		l.file.Close()
	}
}

func main() {
	flag.Parse()

	if *versionFlag {
		fmt.Printf("ukabu-trackerd version %s\n", version)
		os.Exit(0)
	}

	// Initialize logger
	logger, err := NewLogger(*logPath)
	if err != nil {
		log.Fatalf("Failed to initialize logger: %v", err)
	}
	defer logger.Close()

	logger.Log("info", "daemon_start", map[string]interface{}{
		"version": version,
	})

	// Load configuration
	cfg, err := config.Load(*configPath)
	if err != nil {
		logger.Log("error", "config_load_failed", map[string]interface{}{
			"error": err.Error(),
		})
		log.Fatalf("Failed to load configuration: %v", err)
	}

	logger.Log("info", "config_loaded", map[string]interface{}{
		"domains": len(cfg.Domains),
	})

	// Initialize firewall manager (auto-detect iptables vs nftables)
	fwManager, err := ipset.NewFirewallManager(logger)
	if err != nil {
		logger.Log("error", "firewall_init_failed", map[string]interface{}{
			"error": err.Error(),
		})
		log.Fatalf("Failed to initialize firewall: %v", err)
	}

	logger.Log("info", "firewall_initialized", map[string]interface{}{
		"backend": fwManager.Backend(),
	})

	// Initialize ipset manager
	ipsetMgr := ipset.NewManager(fwManager, logger)
	if err := ipsetMgr.Initialize(); err != nil {
		logger.Log("error", "ipset_init_failed", map[string]interface{}{
			"error": err.Error(),
		})
		log.Fatalf("Failed to initialize ipsets: %v", err)
	}

	logger.Log("info", "ipsets_initialized", nil)

	// Load existing blacklist
	if err := ipsetMgr.LoadBlacklist("/etc/ukabu/config/ip_blacklist.conf"); err != nil {
		logger.Log("warn", "blacklist_load_failed", map[string]interface{}{
			"error": err.Error(),
		})
	}

	// Initialize strike tracker
	tracker, err := strikes.NewTracker(*dbPath, cfg, ipsetMgr, logger)
	if err != nil {
		logger.Log("error", "tracker_init_failed", map[string]interface{}{
			"error": err.Error(),
		})
		log.Fatalf("Failed to initialize strike tracker: %v", err)
	}
	defer tracker.Close()

	logger.Log("info", "tracker_initialized", map[string]interface{}{
		"strikes_loaded": tracker.ActiveStrikes(),
	})

	// Start metrics server
	metricsSrv := metrics.NewServer(*metricsPort, tracker, ipsetMgr, logger)
	go func() {
		if err := metricsSrv.Start(); err != nil {
			logger.Log("error", "metrics_server_failed", map[string]interface{}{
				"error": err.Error(),
			})
		}
	}()

	logger.Log("info", "metrics_server_started", map[string]interface{}{
		"port": *metricsPort,
	})

	// Start Unix socket server
	socketSrv := socket.NewServer(*socketPath, tracker, logger)
	
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go func() {
		if err := socketSrv.Start(ctx); err != nil {
			logger.Log("error", "socket_server_failed", map[string]interface{}{
				"error": err.Error(),
			})
			log.Fatalf("Socket server failed: %v", err)
		}
	}()

	logger.Log("info", "socket_listening", map[string]interface{}{
		"path": *socketPath,
	})

	// Start background cleanup goroutine
	go func() {
		ticker := time.NewTicker(60 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				tracker.CleanupExpired()
			case <-ctx.Done():
				return
			}
		}
	}()

	// Wait for shutdown signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	
	sig := <-sigChan
	logger.Log("info", "shutdown_signal_received", map[string]interface{}{
		"signal": sig.String(),
	})

	// Graceful shutdown
	cancel()
	socketSrv.Stop()
	
	logger.Log("info", "daemon_stopped", nil)
}
