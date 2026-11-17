# TARİHSEL — S-UI ilk aşama / yeniden çalıştırma

> **Mevcut VDS için kurulum talimatı değildir.** Kullanıcı yeni Docker panelini açtığını ve yönetici parolasını değiştirdiğini bildirdi. `mualiy-sui-panel.sh` tekrar çalıştırılmayacak; DB, compose ve sertifika dizini silinmeyecek. Güncel yol: [kök devir belgesi](../README.md) → [HIZLI_YAYIN.md](HIZLI_YAYIN.md).

Bu dosya, ilk panelin nasıl oluşturulduğunu ve yayın betiğinin hangi yapıyı beklediğini açıklamak için tutuldu. Hatalı yeniden kurulum riskini azaltmak için eski adım adım kurulum, varsayılan parola ve “şimdi kur” komutları devir kopyasından çıkarıldı; kaynak betik/testleri denetlenebilir tarihçe olarak yerinde bırakıldı.

## İlk kurulumun tasarımı

- Ayrı Docker Compose projesi: **`mualiy-sui`**, servis: **`panel`**.
- Dosyalar: `/opt/mualiy-sui/compose.yaml`, `/opt/mualiy-sui/db`, `/opt/mualiy-sui/cert`, `.mualiy-managed`.
- Beklenen işaret: `mualiy-sui-loopback-bootstrap-v1`.
- Image: `alireza7/s-ui:v1.6.7@sha256:c262ebd5cd53fd098d3080089af46220473bacbaf1a113e767aa9aadd2eed36d`.
- Platform `linux/amd64`, UID:GID `10001:10001`; capabilities kapalı, no-new-privileges.
- Yalnız `127.0.0.1:2095` panel ve `127.0.0.1:2096` abonelik yayını. İlk aşama **80/443/8443 yayımlamaz**.
- Başlangıçta `restart: "no"`; Ubuntu reboot sonrasında durmuş panel görülmesi DB kaybını veya yeniden kurulum gereğini kanıtlamaz. Gerçek duruma bakıp yalnız bu mevcut proje başlatılır.
- DB bind mount `/app/db`, salt-okunur sertifika bind mount `/app/cert`.
- Panel için 512MiB RAM, 1vCPU, 256 process/thread ve sınırlı container logu. Bu, ortak hostta diğer hizmetlere sıfır etki garantisi değildir.

## İlk aşamada yapılmayanlar

Trojan inbound/istemci, genel CA sertifikası, 8443 yayını, Cloudflare Tunnel, Access politikası ve cihaz TUN kabulü ilk kurucunun işi değildi. Sonraki yayın aracı bunları **mevcut paneli koruyarak** hazırlamak üzere üretildi. `restart: unless-stopped` de yayın aşamasında yalnız yeni panel ve yeni connector için uygulanır.

Eski envanterde native `ozgur-trojan.service` ve `sing-box` 8443 kullanıyordu; Docker 29.9.3 / Compose v5.7.1 görülmüştü. Bunlar tarihsel gözlemlerdir. Eski PID2014 güncel durdurma hedefi değildir. Crafty'nin yalnız `8443/tcp` exposed satırı host portu sahipliği demek değildir; güncel socket **ve** Docker mapping birlikte kontrol edilir.

## Kanıt ve sınırlar

- `TEST_SONUCLARI.json`: ilk kurucunun önceki 14 mock testi ve ayrı native upstream smoke kaydı.
- `tests/test_bootstrap.py`: gerçek Docker/curl/ss yerine mock kullanır; hedef ve lock yolu geçici fixture'a çevrilir. Kaynak installer değiştirilmez. Root yalnız fixture içindeki `install -o/-g` davranışı için gerekir; VDS'de sıradan test keşfiyle çalıştırılmamalıdır.
- Yeni devir tekrar testleri kökte `DEVIR_TEST_SONUCLARI.json` içindedir.
- Asistanın VDS'ye SSH erişimi, gerçek Docker build/deploy veya panel DB incelemesi olmadı. Panelin açıldığı ve şifrenin değiştiği **kullanıcı bildirimi**dir.
- S-UI upstream production kullanımını önermiyor; bu kişisel deneme, topluluk hizmeti kabulü değil. MikuBox 1.4.3-UwU-2 de upstream tarafından EOL işaretli.

Kaynaklar: <https://github.com/alireza0/s-ui/releases/tag/v1.6.7> · <https://github.com/HatsuneMikuUwU/MikuBoxForAndroid/releases/tag/1.4.3-UwU-2>
