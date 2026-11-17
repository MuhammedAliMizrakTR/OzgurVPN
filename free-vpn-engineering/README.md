> **DEVİR NOTU — ARŞİV PROTOTİP.** Bu klasör eski Trojan/WSS **uygulama proxy'si** denemesidir; cihaz geneli VPN/TUN değildir ve mevcut VDS'ye kurulmayacaktır. Güncel hedef Docker S-UI + doğrudan Trojan/TLS; başlangıç belgesi [kök README](../README.md). Aşağıdaki test/deploy ifadeleri kendi tarihsel kapsamındadır. Bu birleşik repoda `.github/workflows/` kökte olmadığından buradaki Actions dosyaları otomatik çalışmaz. Docker/Render dağıtımı yapılmış sayılmaz.

# Özgür Ağ — VPN Engineering

**sing-box 1.14.4 · Trojan-over-WSS · Docker · Render Blueprint · Go gateway**

HTTP/HTTPS ve SOCKS trafiğini kendi kimlik doğrulamalı geçidine taşıyan, kaynak kodu açık bir mühendislik prototipi. İstemcide HTTP/SOCKS proxy, sunucuda Trojan-over-WebSocket kullanır. Render için dış TLS sonlandırmasıyla tasarlanmıştır; aynı container uygun bir TLS reverse proxy arkasında başka bir sağlayıcıda da çalıştırılabilir.

