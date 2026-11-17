> **TARİHSEL KANIT:** bu rapor ilk prototip oturumunun sonucudur; yeni devir kontrolleri `../../DEVIR_TEST_SONUCLARI.json` içindedir. Güncel VDS, Docker, Render veya TUN kabulü değildir.

# Doğrulama raporu — 14 Kasım 2026

## Test edilen ortam

- Kaynak: bu paketteki Go gateway + scripts/tests.
- Platform: Linux amd64; Go 1.27.4; Python 3.13.18.
- Resmi sing-box: **1.14.4**, CGO kapalı resmi release binary'si.
- Binary arşivi indirilip `versions.json` içindeki SHA-256 ile doğrulandı.
- Zaman: `2026-11-14T10:21:01+00:00`.
- Testler için rastgele parolalar, geçici sertifika ve özel config dosyaları
  kullanıldı. Hepsi test sonunda silindi; pakette gerçek kullanıcı sırrı yok.

## Birim ve statik kontroller

| Kontrol | Sonuç |
|---|---|
| `go test -race -cover ./...` | PASS |
| `internal/config` statement coverage | %93,5 |
| `internal/gateway` statement coverage | %92,4 |
| `cmd/gateway` doğrudan Go unit coverage | %0; serve/lifecycle ayrı E2E ile çalıştırıldı |
| `go vet ./...` | PASS |
| Python unittest | 12 test PASS |
| Python py_compile | PASS |
| `node --check internal/gateway/web/status.js` | PASS |
| Render / Compose / Actions YAML sözdizimi | Parse başarılı; platform şema/deploy onayı değildir |
| Core server/client şeması | Gerçek pinned binary ile `sing-box check` PASS |
| `.env`, çoklu kullanıcı ve istemci CLI akışı | Geçici dizinde PASS |
| HTTP `/`, `/healthz`, CSS ve JS uçları | Geliştirme servisinde 200 |

## Gerçek WSS testi

Yerelde Render benzeri **TLS sonlandırıcı → Go HTTP/WS → gerçek sing-box
sunucu** ve **gerçek sing-box istemci** çalıştırıldı. İstemci geçici yerel CA'yı
açıkça güvenilir sertifika olarak aldı; `insecure=true` kullanılmadı. Pozitif
testler public `example.com` ve Cloudflare DoH kullanır.

1. PASS — gateway readiness + real core listener
2. PASS — generated client JSON accepted by pinned sing-box core
3. PASS — HTTP → Trojan/WSS → public HTTP
4. PASS — HTTP CONNECT → Trojan/WSS → public HTTPS
5. PASS — SOCKS5h → Trojan/WSS → public HTTPS
6. PASS — wrong Trojan password rejected
7. PASS — untrusted TLS certificate rejected (no insecure mode)
8. PASS — wrong WebSocket path rejected
9. PASS — loopback target blocked, even on an allowed custom port
10. PASS — cloud metadata IPv4 target blocked
11. PASS — private IPv4 target blocked
12. PASS — loopback IPv6 target blocked
13. PASS — IPv4-mapped IPv6 loopback target blocked
14. PASS — disallowed destination port blocked
15. PASS — private hostname blocked
16. PASS — private HTTP sink received zero requests
17. PASS — DNS rebinding fixture resolves to loopback
18. PASS — domain resolving to private IP is blocked
19. PASS — public gateway is not an open HTTP CONNECT proxy
20. PASS — global handshake token bucket returns 429 under burst
21. PASS — generated passwords are absent from process logs
22. PASS — core child is tracked for lifecycle assertions
23. PASS — SIGTERM shuts down gateway cleanly
24. PASS — SIGTERM leaves no core child behind
25. PASS — unexpected core exit fails the gateway instead of reporting healthy

**Toplam: 25 başarılı uçtan uca kontrol.**

Bu test seti belirli saldırı yüzeylerini kontrol eder; tam penetrasyon testi,
tüm DNS rebinding varyasyonları veya bağımsız güvenlik denetimi değildir.

## Yapılmayanlar — bunlar başarılı diye sunulmuyor

- Bu çalışma alanında Docker daemon/CLI yoktu. **Container imajı build edilmedi**;
  `tests/docker_smoke.py` burada çalıştırılmadı. CI bunları ayrıca çalıştıracak
  şekilde yazıldı; GitHub üzerinde henüz bir workflow çalıştırılmadı.
- Docker base image manifest digest'leri ve amd64/arm64 platform kayıtları
  registry üzerinden doğrulandı. Bu, imaj build testinin yerine geçmez.
- Render hesabında servis oluşturulmadı; gerçek ingress, cold-start, outbound
  kısıtları, faturalama ve AUP uygunluğu doğrulanmadı.
- GitHub reposu oluşturulmadı veya herhangi bir remote'a push yapılmadı.
- arm64 binary çalıştırma, gerçek mobil/masaüstü TUN, UDP, yük/throughput,
  tarayıcı görsel regresyonu ve uzun süreli kesintisizlik testi yapılmadı.
- Halka açık ücretsiz hizmet, kalıcı kullanıcı kotası veya no-logs garantisi yok.

## Tekrarlama

```bash
make test
make e2e
# Docker olan bir ortamda ayrıca:
docker build -t ozgurag:ci .
python3 tests/docker_smoke.py --image ozgurag:ci
```

Makine tarafından okunabilir aynı snapshot: `docs/e2e-results.json`.
