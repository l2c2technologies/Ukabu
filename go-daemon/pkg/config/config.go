// Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
//
// For licensing inquiries, contact:
// Indranil Das Gupta <indradg@l2c2.co.in>

package config

import (
	"encoding/json"
	"os"
	"time"
)

type XFFHandling struct {
	Enabled             bool     `json:"enabled"`
	HeaderName          string   `json:"header_name"`
	Recursive           bool     `json:"recursive"`
	TrustedProxySources []string `json:"trusted_proxy_sources"`
	CustomProxies       []string `json:"custom_proxies"`
}

type DomainConfig struct {
	POWDifficulty         int                 `json:"pow_difficulty"`
	HMACSecret            string              `json:"hmac_secret"`
	HMACSecretOld         *string             `json:"hmac_secret_old"`
	SecretRotationExpires *time.Time          `json:"secret_rotation_expires"`
	CookieDuration        int                 `json:"cookie_duration"`
	LockoutPeriod         int                 `json:"lockout_period"` // minutes
	ExcuseFirstTimeout    bool                `json:"excuse_first_timeout"`
	ExemptPaths           []string            `json:"exempt_paths"`
	RestrictedPaths       map[string][]string `json:"restricted_paths"`
	XFFHandling           XFFHandling         `json:"xff_handling"`
}

type DefaultConfig struct {
	POWDifficulty      int         `json:"pow_difficulty"`
	CookieDuration     int         `json:"cookie_duration"`
	LockoutPeriod      int         `json:"lockout_period"`
	ExcuseFirstTimeout bool        `json:"excuse_first_timeout"`
	XFFHandling        XFFHandling `json:"xff_handling"`
}

type Config struct {
	Default DefaultConfig           `json:"default"`
	Domains map[string]DomainConfig `json:"domains"`
}

func Load(path string) (*Config, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var cfg Config
	if err := json.NewDecoder(file).Decode(&cfg); err != nil {
		return nil, err
	}

	// Apply defaults to domains that don't override
	for domain, dcfg := range cfg.Domains {
		if dcfg.POWDifficulty == 0 {
			dcfg.POWDifficulty = cfg.Default.POWDifficulty
		}
		if dcfg.CookieDuration == 0 {
			dcfg.CookieDuration = cfg.Default.CookieDuration
		}
		if dcfg.LockoutPeriod == 0 {
			dcfg.LockoutPeriod = cfg.Default.LockoutPeriod
		}
		// Update map
		cfg.Domains[domain] = dcfg
	}

	return &cfg, nil
}

func (c *Config) GetDomainConfig(domain string) (DomainConfig, bool) {
	cfg, exists := c.Domains[domain]
	return cfg, exists
}
