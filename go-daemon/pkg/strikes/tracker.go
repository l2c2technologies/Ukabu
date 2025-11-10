// Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
//
// For licensing inquiries, contact:
// Indranil Das Gupta <indradg@l2c2.co.in>

package strikes

import (
	"database/sql"
	"sync"
	"time"

	_ "github.com/mattn/go-sqlite3"
	"ukabu-trackerd/pkg/config"
	"ukabu-trackerd/pkg/ipset"
)

type Logger interface {
	Log(level, event string, fields map[string]interface{})
}

type Strike struct {
	IP                  string
	Domain              string
	StrikeCount         int
	FirstFailure        time.Time
	LastFailure         time.Time
	FirstTimeoutExcused bool
	ExpiresAt           *time.Time
}

type Tracker struct {
	db       *sql.DB
	config   *config.Config
	ipsetMgr *ipset.Manager
	logger   Logger
	strikes  map[string]*Strike // key: "ip:domain"
	mu       sync.RWMutex
}

func NewTracker(dbPath string, cfg *config.Config, ipsetMgr *ipset.Manager, logger Logger) (*Tracker, error) {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, err
	}

	// Initialize schema
	if err := initSchema(db); err != nil {
		db.Close()
		return nil, err
	}

	t := &Tracker{
		db:       db,
		config:   cfg,
		ipsetMgr: ipsetMgr,
		logger:   logger,
		strikes:  make(map[string]*Strike),
	}

	// Load strikes from database
	if err := t.loadStrikes(); err != nil {
		logger.Log("warn", "strikes_load_failed", map[string]interface{}{
			"error": err.Error(),
		})
	}

	return t, nil
}

func initSchema(db *sql.DB) error {
	schema := `
	CREATE TABLE IF NOT EXISTS strikes (
		ip TEXT NOT NULL,
		domain TEXT NOT NULL,
		strike_count INTEGER NOT NULL,
		first_failure TIMESTAMP NOT NULL,
		last_failure TIMESTAMP NOT NULL,
		first_timeout_excused BOOLEAN DEFAULT 0,
		expires_at TIMESTAMP,
		PRIMARY KEY (ip, domain)
	);
	
	CREATE INDEX IF NOT EXISTS idx_expires ON strikes(expires_at);
	CREATE INDEX IF NOT EXISTS idx_domain ON strikes(domain);
	
	CREATE TABLE IF NOT EXISTS blocked_ips (
		ip TEXT PRIMARY KEY,
		domain TEXT NOT NULL,
		blocked_at TIMESTAMP NOT NULL,
		lockout_expires TIMESTAMP,
		reason TEXT,
		ipset_name TEXT
	);
	`
	_, err := db.Exec(schema)
	return err
}

func (t *Tracker) loadStrikes() error {
	rows, err := t.db.Query(`
		SELECT ip, domain, strike_count, first_failure, last_failure, 
		       first_timeout_excused, expires_at
		FROM strikes
		WHERE expires_at IS NULL OR expires_at > ?
	`, time.Now().UTC())
	if err != nil {
		return err
	}
	defer rows.Close()

	count := 0
	for rows.Next() {
		s := &Strike{}
		var expiresAt sql.NullTime
		
		err := rows.Scan(&s.IP, &s.Domain, &s.StrikeCount, &s.FirstFailure,
			&s.LastFailure, &s.FirstTimeoutExcused, &expiresAt)
		if err != nil {
			continue
		}

		if expiresAt.Valid {
			s.ExpiresAt = &expiresAt.Time
		}

		key := s.IP + ":" + s.Domain
		t.strikes[key] = s
		count++
	}

	t.logger.Log("info", "strikes_loaded", map[string]interface{}{
		"count": count,
	})

	return nil
}

func (t *Tracker) RecordFailure(ip, domain, reason string) (int, bool) {
	t.mu.Lock()
	defer t.mu.Unlock()

	key := ip + ":" + domain
	now := time.Now().UTC()

	domainCfg, exists := t.config.GetDomainConfig(domain)
	if !exists {
		// Use default config
		domainCfg = config.DomainConfig{
			LockoutPeriod:      t.config.Default.LockoutPeriod,
			ExcuseFirstTimeout: t.config.Default.ExcuseFirstTimeout,
		}
	}

	strike, exists := t.strikes[key]
	if !exists {
		strike = &Strike{
			IP:           ip,
			Domain:       domain,
			StrikeCount:  0,
			FirstFailure: now,
			LastFailure:  now,
		}
		t.strikes[key] = strike
	}

	// Check if this is a timeout and if we should excuse it
	shouldExcuse := false
	if reason == "timeout" && domainCfg.ExcuseFirstTimeout && !strike.FirstTimeoutExcused {
		shouldExcuse = true
		strike.FirstTimeoutExcused = true
		t.logger.Log("info", "first_timeout_excused", map[string]interface{}{
			"ip":     ip,
			"domain": domain,
		})
	}

	if !shouldExcuse {
		strike.StrikeCount++
		strike.LastFailure = now
	}

	// Calculate expiry
	if domainCfg.LockoutPeriod > 0 {
		expiresAt := now.Add(time.Duration(domainCfg.LockoutPeriod) * time.Minute)
		strike.ExpiresAt = &expiresAt
	}

	// Persist to database
	t.saveStrike(strike)

	// Log failure
	t.logger.Log("warn", "pow_failure", map[string]interface{}{
		"ip":           ip,
		"domain":       domain,
		"reason":       reason,
		"strike_count": strike.StrikeCount,
		"excused":      shouldExcuse,
	})

	// Check if we should block (3 strikes)
	if strike.StrikeCount >= 3 {
		t.blockIP(ip, domain, strike)
		return strike.StrikeCount, true
	}

	return strike.StrikeCount, false
}

