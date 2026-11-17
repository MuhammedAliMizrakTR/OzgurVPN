> **ARŞİV YOL HARİTASI:** bu klasörün eski prototip hedefleridir. “Var” veya “CI/container testleri” test **dosyalarının** bulunmasını da içerebilir; gerçek Docker/Actions/Render çalıştırması kanıtlanmadı. Güncel öncelik ve kalanlar `../../README.md` içindedir.

# Kontrollü prototipten topluluk hizmetine

## Aşama 0 — Bu teslim: teknik prototip

**Var:** gerçek sing-box; TLS doğrulamalı WSS; HTTP/HTTPS/SOCKS testleri;
kullanıcı başına env parolaları; private/metadata/UDP/port politikası; global
oturum/handshake/süre sınırları; CI/container testleri; izin koşullu Render
Blueprint; ana sayfa ve hazırlık kontrolü.

**Kabul:** yerel test raporu başarılı. Container build ve gerçek sağlayıcı
üzerindeki egress/sertifika/soğuk başlangıç doğrulaması ayrıca tamamlanmalı.

## Aşama 1 — Barındırma ve izin kapısı

- Sağlayıcı, VPN/proxy ve üçüncü kişi trafiğine açıkça izin vermeli.
- Render için AUP 3, 7, 9 açısından yazılı uygunluk alınmalı; ücretli planın
  tek başına izin olmadığı kabul edilmeli.
- Alternatifte uygun VPS veya barındırma, geçerli domain/TLS ve host-level
  egress firewall tasarlanmalı. Docker origin private kalmalı.
- Bant genişliği, saat, ek ücret ve bağış/sponsorluk bütçesi belirlenmeli.

**Kabul:** izin ve aylık üst bütçe belgeli. Bu sağlanmadan “herkese açık” kayıt
veya kesintisizlik duyurusu yapılmaz.

## Aşama 2 — Davetli beta

- Ayrı kullanıcı parolaları ve güvenli dağıtım; kullanıcı listesi asla public değil.
- Harici kalıcı depolamada kullanıcı, iptal, süre ve aylık byte sayacı.
- Kullanıcı başına hız/bağlantı/GB kotası ve kota aşıldığında fail-closed davranış.
- Restart, eşzamanlı oturum ve atomik sayaç testleri.
- Abuse/şikâyet kanalı, kullanım koşulları, log ve kişisel veri politikası.

**Kabul:** kullanıcı kotası restart ile yenilenmiyor; iptal edilen kullanıcı
aktif oturumla devam edemiyor; bütçe aşımı tatbikatı başarılı.

## Aşama 3 — Ücretsiz topluluk erişimi

- Kullanıcı kayıt ve davet sistemi; admin MFA; sır yönetimi ve rotasyon.
- Adil kullanım politikası; kötüye kullanım önleme ve gerektiğinde insan incelemesi.
- Trafik içeriğini saklamadan uygun kapasite/gözlem ölçümleri.
- Erişilebilirlik, yük ve güvenlik denetimi; test edilmiş geri dönüş planı.
- “Ücretsiz” modelin maliyeti kullanıcıya değil sponsor/operatöre ait olduğunun
  açıklanması. Sınırsız bant genişliği iddiasından kaçınma.

**Kabul:** sağlayıcı izni, bütçe, abuse süreçleri ve bağımsız güvenlik gözden
geçirmesi hazır olmadan anonim herkese açık proxy açılmaz.

## Ayrı ürün işi — Cihaz genelinde VPN

Mobil/masaüstü TUN profili, UDP/QUIC desteği, DNS/killswitch/IPv6/WebRTC sızıntı
analizi, ağ değişimi ve uyku/uyanma testleri ayrı tasarım gerektirir. Mevcut
uygulama proxy'si bu özellikleri sağlamaz; aynı isimle varmış gibi sunulmaz.
