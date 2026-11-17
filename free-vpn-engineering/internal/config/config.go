// SPDX-License-Identifier: GPL-3.0-or-later
package config

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"regexp"
	"slices"
	"strconv"
	"strings"
	"time"
)

type User struct {
	Name     string `json:"name"`
	Password string `json:"password"`
}

type Config struct {
	Port                int
	CorePort            int
	WSPath              string
	Users               []User
	EgressPorts         []int
	MaxTunnels          int
	HandshakesPerMinute int
	HandshakeBurst      int
	IdleTimeout         time.Duration
	MaxAge              time.Duration
	CoreBinary          string
	LogLevel            string
}

var userNameRE = regexp.MustCompile(`^[a-zA-Z0-9_-]{1,32}$`)
var pathRE = regexp.MustCompile(`^/[a-zA-Z0-9_-]{4,80}$`)

// Load deliberately returns errors that never contain passwords or raw JSON.
func Load(getenv func(string) string) (Config, error) {
	c := Config{}
	var err error
	number := func(key string, fallback, low, high int) (int, error) {
		raw := getenv(key)
		if raw == "" {
			return fallback, nil
		}
		n, e := strconv.Atoi(raw)
		if e != nil || n < low || n > high {
			return 0, fmt.Errorf("%s must be an integer in [%d,%d]", key, low, high)
		}
		return n, nil
	}
	if c.Port, err = number("PORT", 10000, 1024, 65535); err != nil {
		return c, err
	}
	if c.CorePort, err = number("CORE_PORT", 10001, 1024, 65535); err != nil {
		return c, err
	}
	if c.Port == c.CorePort {
		return c, errors.New("PORT and CORE_PORT must be different")
	}
	if c.MaxTunnels, err = number("MAX_TUNNELS", 16, 1, 256); err != nil {
		return c, err
	}
	if c.HandshakesPerMinute, err = number("HANDSHAKES_PER_MINUTE", 60, 1, 10000); err != nil {
		return c, err
	}
	if c.HandshakeBurst, err = number("HANDSHAKE_BURST", 20, 1, 1000); err != nil {
		return c, err
	}
	c.WSPath = getenv("WS_PATH")
	if c.WSPath == "" {
		c.WSPath = "/tunnel"
	}
	if !pathRE.MatchString(c.WSPath) || c.WSPath == "/healthz" || c.WSPath == "/robots" {
		return c, errors.New("WS_PATH must be a non-reserved /path of 4-80 URL-safe characters")
	}
	c.CoreBinary = getenv("SING_BOX_BINARY")
	if c.CoreBinary == "" {
		c.CoreBinary = "sing-box"
	}
	c.LogLevel = getenv("LOG_LEVEL")
	if c.LogLevel == "" {
		c.LogLevel = "warn"
	}
	if c.LogLevel != "warn" && c.LogLevel != "error" {
		return c, errors.New("LOG_LEVEL must be warn or error")
	}
	duration := func(key string, fallback, min, max time.Duration) (time.Duration, error) {
		raw := getenv(key)
		if raw == "" {
			return fallback, nil
		}
		d, e := time.ParseDuration(raw)
		if e != nil || d < min || d > max {
			return 0, fmt.Errorf("%s must be between %s and %s", key, min, max)
		}
		return d, nil
	}
	if c.IdleTimeout, err = duration("TUNNEL_IDLE_TIMEOUT", 2*time.Minute, 10*time.Second, 10*time.Minute); err != nil {
		return c, err
	}
	if c.MaxAge, err = duration("TUNNEL_MAX_AGE", 30*time.Minute, time.Minute, time.Hour); err != nil {
		return c, err
	}
	if c.IdleTimeout > c.MaxAge {
		return c, errors.New("TUNNEL_IDLE_TIMEOUT must not exceed TUNNEL_MAX_AGE")
	}
	password, rawUsers := getenv("TROJAN_PASSWORD"), getenv("TROJAN_USERS_JSON")
	if password != "" && rawUsers != "" {
		return c, errors.New("set only one of TROJAN_PASSWORD and TROJAN_USERS_JSON")
	}
	if password != "" {
		c.Users = []User{{Name: "owner", Password: password}}
	} else if rawUsers != "" {
		if len(rawUsers) > 32768 {
			return c, errors.New("TROJAN_USERS_JSON is too large")
		}
		d := json.NewDecoder(strings.NewReader(rawUsers))
		d.DisallowUnknownFields()
		if d.Decode(&c.Users) != nil {
			return c, errors.New("TROJAN_USERS_JSON must be an array of name/password objects")
		}
		var extra any
		if d.Decode(&extra) != io.EOF {
			return c, errors.New("TROJAN_USERS_JSON contains trailing data")
		}
	} else {
		return c, errors.New("TROJAN_PASSWORD or TROJAN_USERS_JSON is required; refusing unauthenticated startup")
	}
	if len(c.Users) < 1 || len(c.Users) > 64 {
		return c, errors.New("configure between 1 and 64 users")
	}
	names, passes := map[string]bool{}, map[string]bool{}
	for _, u := range c.Users {
		if !userNameRE.MatchString(u.Name) || names[u.Name] {
			return c, errors.New("user names must be unique and contain 1-32 letters, digits, _ or -")
		}
		if !StrongPassword(u.Password) || passes[u.Password] {
			return c, errors.New("user passwords must be unique, random, printable ASCII, and 24-256 characters")
		}
		names[u.Name] = true
		passes[u.Password] = true
	}
	rawPorts := getenv("EGRESS_TCP_PORTS")
	if rawPorts == "" {
		rawPorts = "80,443"
	}
	seen := map[int]bool{}
	for _, raw := range strings.Split(rawPorts, ",") {
		n, e := strconv.Atoi(strings.TrimSpace(raw))
		if e != nil || n < 1 || n > 65535 || seen[n] {
			return c, errors.New("EGRESS_TCP_PORTS must be a unique comma-separated list of TCP ports")
		}
		if n == 25 || n == 465 || n == 587 {
			return c, errors.New("SMTP egress ports are intentionally disallowed")
		}
		c.EgressPorts = append(c.EgressPorts, n)
		seen[n] = true
	}
	if len(c.EgressPorts) > 16 {
		return c, errors.New("at most 16 egress ports are supported")
	}
	slices.Sort(c.EgressPorts)
	return c, nil
}

