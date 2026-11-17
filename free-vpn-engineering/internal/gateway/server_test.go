package gateway

import (
	"bufio"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strconv"
	"strings"
	"testing"
	"time"

	"example.com/free-vpn-engineering/internal/config"
)

func fixture(t *testing.T) config.Config {
	t.Helper()
	c, e := config.Load(func(k string) string {
		if k == "TROJAN_PASSWORD" {
			return "H9c4xV7mK1pT5nR8yQ2wZ6dB3fS0jL_a"
		}
		return ""
	})
	if e != nil {
		t.Fatal(e)
	}
	return c
}
func TestHTTPRoutes(t *testing.T) {
	for _, tc := range []struct {
		method, path string
		ready        bool
		code         int
	}{
		{"GET", "/", true, 200}, {"HEAD", "/", true, 200}, {"GET", "/healthz", true, 200}, {"GET", "/healthz", false, 503},
		{"POST", "/", true, 405}, {"CONNECT", "example.com:443", true, 405}, {"GET", "/missing", true, 404},
		{"GET", "/assets/style.css", true, 200}, {"GET", "/assets/status.js", true, 200}, {"GET", "/robots.txt", true, 200},
		{"GET", "/tunnel", true, 426}, {"GET", "/tunnel?x=y", true, 404},
	} {
		t.Run(tc.method+tc.path, func(t *testing.T) {
			c := fixture(t)
			g := New(c, func() bool { return tc.ready })
			defer g.CloseTunnels()
			w := httptest.NewRecorder()
			r := httptest.NewRequest(tc.method, tc.path, nil)
			g.ServeHTTP(w, r)
			if w.Code != tc.code {
				t.Fatalf("got %d want %d", w.Code, tc.code)
			}
			if strings.Contains(w.Body.String(), c.Users[0].Password) {
				t.Fatal("password in HTTP response")
			}
			if tc.method == "HEAD" && w.Body.Len() != 0 {
				t.Fatal("HEAD body must be empty")
			}
			if w.Header().Get("X-Frame-Options") != "" || strings.Contains(w.Header().Get("Content-Security-Policy"), "frame-ancestors") {
				t.Fatal("must permit live-preview embedding")
			}
		})
	}
}
func TestGlobalCapacity(t *testing.T) {
	c := fixture(t)
	c.MaxTunnels = 1
	g := New(c, func() bool { return true })
	defer g.CloseTunnels()
	g.slots <- struct{}{}
	r := httptest.NewRequest("GET", c.WSPath, nil)
	r.Header.Set("Connection", "keep-alive, Upgrade")
	r.Header.Set("Upgrade", "websocket")
	w := httptest.NewRecorder()
	g.ServeHTTP(w, r)
	if w.Code != 503 || w.Header().Get("Retry-After") == "" {
		t.Fatal("capacity not enforced")
	}
}
func TestTokenBucket(t *testing.T) {
	l := newLimiter(60, 2)
	if !l.allow() || !l.allow() || l.allow() {
		t.Fatal("burst limit not enforced")
	}
	l.last = time.Now().Add(-time.Minute)
	if !l.allow() {
		t.Fatal("bucket not replenished")
	}
}
func TestWebsocketProxyAndShutdown(t *testing.T) {
	observed := make(chan bool, 1)
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		observed <- r.URL.Path == "/tunnel" && r.Header.Get("X-Forwarded-For") == "" && r.Header.Get("Cookie") == "" && r.Header.Get("Authorization") == ""
		conn, b, e := w.(http.Hijacker).Hijack()
		if e != nil {
			return
		}
		defer conn.Close()
		fmt.Fprint(b, "HTTP/1.1 101 Switching Protocols\r\nConnection: Upgrade\r\nUpgrade: websocket\r\n\r\n")
		_ = b.Flush()
		_, _ = io.Copy(conn, conn)
	}))
	defer upstream.Close()
	c := fixture(t)
	u, _ := url.Parse(upstream.URL)
	_, p, _ := net.SplitHostPort(u.Host)
	c.CorePort, _ = strconv.Atoi(p)
	g := New(c, func() bool { return true })
	front := httptest.NewServer(g)
	defer front.Close()
	defer g.CloseTunnels()
	f, _ := url.Parse(front.URL)
	conn, e := net.Dial("tcp", f.Host)
	if e != nil {
		t.Fatal(e)
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(3 * time.Second))
	fmt.Fprintf(conn, "GET /tunnel HTTP/1.1\r\nHost: test\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nX-Forwarded-For: forged\r\nCookie: secret\r\nAuthorization: secret\r\n\r\n")
	reader := bufio.NewReader(conn)
	resp, e := http.ReadResponse(reader, nil)
	if e != nil {
		t.Fatal(e)
	}
	if resp.StatusCode != 101 {
		t.Fatalf("got %d", resp.StatusCode)
	}
	if !<-observed {
		t.Fatal("proxy routing or header sanitization failed")
	}
	if _, e = conn.Write([]byte("ping")); e != nil {
		t.Fatal(e)
	}
	b := make([]byte, 4)
	if _, e = io.ReadFull(reader, b); e != nil || string(b) != "ping" {
		t.Fatalf("bidirectional relay failed: %v", e)
	}
	g.CloseTunnels()
	_ = conn.SetReadDeadline(time.Now().Add(time.Second))
	if _, e = reader.ReadByte(); e == nil {
		t.Fatal("shutdown did not close upgraded connection")
	}
}
func TestTunnelTimeouts(t *testing.T) {
	for _, tc := range []struct {
		name      string
		idle, age time.Duration
	}{{"idle", 20 * time.Millisecond, time.Second}, {"max-age", time.Second, 20 * time.Millisecond}} {
		t.Run(tc.name, func(t *testing.T) {
			a, b := net.Pipe()
			defer a.Close()
			defer b.Close()
			c := &timedConn{Conn: a, idle: tc.idle, end: time.Now().Add(tc.age)}
			_, e := c.Read(make([]byte, 1))
			ne, ok := e.(net.Error)
			if !ok || !ne.Timeout() {
				t.Fatalf("expected deadline, got %v", e)
			}
		})
	}
}
