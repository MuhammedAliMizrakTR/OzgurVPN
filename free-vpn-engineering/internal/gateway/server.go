// SPDX-License-Identifier: GPL-3.0-or-later
package gateway

import (
	"context"
	"embed"
	"fmt"
	"html/template"
	"io/fs"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"sync"
	"time"

	"example.com/free-vpn-engineering/internal/config"
)

//go:embed web/*
var web embed.FS
var page = template.Must(template.ParseFS(web, "web/index.html"))

type Gate struct {
	cfg           config.Config
	ready         func() bool
	slots         chan struct{}
	limiter       *limiter
	proxy         *httputil.ReverseProxy
	connectionsMu sync.Mutex
	connections   map[*timedConn]struct{}
	closed        bool
}

func New(c config.Config, ready func() bool) *Gate {
	g := &Gate{cfg: c, ready: ready, slots: make(chan struct{}, c.MaxTunnels), limiter: newLimiter(c.HandshakesPerMinute, c.HandshakeBurst), connections: make(map[*timedConn]struct{})}
	target, _ := url.Parse(fmt.Sprintf("http://127.0.0.1:%d", c.CorePort))
	transport := &http.Transport{
		Proxy:             nil,
		DialContext:       (&net.Dialer{Timeout: 5 * time.Second, KeepAlive: 30 * time.Second}).DialContext,
		ForceAttemptHTTP2: false, DisableKeepAlives: true, ResponseHeaderTimeout: 10 * time.Second,
	}
	dial := transport.DialContext
	transport.DialContext = func(ctx context.Context, network, addr string) (net.Conn, error) {
		conn, err := dial(ctx, network, addr)
		if err != nil {
			return nil, err
		}
		tc := &timedConn{Conn: conn, idle: c.IdleTimeout, end: time.Now().Add(c.MaxAge)}
		tc.onClose = func() { g.connectionsMu.Lock(); delete(g.connections, tc); g.connectionsMu.Unlock() }
		g.connectionsMu.Lock()
		if g.closed {
			g.connectionsMu.Unlock()
			conn.Close()
			return nil, net.ErrClosed
		}
		g.connections[tc] = struct{}{}
		g.connectionsMu.Unlock()
		tc.touch()
		return tc, nil
	}
	g.proxy = &httputil.ReverseProxy{
		Rewrite: func(pr *httputil.ProxyRequest) {
			pr.SetURL(target)
			pr.Out.Host = target.Host
			// Never trust client-supplied forwarding headers or forward browser cookies.
			for _, h := range []string{"Forwarded", "X-Forwarded-For", "X-Forwarded-Host", "X-Forwarded-Proto", "X-Real-Ip", "Cookie", "Authorization"} {
				pr.Out.Header.Del(h)
			}
		},
		Transport: transport,
		ErrorHandler: func(w http.ResponseWriter, r *http.Request, err error) {
			http.Error(w, "Tunnel upstream unavailable", http.StatusBadGateway)
		},
	}
	return g
}

func (g *Gate) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("Referrer-Policy", "no-referrer")
	w.Header().Set("Content-Security-Policy", "default-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'")
	w.Header().Set("Cache-Control", "no-store")
	if r.URL.Path == g.cfg.WSPath {
		g.tunnel(w, r)
		return
	}
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		w.Header().Set("Allow", "GET, HEAD")
		http.Error(w, "Method not allowed", 405)
		return
	}
	switch r.URL.Path {
	case "/healthz":
		w.Header().Set("Content-Type", "application/json")
		if !g.ready() {
			w.WriteHeader(503)
			if r.Method != "HEAD" {
				fmt.Fprintln(w, `{"status":"not_ready"}`)
			}
			return
		}
		if r.Method != "HEAD" {
			fmt.Fprintln(w, `{"status":"ok","core":"ready"}`)
		}
	case "/":
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		if r.Method == "HEAD" {
			return
		}
		ports := make([]string, len(g.cfg.EgressPorts))
		for i, p := range g.cfg.EgressPorts {
			ports[i] = fmt.Sprint(p)
		}
		_ = page.Execute(w, map[string]any{"Ports": strings.Join(ports, " / "), "MaxTunnels": g.cfg.MaxTunnels})
	case "/robots.txt":
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		if r.Method != "HEAD" {
			fmt.Fprint(w, "User-agent: *\nDisallow: /\n")
		}
	case "/assets/style.css", "/assets/status.js":
		sub, _ := fs.Sub(web, "web")
		if strings.HasSuffix(r.URL.Path, ".css") {
			w.Header().Set("Content-Type", "text/css; charset=utf-8")
		} else {
			w.Header().Set("Content-Type", "text/javascript; charset=utf-8")
		}
		b, _ := fs.ReadFile(sub, strings.TrimPrefix(r.URL.Path, "/assets/"))
		if r.Method != "HEAD" {
			_, _ = w.Write(b)
		}
	default:
		http.NotFound(w, r)
	}
}