> **Önemli kapsam ve izin sınırı:** Bu paket, Render Free üzerinde “herkese sınırsız ve sürekli açık VPN” hizmeti vaat etmez. Render AUP'nin 3, 7 ve 9. maddeleri; kapasite/kullanım kısıtlarını aşma, üçüncü kişilere hizmet sağlama ve ağ kısıtlarını aşma hedefleri açısından engel oluşturabilir. Proxy/VPN kullanımın için sağlayıcıdan uygunluğu doğrulamadan Render'a dağıtma. Ücretli plana geçmek kullanım politikasını ortadan kaldırmaz. Uyku bypass, hesap/kota çoğaltma veya sahte repo aktivitesi **eklenmedi**. [1](https://render.com/acceptable-use)

## Teslim durumu

| Bileşen | Durum |
|---|---|
| Go geçidi + gerçek sing-box istemci/sunucusu | Yerel ortamda derlendi ve çalıştırıldı |
| Gerçek HTTP, HTTPS CONNECT ve SOCKS5h → WSS akışı | Başarılı |
| Parola, TLS, private IP, metadata, DNS-private, kapanış testleri | 25 uçtan uca kontrol başarılı |
| Go birim testleri / race detector / vet | Başarılı |
| Python yardımcıları | 12 birim testi başarılı |
| Dockerfile / Compose / Render / Actions dosyaları | Hazır; container build ve Render deploy bu ortamda yapılmadı |
| GitHub reposu oluşturma / Render hesabına işlem | Yapılmadı; dosyaları kendi hesabına yüklemelisin |
| Herkese açık üyelik, kalıcı kota, tam cihaz VPN/TUN | Bu MVP'de yok |

Ayrıntı: [`docs/TEST_RESULTS.md`](docs/TEST_RESULTS.md). Çalışma alanındaki canlı önizleme, geçici bir geliştirme servisi; kalıcı Render dağıtımı veya kullanıcılara sunulmuş bir VPN değildir.

## 1. Trafik akışı

```text
Tarayıcı / curl / proxy destekleyen uygulama
       │ HTTP proxy veya SOCKS5h — 127.0.0.1:1080
       ▼
Cihazdaki sing-box istemcisi
       │ Trojan + WebSocket + doğrulanan TLS
       ▼
Render HTTPS :443                 ← dış TLS burada sonlanır
       │ HTTP / WebSocket
       ▼
Go gateway — 0.0.0.0:$PORT         ← /, /healthz ve WS yolu
       │ yalnızca container loopback
       ▼
sing-box — 127.0.0.1:$CORE_PORT   ← kullanıcı parolası + çıkış politikası
       │ yalnızca public hedefler, varsayılan TCP 80/443
       ▼
İnternet
```

Render bir web servisine tek public HTTP portu yönlendirir ve dış TLS'i kendisi sonlandırır. Bu yüzden ham Trojan/TCP yerine **Trojan-over-WSS** kullanılır. Ayrı bir public SOCKS veya HTTP CONNECT portu açılmaz. [1](https://render.com/docs/web-services)

**Bu bir uygulama proxy'sidir:** yalnızca proxy'ye yönlendirdiğin uygulamaların TCP trafiği tünellenir. İşletim sisteminin tüm trafiğini, DNS'ini veya UDP/QUIC trafiğini otomatik taşımaz. `TUN`, `NET_ADMIN` ya da privileged container gerektirmez.

## 2. Yerelde başlat — önce bunu dene

Gereksinimler: Docker + Compose v2, Python 3.10+ ve cihazında resmi **sing-box 1.14.4**. Go yalnızca kaynak kodunu container dışında derlemek/test etmek için gerekir.

Proje klasöründe:

```bash
# Rastgele parola + WS yolu içeren özel .env oluşturur; parolayı yazdırmaz.
python3 scripts/init_env.py

# İmajı derler ve yalnızca localhost'a yayınlar.
docker compose up --build -d

# Hazırlık kontrolü. Beklenen JSON: {"status":"ok","core":"ready"}
curl --fail http://127.0.0.1:10000/healthz
```

Aynı makinede istemci yapılandırmasını üret:

```bash
python3 scripts/client.py \
  --server 127.0.0.1 \
  --local-plaintext \
  --env-file .env \
  --output clients/local.json

sing-box check -c clients/local.json
sing-box run -c clients/local.json
```

Başka bir terminalde:

```bash
# NO_PROXY ayarlarının testi atlamaması için --noproxy '' kullanılır.
curl --noproxy '' --fail --proxy http://127.0.0.1:1080 https://example.com
curl --noproxy '' --fail --proxy socks5h://127.0.0.1:1080 https://example.com
```

- `--local-plaintext`, **yalnızca loopback** için çalışır. Uzak bir sunucuda TLS'i kapatmaz.
- Compose, cleartext origin'i `127.0.0.1:10000` adresine bağlar. Bunu `0.0.0.0` yapıp TLS olmadan internete açma.
- `.env`, `clients/` ve `secrets/` hem Git hem Docker build bağlamından hariçtir.
- Dosyalar mevcutsa yardımcılar üzerine yazmaz. Rotasyonda önce yedekle veya yeni `--output` seç.
- Kapatma: `docker compose down`.

## 3. Render'a dağıt — yalnızca uygun kullanım izniyle

1. **Önce sağlayıcı uygunluğunu doğrula.** Kişisel bir demo olması otomatik izin anlamına gelmez. [1](https://render.com/acceptable-use)
2. Bu kaynak dosyalarını kendi GitHub repona yükle. `.env` veya üretilen istemci dosyalarını ekleme.
3. İlk CI testlerini çalıştır. Render Dashboard → **New → Blueprint** ile repoyu seç.
4. `render.yaml` bir Docker Web Service tanımlar: `free`, `frankfurt`, tek public port `10000`, sağlık yolu `/healthz`. Sonraki otomatik dağıtımlar `checksPass` ile CI kontrollerini bekler. İlk dağıtımı ayrıca takip et. [1](https://render.com/docs/blueprint-spec)
5. Render, `TROJAN_PASSWORD` için rastgele bir sır üretir. **Environment** bölümünden özel olarak al; loga, ekran görüntüsüne veya repoya koyma. Varsayılan `WS_PATH=/tunnel`.
6. Deploy tamamlandıktan sonra servis ana sayfasını ve `/healthz` JSON'unu kontrol et.
7. Kendi cihazında istemciyi üret. `SERVIS_ADIN` yerine Render'ın verdiği gerçek servis adını yaz:

```bash
python3 scripts/client.py \
  --server SERVIS_ADIN.onrender.com \
  --output clients/render.json
# Parola gizli girişle sorulur; komut satırına açık parola yazılmaz.

sing-box check -c clients/render.json
sing-box run -c clients/render.json
```

Özel WS yolu kullandıysan `--ws-path /secilen-yol` ekle. İstemci uzak sunucularda TLS sertifikasını doğrular; `insecure: false` varsayılanını değiştirme.

Tarayıcıya HTTP proxy `127.0.0.1:1080` veya SOCKS5 `127.0.0.1:1080` ayarla. SOCKS kullanırken uzak DNS çözümlemesini aç; CLI'da bunun karşılığı `socks5h://`.

> **Soğuk başlangıç:** Free instance 15 dakika gelen trafik almazsa uyuyabilir; yeni HTTP/WebSocket isteğiyle uyanması yaklaşık bir dakika sürer. Mevcut TCP oturumu bu sırada korunmaz. Gerekirse ana sayfayı açıp `/healthz` geçerli JSON döndükten sonra yeni bağlantı dene. Her isteğin ilk seferde çalışması garanti değildir. [1](https://render.com/docs/free)

## 4. Kullanıcılar: ortak parola yerine ayrı sırlar

Tek kullanıcıda yalnızca `TROJAN_PASSWORD` kullanılır. Kontrollü/davetli testte her kullanıcıya ayrı parola üretilebilir:

```bash
python3 scripts/users.py --names owner,friend --output secrets/users.json
```

Operatör olarak dosyanın JSON içeriğini Render'ın **özel** `TROJAN_USERS_JSON` ortam değişkenine aktar ve `TROJAN_PASSWORD` değişkenini kaldır. İkisi aynı anda tanımlıysa servis açılmaz. JSON en çok 64 benzersiz isim/parola kabul eder.

Her kullanıcı için **ayrı** istemci üret:

```bash
python3 scripts/client.py \
  --server SERVIS_ADIN.onrender.com \
  --users-file secrets/users.json \
  --user friend \
  --output clients/friend.json
```

Yalnızca ilgili `clients/friend.json` dosyasını güvenli kanaldan o kullanıcıya ver. `users.json`, diğer istemciler veya Render parolasının tamamı paylaşılmaz. Kullanıcıyı iptal etmek için env listesinden çıkarıp yeniden deploy et; mevcut bağlantıların kapanmasını doğrula. Bu işlem kalıcı kota, self-service üyelik veya gerçek zamanlı kullanıcı yönetimi değildir.

## 5. Varsayılan güvenlik ve sınırlar

| Ayar / davranış | Varsayılan |
|---|---|
| Public HTTP portu | `PORT=10000`; `0.0.0.0` üzerinde |
| Core WS portu | `CORE_PORT=10001`; **yalnızca 127.0.0.1** |
| Kimlik doğrulaması | Zorunlu, kullanıcı başına ayrı Trojan parolası |
| Çıkış | `EGRESS_TCP_PORTS=80,443`; UDP/ICMP reddedilir |
| Özel/hedef koruması | Private, loopback, link-local, metadata, reserved CIDR engeli |
| DNS-private koruması | Domain önce public DoH ile çözülür, sonra IP kuralı uygulanır |
| DNS | Sunucuda Cloudflare DoH; domain hedefleri IPv4 çözülür |
| Global eşzamanlı tünel | `MAX_TUNNELS=16` |
| Global handshake hızı | Dakikada 60; anlık burst 20 |
| Trafiksiz tünel zaman aşımı | `TUNNEL_IDLE_TIMEOUT=2m` |
| Bir tünelin azami ömrü | `TUNNEL_MAX_AGE=30m` |
| Container | UID/GID 10001; Compose'ta salt-okunur kök, capabilities yok |
| Çekirdek konfigürasyonu | Geçici dizinde 0600; başlangıçta üretilir, çıkışta silinir |
| Çekirdek indirimi | Resmi 1.14.4 arşivi; amd64/arm64 SHA-256 lock |

**Dürüst sınırlar:**

- TCP 80/443 filtresi bir HTTP içerik denetleyicisi değildir; o porttaki başka protokolleri tanımaz.
- Global tünel/handshake sınırı **kullanıcı başına hız veya aylık GB kotası değildir**.
- Süre/bağlantı sayaçları restart sonrası sıfırlanır. Kalıcı kota için harici dayanıklı depolama gerekir.
- Azami ömre ulaşan aktif tünel de kapanır; sürmekte olan indirmeler kesilebilir. Yeni bağlantılar yeniden kurulur.
- Uygulama seviyesindeki hedef kuralları tek başına sert bir ağ firewall'u değildir.
- Bu proje bağımsız güvenlik denetiminden geçmedi. “Anonim”, “no-logs”, “DNS sızıntısız” veya sansür altında erişilebilirlik garantisi vermez.
- Render dış TLS'i sonlandırır; sağlayıcıya güvenmek gerekir. HTTP hedeflerinin içeriği TLS hedefleri gibi uçtan uca korunmaz. Hedef sitelerde HTTPS kullan.
- HTTP erişim logu kapalıdır; **sing-box hata logları hedef adres, kullanıcı veya bağlantı bilgisi içerebilir**. Sağlayıcı logları için ayrıca politika gerekir.

Tehdit modeli: [`SECURITY.md`](SECURITY.md).

## 6. GitHub Actions: test ve isteğe bağlı gözlem

### `ci.yml`

Go race/unit/vet, Python testleri, gerçek sing-box ile TLS'li uçtan uca testler, Docker build ve non-root/read-only container smoke testi. Minimum `contents: read` izni; üçüncü taraf Actions commit SHA ile sabitlenmiştir. E2E için public internet, `example.com` ve Cloudflare DoH gerekir; bu servislerin kesintisi CI'ı da etkileyebilir.

### `health.yml`

Varsayılan olarak **istek göndermez**. Actions → Variables altında:

- `SERVICE_URL`: `https://SERVIS_ADIN.onrender.com`
- `ENABLE_HEALTH_MONITOR`: `true` — yalnızca planlı kontrol isteniyorsa

Etkinleştirilirse **6 saatte bir** hazırlık kontrolü yapar; elle de çalıştırılabilir. Uyuyan servisi uyandırabilir. Yapay sürekli trafik, anti-sleep döngüsü veya otomatik “keep-alive commit” içermez. `/healthz`, yalnızca gateway ve core dinleyicisinin hazırlığını ölçer; parola ve internet çıkışını uçtan uca test etmez.

Actions schedule işleri gecikebilir/atlanabilir; bu bir SLA veya kesintisizlik mekanizması değildir. [1](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)

## 7. Testleri kendin çalıştır

Gereksinimler: Go **1.27.4**, Python 3.10+, Linux, `curl`, `openssl`.

```bash
make test
make e2e
```

Çekirdek şema kontrolünü de Go testlerine dahil etmek için:

```bash
python3 scripts/fetch_core.py --dest .cache/sing-box
SING_BOX_TEST_BINARY="$PWD/.cache/sing-box" go test -race -cover ./...
```

Container testi:

```bash
docker build -t ozgurag:ci .
python3 tests/docker_smoke.py --image ozgurag:ci
```

`versions.json` ve Docker base digest'leri 14 Kasım 2026 tarihinde kilitlendi. Güncellemelerde arşiv hash'lerini resmi kaynaktan tekrar doğrula ve tüm testleri çalıştır. Hash kilidi, değişmeyen artifact kontrolüdür; resmi imza doğrulamasının veya tam tedarik zinciri denetiminin yerine geçmez. `apk` paketleri ayrıca sabitlenmediği için bit-bit yeniden üretilebilir build iddiası yoktur.

## 8. Sorun giderme

| Belirti | Kontrol |
|---|---|
| Deploy port bulunamıyor | HTTP portu `PORT` ile aynı mı, dinleme `0.0.0.0` mı? |
| `configuration check failed` | Resmi 1.14.4 binary ve doğru mimari mi? |
| WS `404` | İstemcideki yol ile `WS_PATH` birebir aynı mı? |
| WS `426` | Tünel yoluna düz HTTP yerine WS upgrade gerekir |
| WS `429` | Global handshake limiti; anında tekrar deneme fırtınası yapma |
| WS `503` | Servis hazır değil veya global tünel kapasitesi dolu |
| `bad request: fallback disabled` | Yanlış parola ya da geçersiz Trojan verisi; fallback bilerek kapalı |
| Sertifika hatası | Gerçek hostname/SNI doğru mu? `insecure=true` ile geçiştirme |
| Sadece bazı hedefler çalışmıyor | Varsayılan yalnızca public TCP 80/443; UDP, SMTP ve private hedefler kapalı |
| İlk bağlantı başarısız | Free instance soğuk başlangıcı ve `/healthz` JSON'u |
| 30 dakika sonra kopma | `TUNNEL_MAX_AGE` tasarım gereği; aktif TCP akışı da kapanır |
| Ücretsiz servis askıya alındı | Dashboard saat/bant genişliği, AUP ve service-initiated traffic uyarıları |

## 9. “Free VPN for all” için bir sonraki aşama

Önce kullanım izni ve sürdürülebilir maliyet; sonra davet/üyelik, kullanıcı başına kalıcı kota, abuse bildirimi, gözlem ve kapasite testi. Render Free yerine VPN/proxy kullanımına açıkça izin veren bir VPS/barındırma ve yeterli bant genişliği gerekebilir. Ücret kullanıcıdan alınmasa bile sunucu maliyeti bir yerde karşılanır.

Ayrıntılı aşamalar ve kabul kriterleri: [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Dosyalar

```text
Dockerfile / compose.yaml / render.yaml   Dağıtım tanımları
cmd/gateway/                             Core süreç yönetimi ve kapanış
internal/config/                         Sır doğrulama + sing-box politikası
internal/gateway/                        HTTP/WS geçidi, limitler, durum sayfası
scripts/                                 Güvenli .env, kullanıcı ve istemci üretimi
tests/                                   Birim, gerçek WSS E2E, container smoke
.github/workflows/                       CI + opt-in hazırlık kontrolü
docs/                                    Test raporu, tasarım, yol haritası
```

**Lisans:** GPL-3.0-or-later. Resmi sing-box projesi, Render veya GitHub ile ilişki/ortaklık iddiası yoktur. Upstream ve yeniden dağıtım notları: [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
