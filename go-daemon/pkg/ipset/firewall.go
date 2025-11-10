// Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
//
// For licensing inquiries, contact:
// Indranil Das Gupta <indradg@l2c2.co.in>

package ipset

import (
	"fmt"
	"os/exec"
	"strings"
)

type Logger interface {
	Log(level, event string, fields map[string]interface{})
}

type FirewallBackend string

const (
	BackendIPTables FirewallBackend = "iptables"
	BackendNFTables FirewallBackend = "nftables"
)

type FirewallManager struct {
	backend FirewallBackend
	logger  Logger
}

func NewFirewallManager(logger Logger) (*FirewallManager, error) {
	fm := &FirewallManager{
		logger: logger,
	}

	// Auto-detect backend
	if isNFTablesAvailable() {
		fm.backend = BackendNFTables
		logger.Log("info", "firewall_backend_detected", map[string]interface{}{
			"backend": "nftables",
		})
	} else if isIPTablesAvailable() {
		fm.backend = BackendIPTables
		logger.Log("info", "firewall_backend_detected", map[string]interface{}{
			"backend": "iptables",
		})
	} else {
		return nil, fmt.Errorf("no firewall backend available (tried nftables and iptables)")
	}

	return fm, nil
}

func (fm *FirewallManager) Backend() string {
	return string(fm.backend)
}

func isNFTablesAvailable() bool {
	cmd := exec.Command("nft", "list", "tables")
	return cmd.Run() == nil
}

func isIPTablesAvailable() bool {
	cmd := exec.Command("iptables", "-L", "-n")
	return cmd.Run() == nil
}

// CreateIPSet creates a new ipset
func (fm *FirewallManager) CreateIPSet(name string, maxElem int) error {
	cmd := exec.Command("ipset", "create", name, "hash:net", "maxelem", fmt.Sprintf("%d", maxElem), "-exist")
	output, err := cmd.CombinedOutput()
	if err != nil {
		fm.logger.Log("error", "ipset_create_failed", map[string]interface{}{
			"name":   name,
			"error":  err.Error(),
			"output": string(output),
		})
		return err
	}
	return nil
}

// AddIPToSet adds an IP to an ipset
func (fm *FirewallManager) AddIPToSet(setName, ip string) error {
	cmd := exec.Command("ipset", "add", setName, ip, "-exist")
	output, err := cmd.CombinedOutput()
	if err != nil {
		fm.logger.Log("error", "ipset_add_failed", map[string]interface{}{
			"set":    setName,
			"ip":     ip,
			"error":  err.Error(),
			"output": string(output),
		})
		return err
	}
	return nil
}

// RemoveIPFromSet removes an IP from an ipset
func (fm *FirewallManager) RemoveIPFromSet(setName, ip string) error {
	cmd := exec.Command("ipset", "del", setName, ip, "-exist")
	output, err := cmd.CombinedOutput()
	if err != nil {
		fm.logger.Log("warn", "ipset_remove_failed", map[string]interface{}{
			"set":    setName,
			"ip":     ip,
			"error":  err.Error(),
			"output": string(output),
		})
		return err
	}
	return nil
}

// ListIPSet lists all IPs in a set
func (fm *FirewallManager) ListIPSet(setName string) ([]string, error) {
	cmd := exec.Command("ipset", "list", setName)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return nil, err
	}

	var ips []string
	lines := strings.Split(string(output), "\n")
	inMembers := false
	
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "Members:" {
			inMembers = true
			continue
		}
		if inMembers && line != "" && !strings.HasPrefix(line, "Size") {
			ips = append(ips, line)
		}
	}

	return ips, nil
}

// GetIPSetSize returns the number of entries in a set
func (fm *FirewallManager) GetIPSetSize(setName string) (int, error) {
	ips, err := fm.ListIPSet(setName)
	if err != nil {
		return 0, err
	}
	return len(ips), nil
}

// InstallFirewallRules installs rules to block ipsets
func (fm *FirewallManager) InstallFirewallRules(setNames []string) error {
	if fm.backend == BackendIPTables {
		return fm.installIPTablesRules(setNames)
	}
	return fm.installNFTablesRules(setNames)
}

func (fm *FirewallManager) installIPTablesRules(setNames []string) error {
	for _, setName := range setNames {
		// Check if rule already exists
		cmd := exec.Command("iptables", "-C", "INPUT", "-m", "set", "--match-set", setName, "src", "-j", "DROP")
		if cmd.Run() != nil {
			// Rule doesn't exist, add it
			cmd = exec.Command("iptables", "-I", "INPUT", "1", "-m", "set", "--match-set", setName, "src", "-j", "DROP")
			output, err := cmd.CombinedOutput()
			if err != nil {
				fm.logger.Log("error", "iptables_rule_failed", map[string]interface{}{
					"set":    setName,
					"error":  err.Error(),
					"output": string(output),
				})
				return err
			}
			fm.logger.Log("info", "iptables_rule_added", map[string]interface{}{
				"set": setName,
			})
		}
	}
	return nil
}

func (fm *FirewallManager) installNFTablesRules(setNames []string) error {
	// Check if table exists
	cmd := exec.Command("nft", "list", "table", "inet", "ukabu")
	if cmd.Run() != nil {
		// Create table and chain
		script := `
table inet ukabu {
	chain input {
		type filter hook input priority filter; policy accept;
	}
}
`
		cmd = exec.Command("nft", "-f", "-")
		cmd.Stdin = strings.NewReader(script)
		if err := cmd.Run(); err != nil {
			fm.logger.Log("error", "nftables_table_create_failed", map[string]interface{}{
				"error": err.Error(),
			})
			return err
		}
	}

	// Add sets and rules
	for _, setName := range setNames {
		// Create set
		cmd := exec.Command("nft", "add", "set", "inet", "ukabu", setName, 
			"{", "type", "ipv4_addr", ";", "flags", "interval", ";", "}")
		if err := cmd.Run(); err != nil {
			// Set might already exist, continue
			fm.logger.Log("debug", "nftables_set_exists", map[string]interface{}{
				"set": setName,
			})
		}

		// Add rule to drop packets from set
		cmd = exec.Command("nft", "add", "rule", "inet", "ukabu", "input",
			"ip", "saddr", "@"+setName, "drop")
		if err := cmd.Run(); err != nil {
			fm.logger.Log("error", "nftables_rule_failed", map[string]interface{}{
				"set":   setName,
				"error": err.Error(),
			})
			// Continue even if rule fails (might already exist)
		} else {
			fm.logger.Log("info", "nftables_rule_added", map[string]interface{}{
				"set": setName,
			})
		}
	}

	return nil
}

// FlushIPSet removes all entries from a set
func (fm *FirewallManager) FlushIPSet(setName string) error {
	cmd := exec.Command("ipset", "flush", setName)
	return cmd.Run()
}

// DestroyIPSet removes a set
func (fm *FirewallManager) DestroyIPSet(setName string) error {
	cmd := exec.Command("ipset", "destroy", setName)
	return cmd.Run()
}