func (t *Tracker) RecordSuccess(ip, domain string) {
	t.mu.Lock()
	defer t.mu.Unlock()

	key := ip + ":" + domain
	
	if _, exists := t.strikes[key]; exists {
		delete(t.strikes, key)
		
		// Remove from database
		t.db.Exec("DELETE FROM strikes WHERE ip = ? AND domain = ?", ip, domain)
		
		t.logger.Log("info", "strike_cleared", map[string]interface{}{
			"ip":     ip,
			"domain": domain,
		})
	}
}

func (t *Tracker) blockIP(ip, domain string, strike *Strike) {
	now := time.Now().UTC()
	
	domainCfg, _ := t.config.GetDomainConfig(domain)
	
	var lockoutExpires *time.Time
	var ipsetName string
	
	if domainCfg.LockoutPeriod == 0 {
		// Permanent block
		ipsetName = "ukabu-permanent"
	} else {
		// Temporary block
		ipsetName = t.ipsetMgr.GetAvailableTemporarySet()
		expires := now.Add(time.Duration(domainCfg.LockoutPeriod) * time.Minute)
		lockoutExpires = &expires
	}

	// Add to ipset
	if err := t.ipsetMgr.AddIP(ipsetName, ip); err != nil {
		t.logger.Log("error", "ipset_add_failed", map[string]interface{}{
			"ip":     ip,
			"ipset":  ipsetName,
			"error":  err.Error(),
		})
		return
	}

	// Record in blocked_ips table
	var expiresSQL interface{} = nil
	if lockoutExpires != nil {
		expiresSQL = lockoutExpires
	}
	
	_, err := t.db.Exec(`
		INSERT OR REPLACE INTO blocked_ips 
		(ip, domain, blocked_at, lockout_expires, reason, ipset_name)
		VALUES (?, ?, ?, ?, ?, ?)
	`, ip, domain, now, expiresSQL, "3_strikes", ipsetName)
	
	if err != nil {
		t.logger.Log("error", "blocked_ip_record_failed", map[string]interface{}{
			"error": err.Error(),
		})
	}

	t.logger.Log("info", "ip_blocked", map[string]interface{}{
		"ip":             ip,
		"domain":         domain,
		"ukabu_status":   "001",
		"strike_count":   strike.StrikeCount,
		"ipset":          ipsetName,
		"lockout_period": domainCfg.LockoutPeriod,
	})
}

func (t *Tracker) saveStrike(strike *Strike) {
	var expiresSQL interface{} = nil
	if strike.ExpiresAt != nil {
		expiresSQL = strike.ExpiresAt
	}

	_, err := t.db.Exec(`
		INSERT OR REPLACE INTO strikes 
		(ip, domain, strike_count, first_failure, last_failure, first_timeout_excused, expires_at)
		VALUES (?, ?, ?, ?, ?, ?, ?)
	`, strike.IP, strike.Domain, strike.StrikeCount, strike.FirstFailure,
		strike.LastFailure, strike.FirstTimeoutExcused, expiresSQL)

	if err != nil {
		t.logger.Log("error", "strike_save_failed", map[string]interface{}{
			"error": err.Error(),
		})
	}
}

func (t *Tracker) CleanupExpired() {
	t.mu.Lock()
	defer t.mu.Unlock()

	now := time.Now().UTC()
	cleaned := 0

	// Clean strikes
	for key, strike := range t.strikes {
		if strike.ExpiresAt != nil && strike.ExpiresAt.Before(now) {
			delete(t.strikes, key)
			t.db.Exec("DELETE FROM strikes WHERE ip = ? AND domain = ?", strike.IP, strike.Domain)
			cleaned++
		}
	}

	// Clean blocked IPs
	rows, err := t.db.Query(`
		SELECT ip, ipset_name FROM blocked_ips 
		WHERE lockout_expires IS NOT NULL AND lockout_expires < ?
	`, now)
	
	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var ip, ipsetName string
			if rows.Scan(&ip, &ipsetName) == nil {
				t.ipsetMgr.RemoveIP(ipsetName, ip)
				t.db.Exec("DELETE FROM blocked_ips WHERE ip = ?", ip)
				
				t.logger.Log("info", "ip_unjailed", map[string]interface{}{
					"ip":    ip,
					"ipset": ipsetName,
				})
			}
		}
	}

	if cleaned > 0 {
		t.logger.Log("info", "expired_strikes_cleaned", map[string]interface{}{
			"count": cleaned,
		})
	}
}

func (t *Tracker) ActiveStrikes() int {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return len(t.strikes)
}

func (t *Tracker) GetStrikeCount(ip, domain string) int {
	t.mu.RLock()
	defer t.mu.RUnlock()
	
	key := ip + ":" + domain
	if strike, exists := t.strikes[key]; exists {
		return strike.StrikeCount
	}
	return 0
}

func (t *Tracker) Close() {
	if t.db != nil {
		t.db.Close()
	}
}
