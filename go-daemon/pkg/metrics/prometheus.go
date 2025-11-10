// Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
//
// For licensing inquiries, contact:
// Indranil Das Gupta <indradg@l2c2.co.in>

package metrics

import (
	"fmt"
	"net/http"
	"time"
)

type Logger interface {
	Log(level, event string, fields map[string]interface{})
}

type Tracker interface {
	ActiveStrikes() int
}

type IPSetManager interface {
	GetPermanentSetSize() int
	GetTemporarySetsTotalSize() int
	GetWhitelistSize() int
	GetSearchEngineSetSize() int
}

type Server struct {
	port          int
	tracker       Tracker
	ipsetMgr      IPSetManager
	logger        Logger
	startTime     time.Time
	blockCount    int64
	strikeUpdates int64
}

func NewServer(port int, tracker Tracker, ipsetMgr IPSetManager, logger Logger) *Server {
	return &Server{
		port:      port,
		tracker:   tracker,
		ipsetMgr:  ipsetMgr,
		logger:    logger,
		startTime: time.Now(),
	}
}

func (s *Server) Start() error {
	http.HandleFunc("/metrics", s.handleMetrics)
	http.HandleFunc("/health", s.handleHealth)

	addr := fmt.Sprintf(":%d", s.port)
	s.logger.Log("info", "metrics_server_listening", map[string]interface{}{
		"address": addr,
	})

	return http.ListenAndServe(addr, nil)
}

func (s *Server) handleMetrics(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain; version=0.0.4")

	// Active strikes
	activeStrikes := s.tracker.ActiveStrikes()
	fmt.Fprintf(w, "# HELP ukabu_active_strikes Number of IPs with active strikes\n")
	fmt.Fprintf(w, "# TYPE ukabu_active_strikes gauge\n")
	fmt.Fprintf(w, "ukabu_active_strikes %d\n", activeStrikes)

	// Permanent blacklist size
	permanentSize := s.ipsetMgr.GetPermanentSetSize()
	fmt.Fprintf(w, "# HELP ukabu_permanent_blocks Number of permanently blocked IPs\n")
	fmt.Fprintf(w, "# TYPE ukabu_permanent_blocks gauge\n")
	fmt.Fprintf(w, "ukabu_permanent_blocks %d\n", permanentSize)

	// Temporary blacklist size
	temporarySize := s.ipsetMgr.GetTemporarySetsTotalSize()
	fmt.Fprintf(w, "# HELP ukabu_temporary_blocks Number of temporarily blocked IPs\n")
	fmt.Fprintf(w, "# TYPE ukabu_temporary_blocks gauge\n")
	fmt.Fprintf(w, "ukabu_temporary_blocks %d\n", temporarySize)

	// Total blocked IPs
	totalBlocked := permanentSize + temporarySize
	fmt.Fprintf(w, "# HELP ukabu_total_blocks Total number of blocked IPs\n")
	fmt.Fprintf(w, "# TYPE ukabu_total_blocks gauge\n")
	fmt.Fprintf(w, "ukabu_total_blocks %d\n", totalBlocked)

	// Whitelist size
	whitelistSize := s.ipsetMgr.GetWhitelistSize()
	fmt.Fprintf(w, "# HELP ukabu_whitelist_size Number of whitelisted IPs\n")
	fmt.Fprintf(w, "# TYPE ukabu_whitelist_size gauge\n")
	fmt.Fprintf(w, "ukabu_whitelist_size %d\n", whitelistSize)

	// Search engine set size
	searchEngineSize := s.ipsetMgr.GetSearchEngineSetSize()
	fmt.Fprintf(w, "# HELP ukabu_search_engine_ips Number of search engine IPs\n")
	fmt.Fprintf(w, "# TYPE ukabu_search_engine_ips gauge\n")
	fmt.Fprintf(w, "ukabu_search_engine_ips %d\n", searchEngineSize)

	// Daemon uptime
	uptime := time.Since(s.startTime).Seconds()
	fmt.Fprintf(w, "# HELP ukabu_uptime_seconds Daemon uptime in seconds\n")
	fmt.Fprintf(w, "# TYPE ukabu_uptime_seconds counter\n")
	fmt.Fprintf(w, "ukabu_uptime_seconds %.0f\n", uptime)

	// Block count (total blocks issued)
	fmt.Fprintf(w, "# HELP ukabu_blocks_total Total blocks issued since start\n")
	fmt.Fprintf(w, "# TYPE ukabu_blocks_total counter\n")
	fmt.Fprintf(w, "ukabu_blocks_total %d\n", s.blockCount)

	// Strike updates
	fmt.Fprintf(w, "# HELP ukabu_strike_updates_total Total strike updates processed\n")
	fmt.Fprintf(w, "# TYPE ukabu_strike_updates_total counter\n")
	fmt.Fprintf(w, "ukabu_strike_updates_total %d\n", s.strikeUpdates)
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, `{"status":"healthy","uptime_seconds":%.0f}`, time.Since(s.startTime).Seconds())
}

func (s *Server) IncrementBlocks() {
	s.blockCount++
}

func (s *Server) IncrementStrikeUpdates() {
	s.strikeUpdates++
}