func StrongPassword(s string) bool {
	if len(s) < 24 || len(s) > 256 {
		return false
	}
	unique := map[rune]bool{}
	for _, r := range s {
		if r < 33 || r > 126 {
			return false
		}
		unique[r] = true
	}
	if len(unique) < 8 {
		return false
	}
	lower := strings.ToLower(s)
	for _, bad := range []string{"change_me", "changeme", "replace_me", "your_password", "example_password"} {
		if strings.Contains(lower, bad) {
			return false
		}
	}
	return true
}

// Reserved/non-public destinations, including metadata, mapped IPv4 and NAT64.
// This is defense in depth, not a substitute for a host-level egress firewall.
var BlockedCIDRs = []string{
	"0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
	"169.254.0.0/16", "172.16.0.0/12", "192.0.0.0/24", "192.0.2.0/24",
	"192.88.99.0/24", "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24",
	"203.0.113.0/24", "224.0.0.0/4", "240.0.0.0/4",
	"::/128", "::1/128", "::ffff:0:0/96", "64:ff9b::/96", "64:ff9b:1::/48",
	"100::/64", "2001::/23", "2001:db8::/32", "2002::/16", "3fff::/20",
	"fc00::/7", "fe80::/10", "ff00::/8",
}

// ServerJSON is generated at runtime into a mode-0600 temporary file.
// Render terminates public TLS; cleartext WebSocket exists on loopback only.
func (c Config) ServerJSON() ([]byte, error) {
	rules := []any{
		map[string]any{"network": []string{"udp", "icmp"}, "action": "reject"},
		map[string]any{"port": c.EgressPorts, "invert": true, "action": "reject"},
		map[string]any{"domain": []string{"localhost", "metadata.google.internal", "instance-data.ec2.internal"}, "domain_suffix": []string{".localhost", ".local", ".internal", ".lan", ".home", ".invalid", ".test"}, "action": "reject"},
		map[string]any{"action": "resolve", "server": "public-doh", "strategy": "ipv4_only", "timeout": "5s"},
		map[string]any{"ip_cidr": BlockedCIDRs, "ip_is_private": true, "action": "reject"},
	}
	conf := map[string]any{
		"log":       map[string]any{"level": c.LogLevel, "timestamp": true},
		"dns":       map[string]any{"servers": []any{map[string]any{"type": "https", "tag": "public-doh", "server": "1.1.1.1", "server_port": 443, "path": "/dns-query", "tls": map[string]any{"enabled": true, "server_name": "cloudflare-dns.com"}}}, "final": "public-doh"},
		"inbounds":  []any{map[string]any{"type": "trojan", "tag": "trojan-ws", "listen": "127.0.0.1", "listen_port": c.CorePort, "users": c.Users, "transport": map[string]any{"type": "ws", "path": c.WSPath}}},
		"outbounds": []any{map[string]any{"type": "direct", "tag": "internet"}},
		"route":     map[string]any{"rules": rules, "final": "internet", "default_domain_resolver": map[string]any{"server": "public-doh", "strategy": "ipv4_only"}},
	}
	return json.MarshalIndent(conf, "", "  ")
}
