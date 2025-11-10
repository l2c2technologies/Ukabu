// Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
//
// For licensing inquiries, contact:
// Indranil Das Gupta <indradg@l2c2.co.in>

package ipset

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"sync"
)

type BlacklistEntry struct {
	IPAddress     string `json:"ip_address"`
	Timestamp     string `json:"timestamp"`
	LockoutPeriod int    `json:"lockout_period"`
}

type Manager struct {
	fw            *FirewallManager
	logger        Logger
	temporarySets []string
	nextTempSet   int
	mu            sync.Mutex
}

const (
	PermanentSetName      = "ukabu-permanent"
	WhitelistSetName      = "ukabu-whitelist"
	SearchEngineSetName   = "ukabu-search-engines"
	TemporarySetPrefix    = "ukabu-temporary_"
	MaxIPsPerTemporarySet = 20000 // Increased from 10000 to 20000
)

func NewManager(fw *FirewallManager, logger Logger) *Manager {
	return &Manager{
		fw:            fw,
		logger:        logger,
		temporarySets: []string{},
		nextTempSet:   0,
	}
}

// Initialize creates all required ipsets and installs firewall rules
func (m *Manager) Initialize() error {
	// Create permanent blacklist
	if err := m.fw.CreateIPSet(PermanentSetName, 50000); err != nil {
		return fmt.Errorf("failed to create permanent set: %w", err)
	}

	// Create whitelist
	if err := m.fw.CreateIPSet(WhitelistSetName, 50000); err != nil {
		return fmt.Errorf("failed to create whitelist set: %w", err)
	}

	// Create search engine set
	if err := m.fw.CreateIPSet(SearchEngineSetName, 50000); err != nil {
		return fmt.Errorf("failed to create search engine set: %w", err)
	}

	// Create first temporary set
	if err := m.createTemporarySet(0); err != nil {
		return fmt.Errorf("failed to create temporary set: %w", err)
	}

	// Install firewall rules
	sets := []string{PermanentSetName, TemporarySetPrefix + "0"}
	if err := m.fw.InstallFirewallRules(sets); err != nil {
		return fmt.Errorf("failed to install firewall rules: %w", err)
	}

	m.logger.Log("info", "ipset_manager_initialized", map[string]interface{}{
		"permanent_set":     PermanentSetName,
		"whitelist_set":     WhitelistSetName,
		"search_engine_set": SearchEngineSetName,
		"temporary_sets":    1,
	})

	return nil
}

func (m *Manager) createTemporarySet(index int) error {
	setName := fmt.Sprintf("%s%d", TemporarySetPrefix, index)
	if err := m.fw.CreateIPSet(setName, MaxIPsPerTemporarySet); err != nil {
		return err
	}
	m.temporarySets = append(m.temporarySets, setName)
	
	m.logger.Log("info", "temporary_set_created", map[string]interface{}{
		"set": setName,
	})
	
	return nil
}

// GetAvailableTemporarySet returns a temporary set that has capacity
func (m *Manager) GetAvailableTemporarySet() string {
	m.mu.Lock()
	defer m.mu.Unlock()

	// Check current set
	currentSet := m.temporarySets[m.nextTempSet]
	size, err := m.fw.GetIPSetSize(currentSet)
	if err != nil || size < MaxIPsPerTemporarySet {
		return currentSet
	}

	// Current set is full, try next
	m.nextTempSet++
	if m.nextTempSet >= len(m.temporarySets) {
		// Need to create new set
		index := len(m.temporarySets)
		if err := m.createTemporarySet(index); err != nil {
			m.logger.Log("error", "temp_set_creation_failed", map[string]interface{}{
				"error": err.Error(),
			})
			// Fall back to first set
			m.nextTempSet = 0
			return m.temporarySets[0]
		}
		
		// Install firewall rule for new set
		m.fw.InstallFirewallRules([]string{m.temporarySets[index]})
	}

	return m.temporarySets[m.nextTempSet]
}

// AddIP adds an IP to the specified set
func (m *Manager) AddIP(setName, ip string) error {
	return m.fw.AddIPToSet(setName, ip)
}

// RemoveIP removes an IP from the specified set
func (m *Manager) RemoveIP(setName, ip string) error {
	return m.fw.RemoveIPFromSet(setName, ip)
}

// LoadBlacklist loads IPs from ip_blacklist.conf
func (m *Manager) LoadBlacklist(path string) error {
	file, err := os.Open(path)
	if err != nil {
		if os.IsNotExist(err) {
			// File doesn't exist yet, that's okay
			return nil
		}
		return err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	permanent := 0
	temporary := 0

	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}

		var entry BlacklistEntry
		if err := json.Unmarshal([]byte(line), &entry); err != nil {
			m.logger.Log("warn", "blacklist_parse_error", map[string]interface{}{
				"line":  line,
				"error": err.Error(),
			})
			continue
		}

		var setName string
		if entry.LockoutPeriod == 0 {
			setName = PermanentSetName
			permanent++
		} else {
			setName = m.GetAvailableTemporarySet()
			temporary++
		}

		if err := m.AddIP(setName, entry.IPAddress); err != nil {
			m.logger.Log("error", "blacklist_add_failed", map[string]interface{}{
				"ip":    entry.IPAddress,
				"error": err.Error(),
			})
		}
	}

	m.logger.Log("info", "blacklist_loaded", map[string]interface{}{
		"permanent": permanent,
		"temporary": temporary,
	})

	return scanner.Err()
}

// GetPermanentSetSize returns the size of the permanent blacklist
func (m *Manager) GetPermanentSetSize() int {
	size, _ := m.fw.GetIPSetSize(PermanentSetName)
	return size
}

// GetTemporarySetsTotalSize returns the total size of all temporary sets
func (m *Manager) GetTemporarySetsTotalSize() int {
	total := 0
	for _, setName := range m.temporarySets {
		size, _ := m.fw.GetIPSetSize(setName)
		total += size
	}
	return total
}

// GetWhitelistSize returns the size of the whitelist
func (m *Manager) GetWhitelistSize() int {
	size, _ := m.fw.GetIPSetSize(WhitelistSetName)
	return size
}

// GetSearchEngineSetSize returns the size of the search engine set
func (m *Manager) GetSearchEngineSetSize() int {
	size, _ := m.fw.GetIPSetSize(SearchEngineSetName)
	return size
}
