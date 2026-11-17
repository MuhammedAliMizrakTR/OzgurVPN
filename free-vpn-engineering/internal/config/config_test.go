package config

import (
	"encoding/json"
	"net/netip"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

const testPassword = "T7z4kQ9nX2mW8pR5sV3yH6cB1fD0jL_a"

func env(overrides map[string]string) func(string) string {
	m := map[string]string{"TROJAN_PASSWORD": testPassword}
	for k, v := range overrides {
		m[k] = v
	}
	return func(k string) string { return m[k] }
}
func TestDefaults(t *testing.T) {
	c, e := Load(env(nil))
	if e != nil {
		t.Fatal(e)
	}
	if c.Port != 10000 || c.CorePort != 10001 || c.MaxTunnels != 16 || len(c.Users) != 1 || c.WSPath != "/tunnel" {
		t.Fatalf("unexpected defaults")
	}
	if len(c.EgressPorts) != 2 || c.EgressPorts[0] != 80 || c.EgressPorts[1] != 443 {
		t.Fatal("unexpected egress defaults")
	}
}
func TestInvalidEnvironment(t *testing.T) {
	cases := map[string]map[string]string{
		"missing authentication": {"TROJAN_PASSWORD": ""}, "weak password": {"TROJAN_PASSWORD": "too-short"},
		"placeholder password":   {"TROJAN_PASSWORD": "CHANGE_ME_to_a_real_password_12345"},
		"whitespace in password": {"TROJAN_PASSWORD": "not a valid password with whitespace 12345"},
		"duplicate ports":        {"EGRESS_TCP_PORTS": "80,80"}, "mail port": {"EGRESS_TCP_PORTS": "25,443"},
		"bad port": {"PORT": "not-a-port"}, "low port": {"PORT": "80"}, "same ports": {"PORT": "10001"},
		"bad path": {"WS_PATH": "//other.example/path"}, "reserved path": {"WS_PATH": "/healthz"},
		"path query": {"WS_PATH": "/tunnel?password=test"}, "zero tunnels": {"MAX_TUNNELS": "0"},
		"both secrets":       {"TROJAN_USERS_JSON": "[]"},
		"empty users":        {"TROJAN_PASSWORD": "", "TROJAN_USERS_JSON": "[]"},
		"unknown JSON field": {"TROJAN_PASSWORD": "", "TROJAN_USERS_JSON": "[{\"name\":\"a\",\"password\":\"" + testPassword + "\",\"typo\":1}]"},
		"trailing JSON":      {"TROJAN_PASSWORD": "", "TROJAN_USERS_JSON": "[] []"},
		"long idle":          {"TUNNEL_IDLE_TIMEOUT": "11m"}, "bad log level": {"LOG_LEVEL": "debug"},
		"idle exceeds age": {"TUNNEL_IDLE_TIMEOUT": "2m", "TUNNEL_MAX_AGE": "1m"},
	}
	for name, m := range cases {
		t.Run(name, func(t *testing.T) {
			_, e := Load(env(m))
			if e == nil {
				t.Fatal("expected failure")
			}
			if strings.Contains(e.Error(), testPassword) {
				t.Fatal("secret leaked in error")
			}
		})
	}
}
func TestMultipleUsers(t *testing.T) {
	raw := `[{"name":"alice","password":"` + testPassword + `"},{"name":"bob","password":"b3K7rT2yU9wP1nM6dV8cX4sZ0fH5jQ_a"}]`
	c, e := Load(env(map[string]string{"TROJAN_PASSWORD": "", "TROJAN_USERS_JSON": raw}))
	if e != nil {
		t.Fatal(e)
	}
	if len(c.Users) != 2 {
		t.Fatal("expected two users")
	}
	duplicate := strings.ReplaceAll(raw, "bob", "alice")
	if _, e = Load(env(map[string]string{"TROJAN_PASSWORD": "", "TROJAN_USERS_JSON": duplicate})); e == nil {
		t.Fatal("duplicate names accepted")
	}
	duplicate = strings.ReplaceAll(raw, "b3K7rT2yU9wP1nM6dV8cX4sZ0fH5jQ_a", testPassword)
	if _, e = Load(env(map[string]string{"TROJAN_PASSWORD": "", "TROJAN_USERS_JSON": duplicate})); e == nil {
		t.Fatal("duplicate passwords accepted")
	}
}
func TestGeneratedPolicy(t *testing.T) {
	c, e := Load(env(nil))
	if e != nil {
		t.Fatal(e)
	}
	b, e := c.ServerJSON()
	if e != nil {
		t.Fatal(e)
	}
	var d map[string]any
	if e = json.Unmarshal(b, &d); e != nil {
		t.Fatal(e)
	}
	inbound := d["inbounds"].([]any)[0].(map[string]any)
	if inbound["listen"] != "127.0.0.1" || inbound["tls"] != nil {
		t.Fatal("core must be cleartext on loopback only")
	}
	rules := d["route"].(map[string]any)["rules"].([]any)
	if rules[3].(map[string]any)["action"] != "resolve" || rules[4].(map[string]any)["action"] != "reject" {
		t.Fatal("resolve must happen before IP rejection")
	}
	for _, address := range []string{"127.0.0.1", "10.0.0.1", "169.254.169.254", "100.100.100.200", "::1", "fd00:ec2::254", "64:ff9b::a9fe:a9fe", "::ffff:127.0.0.1"} {
		found := false
		for _, cidr := range BlockedCIDRs {
			if netip.MustParsePrefix(cidr).Contains(netip.MustParseAddr(address)) {
				found = true
			}
		}
		if !found {
			t.Fatalf("missing blocked address %s", address)
		}
	}
	for _, cidr := range BlockedCIDRs {
		if _, e := netip.ParsePrefix(cidr); e != nil {
			t.Fatal(e)
		}
	}
}
func TestPinnedCoreSchema(t *testing.T) {
	binary := os.Getenv("SING_BOX_TEST_BINARY")
	if binary == "" {
		t.Skip("set SING_BOX_TEST_BINARY to run the pinned core compatibility check")
	}
	c, e := Load(env(nil))
	if e != nil {
		t.Fatal(e)
	}
	b, _ := c.ServerJSON()
	p := filepath.Join(t.TempDir(), "config.json")
	if e = os.WriteFile(p, b, 0600); e != nil {
		t.Fatal(e)
	}
	output, e := exec.Command(binary, "check", "-c", p).CombinedOutput()
	if e != nil {
		t.Fatalf("core config incompatible: %v\n%s", e, output)
	}
}
