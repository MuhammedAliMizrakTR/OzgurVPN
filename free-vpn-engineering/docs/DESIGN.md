> **ARŞİV:** eski WSS uygulama-proxy tasarımı; güncel Docker S-UI/TUN mimarisi değildir. Ana devir belgesi: `../../README.md`.

# Tasarım kararları

## Neden tek container, iki süreç?

Render bir web service için tek public HTTP portu sağlar. Ham TCP Trojan
inbound'unu public portta yayınlamak web ingress modeliyle aynı şey değildir.
Go gateway, ana sayfa ve /healthz ile WebSocket tünelini aynı HTTP portunda
çoklar; gerçek Trojan protokolünü yeniden uygulamaz. Çekirdek resmi sing-box
binary'sidir ve loopback'te çalışır.

Gateway core'un ebeveyn sürecidir. Ek bir process manager/runtime paketine
veya TUN aygıtına ihtiyaç yoktur. Compose init: true ayrıca container PID 1
sinyal/reap davranışı sağlar; Render'da Go süreç yöneticisi doğrudan giriş
noktasıdır.

## Neden TLS core'da kapalı?

İstemci → Render TLS edge bağlantısında sertifika doğrulaması açıktır.
Render bu TLS'i sonlandırır, gateway'e HTTP/WS iletir. Gateway → core ise
aynı container içinde 127.0.0.1'dir. Core'a ikinci bir self-signed TLS katmanı
eklemek, Render'ın TLS sonlandırması gerçeğini ortadan kaldırmaz.

Bu model sağlayıcıdan gizlilik sağlamaz: Render edge Trojan kimlik doğrulama
verisini ve tünel içindeki hedef bağlantı akışını görebilir. Hedef HTTPS ise
uygulama içeriğinin hedefle TLS şifrelemesi ayrıca sürer. HTTP için bu yoktur.

Başka sağlayıcıya taşınırsa public origin mutlaka uygun bir TLS reverse proxy
arkasında kalmalı; raw 10000 portu internete açılmamalıdır.

## Neden “HTTP trafiği” için port filtresi?

Varsayılan amaç web erişimi: TCP 80 ve 443. Bu bir layer-4 izinli listedir,
HTTP içerik analizi değildir. UDP ve ICMP sunucuda reddedilir; istemci Trojan
outbound'u da TCP ile sınırlıdır. SMTP portları yapılandırmada da reddedilir.

Private domain/IP kuralları doğrudan metadata/localhost hedeflerini engeller.
Önce resolve sonra IP policy sırası, bir public domain'in private IP döndürme
riskine karşı önemlidir. Direct outbound çözümlenen hedef adreslerini kullanır.
Yerel test, public DNS'teki localtest.me → 127.0.0.1 senaryosunu da denetler.
Bu kontrol tam bir DNS rebinding penetrasyon testi veya host firewall'u değildir.

## Limitlerin anlamı

- MAX_TUNNELS: aynı anda açık WS tünelleri, global.
- HANDSHAKES_PER_MINUTE / HANDSHAKE_BURST: token bucket, global; client IP
  header'larına güvenilmez. Bu yüzden yanlış bir per-IP güvenlik iddiası yok.
- TUNNEL_IDLE_TIMEOUT: loopback stream'inde son okuma/yazma sonrası hareketsizlik.
- TUNNEL_MAX_AGE: aktif olsa da bir backend stream için sert ömür sınırı.

Bu limitler aylık trafik kotası değildir. Sayaçlar bellektedir; restart ile
sıfırlanır. Bir kullanıcıya harcanabilir, kalıcı GB kotası koymak için dayanıklı
sayaç, atomik tahsis ve ölçülebilir byte muhasebesi gerekir. Bu prototip bunu
varmış gibi göstermez.

## Sağlık ve test ayrımı

/healthz, gateway hazır bayrağı + gerçek loopback TCP bağlantısını kontrol eder.
Dış TLS, Trojan parolası, public DNS ve internet çıkışını ölçmez. E2E testinde
bunlar ayrı ayrı gerçek istemciyle denenir. Render'ın loading page'ine verilen
HTTP 200 tek başına başarı değildir; monitor beklenen JSON'u da kontrol eder.

Core ölürse gateway kapanır. http.Server.Shutdown, hijack edilen WS socket'lerini
kapatmadığı için aktif bağlantılar ayrıca izlenir ve kapatılır. Oturumlar
redeploy'da devam etmez; yeni bağlantı gerekir.

## Neden anti-sleep yok?

Kullanıcı “uygun yöntemi seç” dediği için CI ve gözlem ayrı tasarlandı.
Render AUP'deki kullanım kısıtları ve kaynak kullanım maddelerine rağmen
ücretsiz/sürekli hizmet garantisi verilemez. Actions cron da kesin zamanlı
scheduler değildir. Opt-in 6 saatlik readiness kontrolü bir uyku bypass'ı
değildir; soğuk başlangıcı tetikleyebileceği açıkça belirtilir.

Gerçek sürekli hizmet, kullanım izni olan ve uyumayan compute gerektirir.
Ücretsiz istemci/açık kaynak proje olmak ile ücretsiz sınırsız altyapı aynı
şey değildir.
