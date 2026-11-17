// SPDX-License-Identifier: GPL-3.0-or-later
package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strconv"
	"sync/atomic"
	"syscall"
	"time"

	"example.com/free-vpn-engineering/internal/config"
	"example.com/free-vpn-engineering/internal/gateway"
)

func main() {
	log.SetFlags(log.LstdFlags | log.LUTC)
	command := "serve"
	if len(os.Args) > 1 {
		command = os.Args[1]
	}
	var err error
	switch command {
	case "serve":
		err = serve()
	case "check-env":
		_, err = config.Load(os.Getenv)
		if err == nil {
			fmt.Println("Environment valid; no secrets printed.")
		}
	case "healthcheck":
		err = healthcheck()
	case "version":
		fmt.Println("Ozgur Ag Gateway 1.0.0")
	default:
		err = errors.New("usage: vpn-gateway [serve|check-env|healthcheck|version]")
	}
	if err != nil {
		log.Print(err)
		os.Exit(1)
	}
}

func healthcheck() error {
	port := os.Getenv("PORT")
	if port == "" {
		port = "10000"
	}
	n, e := strconv.Atoi(port)
	if e != nil || n < 1024 || n > 65535 {
		return errors.New("invalid PORT")
	}
	client := &http.Client{Timeout: 2 * time.Second, Transport: &http.Transport{Proxy: nil}}
	resp, e := client.Get(fmt.Sprintf("http://127.0.0.1:%d/healthz", n))
	if e != nil {
		return errors.New("gateway not reachable")
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return errors.New("gateway not ready")
	}
	return nil
}

type coreProcess struct {
	cmd  *exec.Cmd
	done chan struct{}
	err  error
}

func (p *coreProcess) stop() {
	select {
	case <-p.done:
		return
	default:
	}
	_ = p.cmd.Process.Signal(syscall.SIGTERM)
	select {
	case <-p.done:
	case <-time.After(5 * time.Second):
		_ = p.cmd.Process.Kill()
		<-p.done
	}
}
func coreListening(port int) bool {
	c, e := net.DialTimeout("tcp", fmt.Sprintf("127.0.0.1:%d", port), 250*time.Millisecond)
	if e != nil {
		return false
	}
	_ = c.Close()
	return true
}
func serve() error {
	c, err := config.Load(os.Getenv)
	if err != nil {
		return err
	}
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()
	dir, err := os.MkdirTemp("", "ozgurag-")
	if err != nil {
		return errors.New("cannot create runtime directory")
	}
	defer os.RemoveAll(dir)
	raw, err := c.ServerJSON()
	if err != nil {
		return errors.New("cannot generate core configuration")
	}
	configPath := filepath.Join(dir, "sing-box.json")
	if err = os.WriteFile(configPath, raw, 0600); err != nil {
		return errors.New("cannot write private runtime configuration")
	}
	check := exec.CommandContext(ctx, c.CoreBinary, "check", "-c", configPath)
	if _, err = check.CombinedOutput(); err != nil {
		return errors.New("sing-box configuration check failed; verify the pinned core binary and version")
	}
	cmd := exec.Command(c.CoreBinary, "run", "-c", configPath)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	// Do not propagate the original secret environment variables to the child.
	for _, entry := range os.Environ() {
		if len(entry) >= 16 && entry[:16] == "TROJAN_PASSWORD=" {
			continue
		}
		if len(entry) >= 18 && entry[:18] == "TROJAN_USERS_JSON=" {
			continue
		}
		cmd.Env = append(cmd.Env, entry)
	}
	if err = cmd.Start(); err != nil {
		return errors.New("cannot start sing-box")
	}
	child := &coreProcess{cmd: cmd, done: make(chan struct{})}
	go func() { child.err = cmd.Wait(); close(child.done) }()
	defer child.stop()
	deadline := time.NewTimer(10 * time.Second)
	defer deadline.Stop()
	ticker := time.NewTicker(50 * time.Millisecond)
	defer ticker.Stop()
	waiting := true
	for waiting {
		select {
		case <-ctx.Done():
			return nil
		case <-child.done:
			return errors.New("sing-box exited during startup")
		case <-deadline.C:
			return errors.New("sing-box did not become ready within 10 seconds")
		case <-ticker.C:
			waiting = !coreListening(c.CorePort)
		}
	}
	var ready atomic.Bool
	ready.Store(true)
	gate := gateway.New(c, func() bool { return ready.Load() && coreListening(c.CorePort) })
	server := &http.Server{Addr: fmt.Sprintf("0.0.0.0:%d", c.Port), Handler: gate, ReadHeaderTimeout: 10 * time.Second, IdleTimeout: 60 * time.Second, MaxHeaderBytes: 16 << 10}
	httpErr := make(chan error, 1)
	go func() { httpErr <- server.ListenAndServe() }()
	log.Printf("gateway ready; public_port=%d users=%d max_tunnels=%d; access logging disabled", c.Port, len(c.Users), c.MaxTunnels)
	var result error
	select {
	case <-ctx.Done():
	case <-child.done:
		result = errors.New("sing-box exited unexpectedly")
	case e := <-httpErr:
		if !errors.Is(e, http.ErrServerClosed) {
			result = fmt.Errorf("HTTP server stopped: %w", e)
		}
	}
	ready.Store(false)
	gate.CloseTunnels()
	shutdown, stop := context.WithTimeout(context.Background(), 5*time.Second)
	defer stop()
	if e := server.Shutdown(shutdown); e != nil {
		_ = server.Close()
	}
	child.stop()
	return result
}