func headerHasToken(value, token string) bool {
	for _, v := range strings.Split(value, ",") {
		if strings.EqualFold(strings.TrimSpace(v), token) {
			return true
		}
	}
	return false
}
func (g *Gate) tunnel(w http.ResponseWriter, r *http.Request) {
	if r.Method != "GET" || r.URL.RawQuery != "" || r.URL.ForceQuery {
		http.NotFound(w, r)
		return
	}
	if !headerHasToken(r.Header.Get("Connection"), "upgrade") || !strings.EqualFold(r.Header.Get("Upgrade"), "websocket") {
		w.Header().Set("Upgrade", "websocket")
		http.Error(w, "WebSocket upgrade required", 426)
		return
	}
	if !g.ready() {
		http.Error(w, "Service not ready", 503)
		return
	}
	if !g.limiter.allow() {
		w.Header().Set("Retry-After", "2")
		http.Error(w, "Handshake rate exceeded", 429)
		return
	}
	select {
	case g.slots <- struct{}{}:
		defer func() { <-g.slots }()
	default:
		w.Header().Set("Retry-After", "5")
		http.Error(w, "Tunnel capacity reached", 503)
		return
	}
	g.proxy.ServeHTTP(w, r)
}

// CloseTunnels closes upgraded connections, which http.Server.Shutdown does not.
func (g *Gate) CloseTunnels() {
	g.connectionsMu.Lock()
	g.closed = true
	all := make([]*timedConn, 0, len(g.connections))
	for c := range g.connections {
		all = append(all, c)
	}
	g.connectionsMu.Unlock()
	for _, c := range all {
		_ = c.Close()
	}
}

type timedConn struct {
	net.Conn
	idle    time.Duration
	end     time.Time
	once    sync.Once
	onClose func()
}

func (c *timedConn) touch() {
	t := time.Now().Add(c.idle)
	if t.After(c.end) {
		t = c.end
	}
	_ = c.Conn.SetDeadline(t)
}
func (c *timedConn) Read(b []byte) (int, error) {
	c.touch()
	n, e := c.Conn.Read(b)
	if n > 0 {
		c.touch()
	}
	return n, e
}
func (c *timedConn) Write(b []byte) (int, error) {
	c.touch()
	n, e := c.Conn.Write(b)
	if n > 0 {
		c.touch()
	}
	return n, e
}
func (c *timedConn) Close() error {
	err := c.Conn.Close()
	c.once.Do(func() {
		if c.onClose != nil {
			c.onClose()
		}
	})
	return err
}

type limiter struct {
	mu                          sync.Mutex
	tokens, capacity, perSecond float64
	last                        time.Time
}

func newLimiter(perMinute, burst int) *limiter {
	return &limiter{tokens: float64(burst), capacity: float64(burst), perSecond: float64(perMinute) / 60, last: time.Now()}
}
func (l *limiter) allow() bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	now := time.Now()
	l.tokens += now.Sub(l.last).Seconds() * l.perSecond
	l.last = now
	if l.tokens > l.capacity {
		l.tokens = l.capacity
	}
	if l.tokens < 1 {
		return false
	}
	l.tokens--
	return true
}
