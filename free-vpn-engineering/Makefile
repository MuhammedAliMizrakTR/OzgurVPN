.PHONY: test core build e2e docker
GO ?= go
core:
	python3 scripts/fetch_core.py --dest .cache/sing-box
build:
	$(GO) build -trimpath -o .cache/vpn-gateway ./cmd/gateway
test:
	$(GO) test -race -cover ./...
	$(GO) vet ./...
	python3 -m unittest discover -s tests -p 'test_*.py' -v
e2e: build core
	python3 tests/e2e.py --gateway .cache/vpn-gateway --core .cache/sing-box
docker:
	docker compose up --build -d
