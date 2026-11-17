# Mualiy — GitHub ve yeni sohbet devir belgesi

**Tek giriş noktası · 14 Kasım 2026 · Türkçe · Klasör yapısı korunmuş kaynak paketi**

Bu belge; hedefi, son durumu, kanıt sınırlarını, kalan işleri, yeni sohbete yapıştırılacak istemi ve **pakette tutulan her dosyanın açıklamasını** bir araya getirir. Kökünde bu belge bulunan temiz paket **79 dosyadır**. Mevcut beş proje klasörünün adı ve kalan dosyaların iç yolları değiştirilmedi.

> **En önemli bilgi:** Kullanıcı mevcut Docker S-UI panelini açtığını, yönetici parolasını değiştirdiğini ve Ubuntu yükseltmesiyle yeniden başlatmanın başarıyla tamamlandığını bildirdi. **Kurulumu/yükselticiyi baştan çalıştırma.** Öncelik mevcut paneli ve DB'yi koruyarak yayını ve gerçek cihaz geneli Trojan/TUN kabulünü bitirmektir.
>
> **Bu paket canlı sunucu yedeği değildir.** DB, gerçek parolalar, token'lar, özel anahtarlar ve istemci bağlantıları özellikle yoktur. Asistan VDS'ye SSH ile bağlanmadı; Cloudflare hesabında değişiklik veya GitHub'a push yapmadı.

## İçindekiler

1. [Hedef ve kapsam](#1-hedef-ve-kapsam)
2. [Nerede kaldık?](#2-nerede-kaldık)
3. [Seçilen mimari ve korunacak canlı veriler](#3-seçilen-mimari-ve-korunacak-canlı-veriler)
4. [Güvenlik kuralları](#4-güvenlik-kuralları)
5. [Kalan işler: küçük görev parçaları](#5-kalan-işler-küçük-görev-parçaları)
6. [Yeni sohbete yapıştırılacak ana istem](#6-yeni-sohbete-yapıştırılacak-ana-istem)
7. [Klasör yapısı ve her dosyanın açıklaması](#7-klasör-yapısı-ve-her-dosyanın-açıklaması)
8. [Çıkarılanlar ve devir sırasında yapılan düzeltmeler](#8-çıkarılanlar-ve-devir-sırasında-yapılan-düzeltmeler)
9. [Testler: tarihsel sonuç ile yeni kontrol ayrımı](#9-testler-tarihsel-sonuç-ile-yeni-kontrol-ayrımı)
10. [GitHub'a yapıyı bozmadan yükleme](#10-githuba-yapıyı-bozmadan-yükleme)
11. [Resmî başvuru kaynakları ve sınırlar](#11-resmî-başvuru-kaynakları-ve-sınırlar)

---

## 1. Hedef ve kapsam

### Yakın hedef — önce mevcut VDS

- Türkiye'deki mevcut Ubuntu VDS üzerinde **kendi Trojan sunucusunu** çalıştırmak; başka bir Trojan sunucusuna istemci kurmak değil.
- Mevcut **S-UI v1.6.7 / sing-box** Docker panelini korumak; değiştirilmiş yönetici parolası ve DB kaybolmayacak.
- `panel.mualiy.net`: ayrı **YENİ Cloudflare Tunnel**, yalnız sahibin e-postasına izin veren Access, ardından S-UI girişi.
- `sub.mualiy.net`: istemcilerin okuyabildiği özel abonelik; tarayıcı etkileşimli Access yok, gizli abonelik yolu var.
- `vpn.mualiy.net:8443`: Cloudflare **DNS-only**, doğrudan Trojan/TLS. Port ancak güncel socket **ve** Docker yayın eşlemesi kontrol edilerek kullanılacak.
- Android'de kurulu **MikuBox 1.4.3-UwU-2**, Windows'ta **10/11**: **cihaz geneli VPN/TUN, tüm uygulamalar ve değişmiş genel çıkış IP'si**. Yalnız seçili uygulamaya HTTP/SOCKS proxy vermek kabul değildir.
- Önce bu sunucuyla Discord/Roblox/Wattpad'i gerçek cihazda denemek. Gerekirse mevcut resmî zapret2 üzerinden **sunucunun hedeflere çıkışını** kontrollü değerlendirmek.
- Minecraft/Crafty, Jitsi, ThinLinc/cloudflared, SSH, rotalar ve ilgisiz Docker projeleri kesilmeyecek.

### Uzun hedef — henüz tamamlanmadı

- Tamamen ücretsiz, kart istemeyen, Docker çalıştırabilen, **en az100 GB/ay** sağlayan ve VPN'e açıkça izin veren barındırma.
- Birinci kotayı paylaşan iki container değil, **ikinci bağımsız en az100 GB trafik hakkı** olan yabancı yedek.
- Hax tahsisi/uygunluğu ve yalnız izinli yöntemlerle Telegram/API yenilemesi.
- İleride güvenli, sürdürülebilir ücretsiz/topluluk erişimi; kalıcı kullanıcı kotası, iptal/rotasyon, kötüye kullanım süreçleri ve sağlayıcı izni.

İlk `free-vpn-engineering/` prototipi Trojan/WSS uygulama proxy'siydi. Render'ın 15 dakikalık boşta uyuması motivasyonlardan biriydi; **kesintisiz ücretsiz barındırma veya uyku sorununu çözme hedefi gerçekleşmiş sayılmaz**. CI/sağlık kontrol dosyaları sürekli sunucu hizmeti değildir. Back4app için 50. dakikada GitHub/VDS tetiklemeli yeniden dağıtım fikri konuşuldu; uygulanmadı ve bunun yaşam süresini güvenilir/izinli biçimde yenilediği kanıtlanmadı.

## 2. Nerede kaldık?

### Kanıt etiketleri

- **KULLANICI:** Kullanıcının beyanı veya paylaştığı terminal/log; asistanın bağımsız uzak incelemesi değil.
- **ÖNCEKİ YEREL:** Önceki oturumda çalışma alanında yapılan test veya kamuya açık gözlem.
- **DEVİR YEREL:** Bu temiz kopya hazırlanırken gerçekten yeniden yapılan kontrol.
- **HAZIR / BEKLİYOR:** Kod/rehber var; gerçek ortam kabulü yok.

| Konu | Son durum | Kanıt / sınır |
|---|---|---|
| Mevcut Docker paneli | Kullanıcı paneli açtı ve yönetici şifresini değiştirdi | **KULLANICI**; DB/container sonradan bağımsız incelenmedi |
| Ubuntu | Terminal: **Ubuntu 26.04.1 LTS /26.04 /resolute**; kullanıcı sonrasında **başarılı reboot** bildirdi | **KULLANICI**; artık “reboot bildirilmedi” denmeyecek. Kernel/paket/servis sağlığı ayrıca ölçülmedi |
| `Security Violation` / SSH açıklaması | Kullanıcı sağlayıcının değiştirdiği SSH paketleri/imzalarıyla açıkladı | Kullanıcının açıklaması; bağımsız doğrulanmış neden değil. `sshd -t` imza kontrolü değildir |
| Snap indirmeleri | Önceden `api.snapcraft.io:443` refused/timeout hataları görüldü | Güncel düzelme sonucu yok; bu tek başına OS/DEB bozulması kanıtı değil |
| Eski native servis temizliği | Yetki verildi; geri alınabilir arşivleme betiği teslim edildi | VDS'de uygulanıp uygulanmadığı **bilinmiyor**. Yeni DB kapsam dışı |
| Yayın betiği | `mualiy-yayinla.py` hazır; mevcut panel üzerinden ilerler | **HAZIR**; Docker/gerçek ACME/VDS yayını tamamlandı denemez |
| Access hatası | Varsayılan urllib UA403; `MualiySetup/1.1` ile Access302 farkı düzeltildi | **ÖNCEKİ YEREL** kamu gözlemi + yeniden geçen offline guard'lar; VDS tekrar denemesi bilinmiyor |
| Kullanıcının son bilinen yayın denemesi | `check_access` aşamasında durdu | O denemede panel API/ACME/Trojan değişikliklerine geçilmedi. Sonraki deneme varsayılmaz |
| Gerçek S-UI API/TLS/Trojan | Geçici S-UI 1.6.7 + sing-box 1.14.4 fixture'ında API, DB yedeği, TLS, kimlik doğrulamalı TCP echo, idempotence ve abonelik doğrulandı | **DEVİR YEREL** yeniden geçti; loopback, sentetik kullanıcı, geçici CA/DB, süreç durduruldu. VDS başarısı değil |
| Paket testleri | **87 Python testi**, Go race/coverage/vet/build geçti | **DEVİR YEREL**; Docker/systemd test çağrıları mock; ayrıntı kök JSON raporda |
| DNS | Önceki gözlem: vpnA`38.210.77.17`, panelACloudflare; `sub`NXDOMAIN | Tarihsel kamu gözlemi; devir sırasında canlı DNS yeniden sorgulanmadı |
| Android/Windows tam VPN | **BEKLİYOR** | Telefonda/PC'de TUN + değişmiş IP, DNS/IPv6/UDP/oyun/ses kabulü yok |
| Sertifika/yenileme/dış8443 | **BEKLİYOR** | Gerçek CA, host izinleri, container entegrasyonu, dış ingress ve yenileme tatbikatı yok |
| Wattpad zapret2 | Aday seçildi; resmî kurulum kullanıcı logunda var | Yeni Docker çıkışı ve gerçek uygulama kabulü yok |
| Yabancı yedek / bağımsız100 GB / Telegram | **BEKLİYOR** | Tahsis ve izinli otomasyon yok |
| Topluluk yayını | **TAMAMLANMADI** | S-UI upstream production'ı önermiyor; başlangıç kişisel deneme |

**Zaman notu:** Bazı eski yükleme adlarında `20261115` bulunuyor. Bu adlar veya dosya mtime'ları doğrulanmış gözlem zamanı kabul edilmedi. Bu devir belgesinin tarihi görüşmenin yerel tarihidir; olayların güncelliğinde son kullanıcı bildirimi esas alınır. Eski “Ubuntu 24.04”, “henüz kurulmadı”, “SFA” ve “443 bilinmiyor” cümleleri güncel durum değil, işaretlenmiş tarihçedir. Önceki `21.04.LTS` ifadesi geçerli bir LTS adı değildi; buradan yükseltme zinciri uydurulmaz ve yükseltici yeniden çalıştırılmaz.

## 3. Seçilen mimari ve korunacak canlı veriler

```text
Yönetici tarayıcısı
  └─ HTTPS panel.mualiy.net/app/
       └─ Cloudflare Access: yalnız sahibi
            └─ YENİ mualiy-panel Tunnel / mualiy-sui-tunnel connector
                 └─ HTTP 127.0.0.1:2095 → mevcut S-UI paneli

MikuBox / Windows abonelik isteği
  └─ HTTPS sub.mualiy.net/sub/<gizli-yol>
       └─ aynı YENİ Tunnel, tarayıcı etkileşimli Access YOK
            └─ HTTP 127.0.0.1:2096 → S-UI abonelik servisi

Android veya Windows cihaz geneli TUN
  └─ vpn.mualiy.net:8443, doğrudan Trojan + doğrulanan TLS
       └─ DNS-only A 38.210.77.17
            └─ Docker mualiy-sui / panel → hedef internet siteleri
                 └─ gerekiyorsa mevcut resmî zapret2 çıkış etkisi ayrıca test edilir
```

Panel/abonelik HTTP'si Tunnel içindeki yerel origin içindir. Sıradan Trojan/TCP'yi normal HTTP Tunnel route'una koymak eşdeğer çözüm değildir; kullanıcı **doğrudan VPN** taşımasını seçti. DNS-01 ile host80/443'e el koymadan CA sertifikası hedefleniyor.

### Canlı VDS yolları — GitHub'a konmayacak, silinmeyecek

| Yol / ad | Amaç ve korunma nedeni |
|---|---|
| `/opt/mualiy-sui/compose.yaml` | Var olan yeni panelin Compose tanımı; yayın aracı yalnız bu projeyi değiştirir |
| `/opt/mualiy-sui/db/` | Değişmiş yönetici parolası, kullanıcılar ve panel yapılandırması; **asıl korunacak veri** |
| `/opt/mualiy-sui/cert/` | Panelin okuyacağı sertifika/özel anahtar kopyaları; sır içerir |
| `/opt/mualiy-sui/.mualiy-managed` | Beklenen ilk kurulum işareti: `mualiy-sui-loopback-bootstrap-v1` |
| `/opt/mualiy-sui-live/` | Yayın aracının özel state, DB/Compose yedeği, DNS/Tunnel token'ı, ACME ve log/export alanı. Kısmi varlığı bilinmiyor; silinerek “baştan” denenmez |
| `mualiy-sui-live-v1` | Yukarıdaki özel dizinin yönetim işareti |
| `/home/neo/mualiy-baglanti-.../baglanti.txt` | Kullanıcının yalnız yerelde okuyacağı Trojan/abonelik bağlantıları; **bearer-secret** |
| `/root/mualiy-eski-servisler-.../` | Eski native temizliği uygulanmışsa geri dönüş arşivi; eski parola/anahtar barındırabilir |
| `/opt/zapret2/` | Resmî bol-van/zapret2; eski özel `ozgur-zapret` veya Keift `/opt/zapret` ile karıştırma |
| `thinlinc-tunel` | Var olan ThinLinc Cloudflare tüneli; token/config/ingress/DNS korunacak |
| `minecraft-crafty-crafty-1`, `minecraft-crafty-cloudflared-1` | Mevcut Minecraft/Crafty yapısı; port/DNS/mount'ları taşınmayacak |

İlk panel Compose projesi **`mualiy-sui`**, servis **`panel`**, UID:GID **10001:10001**. 2095/2096 hostta loopback'te kalacak. İlk bootstrap `restart: no` kullanıyordu: reboot sonrası panel durmuşsa bu yeniden kurulum gerekçesi değildir. Yayın betiği yalnız yeni panel ve yeni connector için `unless-stopped` ayarlar.

### Sabit sürümler ve değişmemiş çalıştırılabilirler

| Öğe | Kilit / SHA-256 |
|---|---|
| **Güncel yayın betiği** `trojan-panel-plan/mualiy-yayinla.py` | `7e5d51dec9be2858abf5d6484602f2cf351b043c1fea77925f22929d7fb07f5e` |
| Eski native temizliği `mualiy-eski-servis-temizle.py` | `cc6e788ab286ecd83997872eccbd5837eccf5428274a6e5326162efab99d6bb8` |
| **Yeniden çalıştırılmayacak** bootstrap `mualiy-sui-panel.sh` | `5a8196b98fd6a8bac3bf3ac80cae37849cc0007de7ff45bb7a29b7b0c72507a2` |
| S-UI image | `alireza7/s-ui:v1.6.7@sha256:c262ebd5cd53fd098d3080089af46220473bacbaf1a113e767aa9aadd2eed36d` |
| Certbot image | `certbot/dns-cloudflare:v5.10.0@sha256:6d5e1e84f687ce81786c97cbeccb9dda94d86bbb29a81dbb85527bd68008d77d` |
| Ayrı connector image | `cloudflare/cloudflared:2026.11.0@sha256:b94b96edf2c9c4360f8879c8580cfaa99077f19c849ec595ca2f711b27d4f344` |
| Pasif Wattpad aday config'i | `73630be4566251163de982b4379efba224d5a567f7a2af83ea3c9a3ccb671b0d` |

Image digest/platform kayıtları önceki araştırmada incelendi; **bu sandbox'ta Docker image çalıştırılması anlamına gelmez**. Sabitleme, sürümün sonsuza dek güvenli olduğu iddiası değildir. Yayın betiği değiştiğinde Termux başlatıcısındaki kaynak commit'i ve SHA-256 pini birlikte güncellenir; taşınabilirlik düzenlemeleri testlerde ve belgelerde de doğrulanır.

## 4. Güvenlik kuralları

1. Türkçe iletişim kur. Parola, SSH özel anahtarı, Cloudflare/Tunnel/API/Telegram token'ı, DB, `state.json`, özel log, QR veya gerçek istemci/abonelik linkini **sohbette isteme/paylaşma**. Gizli giriş yalnız VDS terminalinde yapılır.
2. Mevcut panel/DB/parola korunur. Bootstrap, parola reseti, DB/compose/private state silme, `docker compose down -v`, genel Docker restart/prune veya `pkill sing-box` yok. Eski PID2014 güncel kill hedefi değildir.
3. Host80/443, Minecraft/Crafty/Jitsi, SSH, rotalar ve ThinLinc'in mevcut cloudflared servisi/DNS'i korunur. `cloudflared service install` ile mevcut servisin üzerine yazma.
4. 8443 için `ss` tek başına yetmez: Docker published-port mapping de kontrol edilir. Container içindeki `8443/tcp` exposed ifadesi host8443'ün Crafty'ye ait olduğunu göstermez. Bilinmeyen port sahibinde dur.
5. Eski native birimler için kullanıcı yetkisi var: `ozgur-trojan.service`, `s-ui.service`, `s.ui.service`, `sing-box.service`. **Bu yetki yeni Docker panelini veya resmî zapret2'yi kapsamaz.** Temizlik aracı önce doğrular, silmek yerine özel arşive taşır. Genel paket/hesap purgesi yapmaz.
6. Yayını gereksiz bir “tüm kalıntılar önce silinsin” turuna bağlama. Yayın aracı gerekli gerçek çakışmayı kendisi denetler; yalnız canlı PID/ExecStart/unit eşleşmesiyle eski `ozgur-trojan`ı durdurabilir. Bilinmeyen servisi durdurmaz.
7. Yönetim hostname'inde Access owner-only olmalı. Access302 görmek, e-posta politikasını veya origin sağlığını kanıtlamaz. UA düzeltmesi guard'ı kaldırmadı; Access'i kapatarak sorunu geçiştirme.
8. Abonelik hostname'ine tarayıcı etkileşimli Access dayatma; yönetim korumasını `*.mualiy.net` yaparak aboneliği bozma. Gizli abonelik yolu parola gibi korunur.
9. TLS doğrulamasını `insecure/allowInsecure` ile kapatma. DNS-only doğrudan bağlantıda Cloudflare Origin Certificate otomatik olarak genel güvenilir sertifika değildir.
10. Genel firewall flush, geniş otomatik apt/dpkg/Snap onarımı, SSH restartı, yeni release upgrade veya körlemesine reboot bu devir işinin parçası değildir.
11. Resmî zapret2 v1.0.7 korunur. Tam blockcheck taramasını tekrarlama, rastgele fake/TTL/OOB stratejileri ekleme. Hostlist, UID/container kısıtlaması değildir; Docker çıkış yolu ayrıca ölçülür.
12. TUN hedefi keyfî tüm L3 protokollerini taşıma garantisi değildir. Trojan TCP/UDP uygulama akışları ile ICMP/hotspot/kalıcı kill-switch aynı şey değildir. `strict_route` tek başına kalıcı kill-switch değildir.
13. S-UI upstream production'ı önermiyor; MikuBox 1.4.3-UwU-2 upstream'de EOL. Kullanıcının uygulaması sessizce SFA'ya/yeni Mihomo dalına değiştirilmez; ilk yayın kişisel denemedir.

## 5. Kalan işler: küçük görev parçaları

**Çalışma biçimi:** Bir parçayı tamamla, sırsız sonucu ve kalan belirsizliği kaydet, sonra sıradakine geç. Aynı OS/domain/transport/istemci sorularını tekrar sorma. Önce 1–3; yedek sağlayıcı araştırması yüzünden mevcut yayını erteleme.

### Parça 1 — Reboot sonrası kısa durum ve mevcut paneli koruma

**İstem:** “Başarılı reboot bildirimini kabul et. `durum.json` ve yayın kodunu oku. Tek kısa salt-okunur çıktı grubuyla kernel/paket/servis, mevcut mualiy-sui health ve8443 socket+Docker mapping durumunu belirle. Yeniden kurulum/yükseltme/temizlik yapma. Gerçek sağlık engeli yoksa yayına dön.”

VDS terminalinde istenebilecek kısa blok; asistan tarafından çalıştırılmış sayılmaz:

```bash
uname -r
uptime -s
systemd-detect-virt
sudo dpkg --audit
sudo /usr/sbin/sshd -t
systemctl --failed --no-pager
sudo docker -H unix:///var/run/docker.sock ps -a \
  --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
sudo ss -H -lntp '( sport = :8443 or sport = :2095 or sport = :2096 )'
```

`dpkg --audit` / `sshd -t` başarıda sessiz olabilir; `systemd-detect-virt` çıktısı ve exit durumu bağlamıyla yorumlanır. Bu çıktılar da hostname/IP içerebilir; paylaşmadan gözden geçirilir. Tam unit/config/env/token/DB dökümü istenmez.

Panel durmuşsa önce beklenen proje/compose/mount yapısını doğrula; yalnız mevcut paneli başlatacak hedefli işlem seç. **Başarı:** panelin sağlıklı olduğu veya tek somut engel biliniyor; DB/parola korunuyor. Ayrı, güncel veriler olmadan tüm servislerin sağlıklı olduğu söylenmez.

### Parça 2 — Access / YENİ Tunnel / DNS ve mevcut betikle yayın

**İstem:** “`trojan-panel-plan/HIZLI_YAYIN.md` ve `mualiy-yayinla.py` üzerinden devam et. Yapılmış Access/Tunnel kayıtlarını yeniden oluşturma. Owner-only Access, ayrı yeni mualiy-panel tunnel ve DNS-only vpn kaydının eksiklerini tamamla; ThinLinc'e dokunma. UA düzeltmesi yerinde kalsın. Mevcut panelden DNS-01 + Trojan/TLS8443 yayınını bitir.”

- Panel route → **HTTP `127.0.0.1:2095`**; ayrı connector projesi **`mualiy-sui-tunnel`**.
- Sub route → **HTTP `127.0.0.1:2096`**; varsa hazır olan korunur. Son tarihsel subDNS sonucu NXDOMAIN'di; güncelmiş gibi tekrarlama.
- VPN → **DNS-only A`38.210.77.17`**. Eski/yanlış AAAA varsa IPv6 erişimi hazırlanmış varsayılmaz.
- DNS token yalnız gerekli zone için **Zone:DNS:Edit / mualiy.net** kapsamlı olmalı. Global API Key istenmez.
- Token'lar sohbete, komut argümanına veya repoya yazılmaz; betik VDS terminalinde görünmez giriş kullanır.

Yalnız güncel dosya VDS'ye `/home/neo/mualiy-yayinla.py` olarak aktarıldıktan ve kısa durum/Cloudflare ön koşulları değerlendirildikten sonra:

```bash
printf '%s\n' '7e5d51dec9be2858abf5d6484602f2cf351b043c1fea77925f22929d7fb07f5e  /home/neo/mualiy-yayinla.py' | sha256sum -c - &&
sudo python3 /home/neo/mualiy-yayinla.py --apply
```

Betiğin `--check` modu **yoktur**; böyle bir seçenek uydurma. `--apply` gerçek değişiklik yapar. DNS-01 CA işlemi, API kayıtları ve eski servis durdurma kısmen ilerleyebilir; otomatik tam rollback yoktur. `/opt/mualiy-sui-live` ve yedekler silinmez. API'deki aynı isimli kaydı kullanıcı değiştirmişse zorlayarak tekrar uygulama yapılmaz. Hata paylaşımı yalnız `DUR:` ve aşamanın sırsız özetidir.

**Başarı:** korumalı panel girişi ve sağlıklı yeni connector, yeni Trojan inbound, güvenilir CA/TLS, yalnız doğru8443 TCP yayını ve dış bağlantı testi. Betiğin yerel TLS handshake'i **tek başına gerçek kimlik doğrulamalı istemci/dış ingress kabulü değildir**. Sağlayıcı firewall'ı kapalıysa yalnız gerekli TCP 8443 izni değerlendirilir; geniş port açma yok.

### Parça 3 — Android MikuBox gerçek cihaz geneli kabulü

**İstem:** “Kurulu MikuBox 1.4.3-UwU-2'yi koru. VDS'de özel `baglanti.txt` dosyasındaki Trojan linkini yalnız kullanıcı kendi cihazında içe aktarsın. TLS doğrulaması açık, VPN/TUN/tüm trafik modu ve Android VPN izniyle gerçek kabul yap. Linki/QR'ı sohbete isteme.”

- MikuBox'un bu sürümü NekoBox soy hattıdır; güncel Miku/Mihomo belgeleriyle aynı varsayılmaz. Körlemesine tam sing-box JSON'u içe aktarma.
- **Telefonun kendi tarayıcısından**, VPN açıkken `https://api.ipify.org` beklenen **`38.210.77.17`** çıkışını göstermeli. VDS/ThinLinc tarayıcısının aynı IP'yi göstermesi telefon VPN'i kanıtı değildir.
- Wi-Fi/mobil veri geçişi, DNS ve IPv6 sızıntısı/kaçışı, bağlantı kopması/yeniden bağlanma ölçülür. Tüm uygulama kapsamı dışlamalarla bozulmamalı.
- Discord oturum/mesaj/ses, Roblox oturum/oyun, Wattpad sayfa/giriş/okuma ayrı ayrı değerlendirilir. Tek curl 200 bütün uygulamaların çalışması değildir.

**Başarı:** telefonda değişmiş çıkış IP'si + cihaz geneli kapsam + gerçek uygulama sonuçları açıkça kaydedildi. UDP/QUIC/ses/oyun çalışmıyorsa açıkça “kaldı” denir.

### Parça 4 — Windows 10/11 TUN ve özel abonelik

**İstem:** “Windows 10/11 bilgisayarda mimariyi yalnız istemci binary'si seçerken doğrula; OS'yi yeniden sorma. Android'deki çıkış IP/DNS/IPv6/UDP/uyku-ağ değişimi kabulünü PC'de de yap. Sonra sub.mualiy.net route/DNS ve MikuBox/Windows abonelik biçimini test et; etkileşimli Access ekleme.”

Manuel Trojan bağlantısı abonelik DNS'inin tamamlanmasına bağımlı değildir; temel bağlantı önce denenebilir. Gizli abonelik adresi kullanıcıya özel kalır. Önceki native fixture yalnız örnek abonelikte doğru domain/Trojan URI ürettiğini gösterir; bu istemcilerin tüm format/alanları içe aktardığını veya uzaktan aboneliğin çalıştığını kanıtlamaz.

**Başarı:** her iki platformda cihaz geneli kabul; özel abonelik gerçek istemcide yenilenebiliyor; herhangi bir gerçek link public dosyaya/sohbete girmedi.

### Parça 5 — Sertifika yaşam döngüsü ve dar kapsamlı eski kalıntı kontrolü

**İstem:** “Canlı DB/Compose yedeğini ve sertifika izinlerini kullanıcıya özel koru. Gerçek cert yenilemesini ve yalnız yeni panelin doğru sertifikayı yüklemesini kontrollü doğrula; ThinLinc ve diğer container'ları yeniden başlatma. Sonra yalnız yetki verilmiş eski native kalıntıları incele; geniş temizlik yapma.”

- Planlanan birimler **`mualiy-sui-cert.service` / `.timer`**, takvim04:20 /16:20 + rastgele gecikme. Önceki takvim sözdizimi kontrolü, timer'ın VDS'de kurulduğu anlamına gelmez.
- Özel CA anahtarı/cert kopyaları root:10001 /0640 hedefleniyor; gerçek container erişimi ve renew sonrası yeni cert ayrıca ölçülür.
- Betikte `--renew` **gerçek** yenileme yoludur; var olmayan bir `--dry-run` bayrağı ekleyip çalıştırma. Üretim CA oran sınırlarını gözeterek kontrollü test tasarla.
- Yalnız sertifika değişince yeni panel restartı kısa VPN kesintisi yapabilir; sessiz sıfır kesinti iddiası yok.
- Eski temizlik rehberi: `trojan-panel-plan/ESKI_SERVIS_TEMIZLIGI.md`. Uzak uygulama sonucu bilinmiyorsa bunu doğrula; sırf bilinmiyor diye yeni yayını başa alma. Arşivleri/ortak paketleri/ev dizinlerini topluca silme.

**Başarı:** gerçek yenileme ve geri dönüş yolu kayıtlı; yeni DB/parola ve ilgisiz servisler korunmuş; eski native kapsamın sonucu biliniyor.

### Parça 6 — Gerekirse Wattpad / resmî zapret2 Docker çıkışı

**İstem:** “`wattpad-inceleme/KURULUM.md` ve `analiz.json` içindeki mevcut `multisplit:pos=2` adayından devam et. Resmî /opt/zapret2'yi tekrar kurma veya tam tarama başlatma. Yeni Docker Trojan çıkışının gerçekten kapsanıp kapsanmadığını dar, yedekli ve geri dönüş zamanlayıcılı karşılaştırmayla ölç.”

Seçilmiş aday: `--payload=tls_client_hello --lua-desync=multisplit:pos=2`. `AVAILABLE` yalnız tarihsel blockcheck sonucudur. `GETLIST=` mevcut global/gzip listeleri kendiliğinden kaldırmaz; user/global/exclude birleşimini ve Docker FORWARD/NAT yolunu incele. Eski native UID kurallarını container'a körlemesine taşıma. Zapret ülke değiştirmez; sert IP/geoblock veya datacenter reddinde yabancı yedek ayrı konudur.

**Başarı:** doğrudan VDS, yeni Trojan/TUN ve gerçek Wattpad giriş/okuma sonuçları karşılaştırıldı; SSH/ThinLinc/Minecraft/Jitsi korunarak yalnız kendi değişikliği geri alınabiliyor.

### Parça 7 — Yabancı yedek, bağımsız kota ve izinli otomasyon

**İstem:** “Önce mevcut VDS kabulünü bitir. Sonra ücretsiz+kartsız+Docker+en az100 GB/ay+VPN izninin her birini resmî güncel kaynak ve gerçek tahsisle doğrula. İkinci container değil ikinci bağımsız trafik hakkı ara. Hax/Telegram otomasyonunu yalnız açıkça izinli resmî API/akış varsa tasarla.”

- Araştırılan `hax.co.id` ile kullanıcının yazdığı `hax.id` aynı hizmet varsayılmadı. Boş stok, IPv6-only erişim, konum/port/Docker kısıtları ve VPN koşulları doğrulanmalı.
- Telegram botunun varlığı otomatik yenilemenin izinli olduğuna kanıt değildir. CAPTCHA, hesap/kota veya anti-bot kısıtlarını aşma yok; gerekirse hatırlatma/insan onayı.
- Hugging Face Docker uygunluğu önceki resmî doküman kontrolünde ücret/eligibility engeline takıldı; ücretsiz çözüm olarak sunulmadı. Back4app yaşam süresi/sleep şartları güncel resmî kaynaktan yeniden doğrulanmalı; dakika50 redeploy uygulanmadı. SnapDeploy önceki koşullarında VPN/proxy/tunnel yasağı nedeniyle uygun sayılmadı.
- `vds-baslangic/ARASTIRMA.md` tarihli araştırmadır. Tor çıkışı çalışma alanında doğrulandı; denenen onion sayfaları zaman aşımına uğradı. “Tüm dark web tarandı / başka sağlayıcı yok” sonucu çıkarılamaz. VDS'ye Tor kurulmadı.

**Başarı:** gerçek tahsis, izin, en az100 GB ikinci bağımsız kota ve erişim/yenileme ölçülmüş. Bunlar yoksa “araştırıldı, henüz bulunmadı” denir.

### Parça 8 — Topluluk hizmeti kararı

**İstem:** “Kişisel denemeyi topluluk hizmetiyle karıştırma. S-UI production uyarısını ve istemci EOL durumunu değerlendir; uygun yönetim/güvenlik çözümü, sağlayıcı izni, dayanıklı kullanıcı kotası, iptal/rotasyon, abuse ve veri politikası olmadan anonim public kayıt açma.”

Bağımsız güvenlik incelemesi, kapasite/ücret modeli ve geri dönüş tatbikatı ayrıca gerekir. “Sınırsız, anonim, no-logs, kesintisiz ücretsiz VPN” garantisi verilmez.

## 6. Yeni sohbete yapıştırılacak ana istem

Aşağıdaki metni, bu repoya veya bu temiz ZIP'e erişim verdiğin **yeni sohbetin ilk mesajına** yapıştır:

```text
Türkçe devam et. Bu repo önceki uzun çalışmanın temiz devridir. Önce kök README.md'yi,
trojan-panel-plan/durum.json'u, HIZLI_YAYIN.md'yi ve mualiy-yayinla.py kodunu oku.
Kaynaklar dosyalardır; eski sohbeti görüyormuş gibi davranma. Önceki rapor, kullanıcı
beyanı ve bu devirdeki yerel testleri birbirine karıştırma.

Yakın hedef: kendi Türkiye VDS'mdeki MEVCUT Docker S-UI v1.6.7 panelini ve değiştirdiğim
yönetici parolasını/DB'yi koruyarak panel + Trojan/TLS yayınını hızla bitirmek.
/opt/mualiy-sui ve DB korunacak. Bootstrap, parola reseti, Ubuntu yükselticisi veya
“silip baştan kur” önerme. Ubuntu 26.04.1/resolute terminalde görüldü ve başarılı reboot'u
ben bildirdim; reboot'u hâlâ bildirilmemiş sayma. Kernel/paket/servis sağlığı bağımsız
ölçülmedi. SSH Security Violation için sağlayıcı-modifiye paket/imza açıklaması benim
beyanım; kanıtlanmış teknik neden diye sunma.

Seçimler kesin: Android'de kurulu MikuBox 1.4.3-UwU-2/NekoBox; Windows 10/11.
Tam cihaz VPN/TUN ve değişmiş genel çıkış IP'si istiyorum, HTTP/SOCKS uygulama proxy'si
istemiyorum. Alan adı mualiy.net; panel.mualiy.net Access arkasında, sub.mualiy.net
etkileşimli Access olmadan özel abonelik, vpn.mualiy.net DNS-only A38.210.77.17.
Trojan doğrudan TLS/TCP 8443; önce güncel socket VE Docker mapping kontrol edilecek.
80/443, SSH, ThinLinc/var olan cloudflared-tunel, Minecraft/Crafty, Jitsi, diğer Docker
projeleri, rotalar ve resmî /opt/zapret2 korunacak. Yeni, ayrı mualiy-panel Tunnel /
mualiy-sui-tunnel connector kullanılacak; cloudflared service install yapma.

mualiy-yayinla.py'nin UA düzeltmesi mevcut: MualiySetup/1.1. Önceki deneme Access
kontrolünde durdu; VDS'de sonraki deneme bilinmiyor. Access'i kapatarak geçiştirme.
Gerçek CA/Docker/VDS yayını veya cihaz TUN kabulü tamamlanmış varsayılmasın.
Eski native ozgur-trojan/s-ui/s.ui/sing-box temizliğine yetki verdim; yeni panel değil.
Arşivleyici teslim edildi ama uzak sonucu bilinmiyor. Yayını gereksiz temizlik kapısına
bağlama; gerçek port çakışmasını dar kapsamda çöz. DB/state/özel yedekleri silme.

Parola, SSH özel anahtarı, DNS/Tunnel/API/Telegram token'ı, DB, state.json, özel log,
Trojan/abonelik linki veya QR'ı sohbette isteme. Gizli giriş yalnız VDS terminalinde.
Erişmediğin hesabı/sunucuyu test ettim deme. Önce en küçük salt-okunur sağlık/health/
port çıktısını bir grupta iste; sağlıklıysa README Parça 2'den mevcut yayına devam et.
Aynı domain/OS/istemci/taşıma sorularını tekrar sorma. Kısa, çalıştırılabilir tek parça
adım ver; sonuç gelince durum.json ve ilgili kanıtı güncelle, manifestleri yenile.

Sonra sırasıyla Android ve Windows cihaz geneli çıkış-IP/DNS/IPv6/UDP/gerçek uygulama
kabulü, abonelik, yenileme, gerekirse mevcut multisplit:pos=2 Wattpad adayı ve daha
sonra yabancı yedek. İkinci yedek bağımsız en az100 GB hak olmalı; ücretsiz+kartsız+
Docker+VPN izni doğrulanmadan bulundu deme. Hax tahsisi/izinli Telegram yenilemesi
ve Back4app dakika50 redeploy henüz yapılmadı. Topluluk VPN'i tamamlandı sayılmasın.
```

**Bir parça bittikten sonraki kısa devam istemi:**

```text
README'deki sıradaki parçaya geç. Önce az önceki sonucu “kullanıcı / yerel test /
gerçek VDS / henüz bilinmiyor” diye sınıflandır. Tamamlanan işi tekrarlama, yeni bir
kurulum zinciri başlatma. Yalnız gereken sonraki adımı, neyi değiştireceğini ve başarı
ölçütünü ver. Sırları isteme; sonucu görünce durum.json ve kanıt/manifeste işle.
```

## 7. Klasör yapısı ve her dosyanın açıklaması

```text
repo-koku/
├── README.md                     ← bu tek kapsamlı devir belgesi
├── .gitignore                    ← yeni public-kaynak hijyeni
├── DEVIR_TEST_SONUCLARI.json      ← bu devirde yeniden yapılan kontroller
├── SHA256SUMS                    ← diğer 83 izlenen dosyanın bütünü için sağlama
├── trojan-panel-plan/            ← GÜNCEL yayın + sınırlı temizlik + tarihçe
├── wattpad-inceleme/              ← seçilmiş aday ve kanıt; otomatik uygulama yok
├── vds-baslangic/                 ← tarihsel ön kontrol ve barındırma araştırması
├── tr-vds-kurulum/                ← ESKİ native kaynak/test arşivi, yeniden kurma
└── free-vpn-engineering/          ← ESKİ WSS uygulama-proxy prototipi
```

**Durum kodları:** **AKTİF** güncel devamda kullanılabilir; **KOŞULLU** yalnız belirtilen kapsam/yetkiyle; **TEST** test kaynağı; **KANIT** tarihsel sonuç; **ARŞİV** güncel VDS'ye uygulanmayacak tarihçe/prototip; **ARAŞTIRMA** yeniden doğrulanması gereken not; **META** envanter/bütünlük/lisans. Arşiv kodları “şimdi kurulacak alternatif” değildir.

### 7.1 Kök — 5 dosya

| Dosya | Durum | Amaç / neden tutuldu? |
|---|---|---|
| `README.md` | AKTİF | Bu kapsamlı devir: hedef, durum, kurallar, görev/istemler, tüm dosya envanteri, çıkarılanlar ve yükleme yöntemi |
| `LICENSE` | META | Önceden var olan kök lisans kaydı; alt ağaçlardaki lisans ve üçüncü taraf bildirimleri ayrıca korunur |
| `.gitignore` | META | Token/DB/anahtar/client export'u, ham yükleme, cache/log ve ZIP'lerin yanlışlıkla eklenmesini azaltır; güvenlik garantisi değildir |
| `DEVIR_TEST_SONUCLARI.json` | KANIT — DEVİR YEREL | Bu temiz kopyada yeniden yapılan 87 test, Go ve native fixture/statik/secret-review sonuçları ile yapılmayanların makine okunur özeti |
| `SHA256SUMS` | META | Kendi dışındaki izlenen kaynak dosyalarının SHA-256'sı; bütünlük kontrolüdür, kriptografik yayıncı imzası değildir |

### 7.2 `trojan-panel-plan/` — 20 dosya

| Dosya | Durum | Amaç / neden tutuldu? |
|---|---|---|
| `mualiy-yayinla.py` | **AKTİF** | Mevcut paneli doğrular; özel yedek, DNS-01 CA, S-UI API TLS/Trojan/client,8443, ayrı Tunnel, yenileme ve özel link export'u. Root/TTY ve açık `--apply`; gerçek değişiklik yapar |
| `termux-yayin-baslat.sh` | **AKTİF** | Termux/VDS için kopyala-yapıştır başlatıcı. Sabit main commit'indeki yayın dosyasını HTTPS+SHA-256 ile doğrular; `curl | sh` kullanmaz, sembolik/beklenmeyen hedefi ezmez ve TTY dışında yayın başlatmaz |
| `mualiy-sifirla-ve-yayinla.py` | **KOŞULLU — AÇIK RESET ONAYI** | Yalnız açık sıfırdan kurulum onayında, doğrulanmış eski Mualiy panel/tunnel state'ini silmeden root-özel arşive taşır; loopback yeni panel/admin kurar ve ardından SHA-256 doğrulanmış normal yayın aracını başlatır. Bilinmeyen mount/label/state'te durur |
| `HIZLI_YAYIN.md` | **AKTİF** | Güncel yayın rehberi; Access/YENİ Tunnel/dar DNS token, UA düzeltmesi, Termux başlatıcı, açık onaylı reset istisnası, kullanım ve kanıt sınırları. Hazır ayarları tekrarlamama/reboot sonrası devam notu eklendi |
| `durum.json` | **AKTİF** | Taşınabilir makine özeti; son kullanıcı reboot26.04.1 bildirimi, kesin seçimler, korunacaklar ve açık işler. Stale yinelenen upgrade anlatımı yerine son durum normalize edildi |
| `mualiy-eski-servis-temizle.py` | KOŞULLU | Yetki verilmiş dört ESKİ native birimi/doğrulanmış yolları kontrol eder ve root-özel arşive taşır; yeni paneli korur. `--check` varsayılan, `--apply` değişiklik yapar; uzak sonuç bilinmiyor |
| `ESKI_SERVIS_TEMIZLIGI.md` | KOŞULLU | Eski native kapsamı, korumalar, arşiv ve sınırlamalar; yayın öncesi gereksiz geniş temizlik kapısı değildir |
| `mualiy-sui-panel.sh` | **ARŞİV — YENİDEN ÇALIŞTIRMA** | İlk loopback panelinin özgün kurucusu. Beklenen Compose/marker/UID yapısını denetleyebilmek ve fixture testleri için tutuldu; mevcut VDS'yi yeniden kurmak için değil |
| `PANEL_ILK_ASAMA.md` | ARŞİV | İlk panelin mimari kayıt belgesi. Yeniden kurulum komutları/varsayılan parola çıkarıldı; DB/mount/restart:no gerekçesi ve açık tarihçe uyarısı kaldı |
| `tests/test_publish_safety.py` | TEST |23 offline guard: doğru panel/port, local Docker socket, bilinmeyen port sahibine dokunmama, secret-file, TLS çakışması, Access/UA reddetme, ilk Trojan kullanıcısının inbound oluşturulurken eklenmesi, kayıtsız core inbound'ının yalnız doğrulanmış panel yeniden başlatılarak temizlenmesi ve cert/key metadata ile container içi okunabilirlik kontrolleri; geçici yol taşınabilir yapıldı |
| `tests/test_termux_launcher.py` | TEST |GitHub erişimi/sudo olmadan fake `curl` ile başlatıcının SHA-256 doğrulamasını, dry-run'ın hedefe dokunmamasını ve TTY dışındaki yayının engellenmesini denetler |
| `tests/test_fresh_reset.py` | TEST |Gerçek Docker/VDS kullanmadan reset aracının loopback compose yapısını, sahiplik işareti/mount korumalarını, arşivleyerek korumayı, yeni admin doğrulamasını, yayıncı SHA-256 pinini ve sır/tehlikeli silme korumalarını denetler |
| `tests/test_publish_native.py` | TEST — AÇIK OPT-IN | Linux amd64, non-root gerçek native fixture; `--binary`/`SUI_TEST_BINARY`, kesin binary hash, loopback, geçici DB/CA ve isteğe bağlı **yeni** rapor. Binary indirmez, canlı VDS kullanmaz, tarihsel raporu ezmez |
| `tests/test_cleanup.py` | TEST |20 offline cleanup fixture; gerçek Docker/systemctl çalışmaz, fake dosyalar geçici dizindedir; yeni panel/mount/process/alias korumalarını denetler |
| `tests/test_bootstrap.py` | TEST / ARŞİV |14 ilk-kurucu fixture testi. Hedef/lock geçici yola çevrilir ve Docker/curl/ss mock'tur. `install -o/-g` için root gerekir; yalnız atılabilir test ortamında, VDS'de değil |
| `YAYIN_TEST_SONUCLARI.json` | KANIT — ÖNCEKİ YEREL | Önceki16 guard + native API/Trojan/abonelik özeti, UA ve yapılmayanlar. Yinelenen ayrı native raporun içeriği zaten bu dosyadaki `real_native_fixture` alanında korunuyor |
| `ACCESS_DUZELTME_TEST.json` | KANIT — ÖNCEKİ YEREL | urllib403 / setupUA302 farkı, eski/yeni betik hash'i ve önceki kamu DNS/Access gözlemi; ham ekran görüntüsü yok, güncel VDS tekrar denemesi kanıtı değil |
| `TEMIZLIK_TEST_SONUCLARI.json` | KANIT — ÖNCEKİ YEREL | Temizlik aracının önceki20 mock testi/derleme/non-root koruması ve uzak sonucun bilinmediği kaydı |
| `TEST_SONUCLARI.json` | KANIT — ÖNCEKİ YEREL | İlk bootstrap14 mock testi ve ayrı upstream native smoke; kullanıcının panel/şifre bildirimi. Mevcut Docker runtime doğrulaması değildir |
| `SHA256SUMS` | META | Bu klasördeki diğer 19 dosyanın güncellenmiş manifesti; `cd trojan-panel-plan && sha256sum -c SHA256SUMS` |

### 7.3 `wattpad-inceleme/` — 3 dosya

| Dosya | Durum | Amaç / neden tutuldu? |
|---|---|---|
| `KURULUM.md` | KOŞULLU / KANIT | Eski yeniden-kurulum akışı yerine seçilen aday, mevcut resmî kurulum kanıtı, Docker çıkışı sınırı ve kontrollü sonraki görevi anlatır; önceki installer/disable/kaldırma/native-test adımları çıkarıldı |
| `analiz.json` | KANIT — KULLANICI LOGU ANALİZİ |11.157 satır/2.597 özet, TLS 1.2/1.3 adayı ve resmî install seçimleri; ham logların pakette olmadığı ve runtime kabulünün yokluğu işaretli |
| `zapret2-wattpad-v1.0.7.conf` | KOŞULLU — PASİF ÖRNEK | Upstream v1.0.7 tabanlı tam aday config; `NFQWS2_ENABLE=0`. Lisanslı, hash'i değişmedi. Live config üzerine otomatik kopyalanmaz, UID/container izolasyonu sağlamaz |

### 7.4 `vds-baslangic/` — 6 dosya

| Dosya | Durum | Amaç / neden tutuldu? |
|---|---|---|
| `vds-on-kontrol.sh` | KOŞULLU — SALT OKUNUR | Sistem/ağ ön-kontrolü; kurulum/firewall/servis değişikliği yapmaz. İsteğe bağlı ağ istekleri ve özel0600 rapor üretir. Kapsamlı yeniden tanılama için değil, gerekirse yeniden kullanılabilir araç |
| `test_preflight.py` | TEST |8 mock test; tanılama komutlarının güvenli argüman, dosya izni ve sırsız çıktı davranışları |
| `README.md` | ARŞİV / ARAÇ REHBERİ | İlk ön-kontrol kullanımını açıklar. Eski “kurulmadı/sürüm bilinmiyor” durumunun tarihsel olduğu en başta belirtildi |
| `ARASTIRMA.md` | ARAŞTIRMA | FreeVPS/öğrenci/sponsorluk/Hax/Woiden ve Tor/onion notları; tahsis yapılmadı, tam tarama değil. Koşullar yeniden doğrulanır; araştırma geçmişini kaybetmemek için tutuldu |
| `TEST_SONUCLARI.md` | KANIT — ÖNCEKİ YEREL | Ön-kontrolün önceki8 fixture testi ve kapsamı; güncel sunucu raporu değildir |
| `SHA256SUMS` | META | Diğer5 dosyanın güncellenmiş bütünlük manifesti |

### 7.5 `tr-vds-kurulum/` — 12 dosya; **eski native tasarım**

Bu klasör yeni Docker paneline **kurulmayacak**. Tam kaynak, eski unit/yol kökenini ve önceki TUN/protokol deneylerini denetlemek için bağımlılıklarıyla tutuldu. Dosyalar SFA/native akışını içerir; MikuBox/güncel panel talimatı değildir.

| Dosya | Durum | Amaç / neden tutuldu? |
|---|---|---|
| `vds.py` | ARŞİV — YENİDEN KURMA | Eski ayrı kullanıcı/systemd Trojan ve isteğe bağlı UID-sınırlı özel zapret kurucusu; config/rollback/test üretimi. Eski servislerin kökenini ve test edilen tasarımı açıklamak için tutuldu |
| `download.py` | ARŞİV / BAĞIMLILIK | Eski kurucunun resmi sürüm/hash kilitli indirme ve güvenli sınırlı arşiv açma yardımcısı; offline testler bunu import eder |
| `versions.json` | META / ARŞİV KİLİT | sing-box 1.14.4 ve zapret2 v1.0.7 arşiv/binary SHA-256 kilitleri; eski testlerin tekrarlanabilirliği |
| `test_offline.py` | TEST |17 güvenlik/config testi; indirmeler mock, root/service değişikliği yok. TUN config alanları gerçek telefon kabulü değildir |
| `test_netns.py` | TEST — İZOLE/ROOT | Yalnız taze network namespace içinde yerel protokol/NFQUEUE deneyleri. Gerçek VDS ağına karşı varsayılan çalıştırılmaz; devirde tekrar koşulmadı |
| `test_internet.py` | TEST — AĞ GEREKTİRİR | Eski native tasarımın yerel relay üzerinden kamu hedefi karşılaştırması; uzak VDS/Android kabulü değil. Devirde tekrar koşulmadı |
| `README.md` | ARŞİV | İlk native kurulum/SFA rehberi. Üstte güçlü “yeniden çalıştırma; Docker/MikuBox geçerli” uyarısı var; içteki24.04/kurulmadı cümleleri tarihsel |
| `TEST_SONUCLARI.md` | KANIT — ÖNCEKİ YEREL |17 offline,15 izole protokol/NFQUEUE ve3 yerel internet testi, ortam/başarısızlık sınırları; güncel VDS kanıtı değil |
| `test-results.json` | KANIT — ÖNCEKİ YEREL | Aynı tarihsel deneyin makine okunur sonucu ve yapılmayanlar; yeni devir testi diye sunulmadı |
| `THIRD_PARTY_NOTICES.md` | META / LİSANS | sing-box GPL/ad-ilişki bildirimi, zapret2 MIT ve kaynak/sürüm bağlantıları; dağıtım yükümlülükleri nedeniyle korunur |
| `LICENSE` | META / LİSANS | Bu eski Python paketinin GPLv3 lisans metni; kaldırılmadı |
| `SHA256SUMS` | META | Diğer11 dosyanın güncellenmiş manifesti |

### 7.6 `free-vpn-engineering/` — 38 dosya; **eski uygulama-proxy prototipi**

Bu klasör tam cihaz VPN/TUN değildir ve mevcut VDS'ye alternatif kurulum olarak sunulmaz. Go kaynakları, testler, UI, Docker/Render tarifleri ve lisansları birbiriyle ilişkili olduğundan bütün tutuldu. **Docker/Render/Actions dağıtımı yapılmış sayılmaz.**

| Dosya | Durum | Amaç / neden tutuldu? |
|---|---|---|
| `README.md` | ARŞİV | Eski WSS uygulama-proxy kullanımı ve izin sınırları; başına güncel Docker/TUN ayrımı ve nested Actions uyarısı eklendi |
| `SECURITY.md` | ARŞİV / GÜVENLİK | Prototipin kimlik, hedef kısıtları, tehdit modeli ve operasyon sınırları; bağımsız güvenlik denetimi değildir |
| `LICENSE` | META / LİSANS | Prototip GPLv3 lisans metni |
| `THIRD_PARTY_NOTICES.md` | META / LİSANS | sing-box, Go/base image ve kaynak sunma/ad kullanımı bildirimleri; lisans bütünlüğü için tutuldu |
| `go.mod` | META / DERLEME | Go modül tanımı ve dil alt sınırı1.26.0; tercih edilen test toolchain1.27.4 |
| `versions.json` | META / KİLİT | sing-box 1.14.4 amd64/arm64 arşiv hash'leri ve test edilen Go sürümü |
| `Makefile` | ARŞİV / GELİŞTİRME | Yalnız bu alt ağaç kökünden test/build/e2e/docker hedefleri. `docker` hedefi değişiklik yapar; mevcut VDS'de çalıştırılmaz |
| `Dockerfile` | ARŞİV / TARİF | Go gateway + hash-kilitli sing-box image tarifi; gerçek container build'i bu ortamda doğrulanmadı |
| `compose.yaml` | ARŞİV / TARİF | Prototipi localhost'a bağlayan örnek Compose; güncel `mualiy-sui` projesi değildir |
| `render.yaml` | ARŞİV / TARİF | İzin koşullu Render Blueprint; birleşik repo kökü ve güncel sağlayıcı koşulları uyarlanmadan deploy edilmez |
| `.dockerignore` | META | Eski image build bağlamından sır/test/cache/belge dışlama |
| `.gitignore` | META | Bu alt ağacın eski sır/cache/export dışlama kuralları; yeni kök ignore'u da uygulanır |
| `.env.example` | META / BOŞ ŞABLON | Gerçek parolası boş örnek değişkenler. Tek izinli `.env` benzeri dosyadır; gerçek env değildir |
| `.github/workflows/ci.yml` | ARŞİV / ŞABLON | Eski race/vet/Python/WSS/Docker CI tarifi. **Repo kökünde değil, otomatik çalışmaz**; yollar bu alt ağacı root varsayar. Bilinçli uyarlama olmadan taşınmaz |
| `.github/workflows/health.yml` | ARŞİV / ŞABLON | Eski opsiyonel6 saatlik readiness kontrolü; anti-sleep veya kesintisizlik çözümü değil. Nested olduğu için bu birleşik repoda etkin değil |
| `cmd/gateway/main.go` | ARŞİV / KAYNAK | Gateway CLI/başlatma, core alt süreci ve kapanış yaşam döngüsü |
| `internal/config/config.go` | ARŞİV / KAYNAK | Env doğrulama, kullanıcı/parola/path/port politikası ve sing-box sunucu JSON'u |
| `internal/config/config_test.go` | TEST | Yapılandırma/politika birim testleri; `SING_BOX_TEST_BINARY` verilirse gerçek core şema kontrolü de yapar |
| `internal/gateway/server.go` | ARŞİV / KAYNAK | HTTP/WS geçidi, sağlık/statik uçlar, tünel/handshake/zaman sınırları |
| `internal/gateway/server_test.go` | TEST | Gateway rota, limit, handshake ve kapanış davranışları |
| `internal/gateway/web/index.html` | ARŞİV / UI | Eski prototipin durum ana sayfası; S-UI yönetim paneli değildir |
| `internal/gateway/web/status.js` | ARŞİV / UI | Prototip readiness bilgisini sayfaya taşıyan küçük script |
| `internal/gateway/web/style.css` | ARŞİV / UI | O prototip ana sayfasının stilleri |
| `scripts/common.py` | ARŞİV / BAĞIMLILIK | Özel dosya yazma, env okuma ve WS yolu doğrulaması; testlerin ortak yardımcısı |
| `scripts/init_env.py` | ARŞİV / YARDIMCI | Yeni rastgele prototip parolası/WS yolu olan özel env üretir; gerçek env repoya konmaz |
| `scripts/client.py` | ARŞİV / YARDIMCI | Prototip için TLS doğrulamalı HTTP/SOCKS istemci config'i; **TUN üreticisi değil** |
| `scripts/users.py` | ARŞİV / YARDIMCI | Eski prototip için ayrı kullanıcı/parola JSON'u üretir; kalıcı kota/self-service yönetim değildir |
| `scripts/fetch_core.py` | ARŞİV / GELİŞTİRME | Resmî sabit sing-box arşivini hash doğrulayarak indirir; binary pakette yok |
| `scripts/healthcheck.py` | ARŞİV / YARDIMCI | Bir HTTPS readiness isteği; hizmeti uyandırabilir ama sürekli canlı tutmaz, gerçek VPN egress testi değildir |
| `tests/test_scripts.py` | TEST |10 yardımcı güvenlik testi; URL içindeki `user:pass` vb. değerler **sentetik negatif fixture**, gerçek kimlik bilgisi değil |
| `tests/test_users.py` | TEST |2 çoklu kullanıcı üretici/doğrulama testi |
| `tests/e2e.py` | TEST — AĞ GEREKTİRİR | Yerel TLS terminator + gerçek sing-box ile25 WSS/proxy/ret/kapanış kontrolü; kamu DNS/example.com gerekir. Devirde yeniden koşulmadı |
| `tests/docker_smoke.py` | TEST — DOCKER GEREKTİRİR | Prototip image'ın non-root/read-only çalışma smoke testi; dosya var, bu ortamda çalıştırılmadı |
| `docs/DESIGN.md` | ARŞİV | Eski WSS prototip mimarisi ve kararları; güncel S-UI mimarisi değildir |
| `docs/ROADMAP.md` | ARŞİV | İlk prototipten topluluk hizmetine eski yol haritası; hedefleri “tamamlandı” yapmaz |
| `docs/TEST_RESULTS.md` | KANIT — ÖNCEKİ YEREL | Önceki25E2E,12Python, Go/schema sonuçları ve yapılmayanlar; devirde yeni testlerle karıştırılmıyor |
| `docs/e2e-results.json` | KANIT — ÖNCEKİ YEREL | O25 E2E kontrolünün makine okunur listesi; VDS/Render/TUN kanıtı değil |
| `PROJECT_MANIFEST.sha256` | META | Bu klasördeki diğer 37 dosyanın güncellenmiş bütünlük manifesti |

## 8. Çıkarılanlar ve devir sırasında yapılan düzeltmeler

### Temiz paketten tamamen çıkarılan / hiç alınmayan dosyalar

Aşağıdakiler **temiz klasör/ZIP içinde yoktur**. “Paketten çıkarma”, kullanıcının canlı VDS'sinde veya ham yükleme alanında uzaktan silme yapıldığı anlamına gelmez. Paylaşılacak kaynak yalnız bu temiz pakettir; eski çalışma alanının tamamını yükleme.

| Dosya / yol | İşlem ve neden |
|---|---|
| `trojan-panel-plan/YAYIN_NATIVE_TEST.json` | Temiz kopyadan **silindi**. Aynı eski native sonuç zaten `YAYIN_TEST_SONUCLARI.json.real_native_fixture` içinde; gereksiz ikilik. Native test artık bu tarihsel dosyayı otomatik yazmıyor |
| `ozgur-ag-vpn-engineering.zip` | Alınmadı; eski 38 dosyalık prototip paketinin yinelenen/stale arşivi; kaynaklar yapısıyla mevcut |
| `tr-vds-trojan-zapret2-paketi.zip` | Alınmadı; eski 12 dosyalık native arşiv; yeniden kurulumla karışmasın, kaynakları işaretli olarak mevcut |
| `vds-baslangic-paketi.zip` | Alınmadı; eski 6 dosyalık ön-kontrol arşivi; kaynakları mevcut |
| `uploads/Screenshot_20261115_231741_Termux.jpg` | Alınmadı; ham terminal ekran görüntüsü, özel operasyon ayrıntısı riski. Yalnız sırsız çıkarım korundu |
| `uploads/image-1.png` | Alınmadı; ham görsel/operasyon kanıtı, kaynak için gereksiz |
| `uploads/image-2.png` | Alınmadı; aynı gerekçe |
| `uploads/image-3.png` | Alınmadı; aynı gerekçe |
| `uploads/image-4.png` | Alınmadı; aynı gerekçe |
| `uploads/image-5.png` | Alınmadı; aynı gerekçe |
| `uploads/output.txt` | Alınmadı; ham terminal çıktısı. Resmî zapret2 kurulum seçimlerinin sırsız özeti `analiz.json` içinde |
| `uploads/zapret2-wattpad.log` | Alınmadı; ham uzun tarama/ağ logu. Aday ve analiz özeti tutuldu; ham veriden yeniden analiz bu pakette tek başına mümkün değil |
| `.cache/` ve içindeki S-UI/sing-box/Go/Tor/araştırma dosyaları | Alınmadı; büyük, ortama özgü ve geçici bağımlılıklar. Gerekirse resmî sürüm/hash ile ayrı temin edilir |
| `__pycache__/`, `*.pyc`, `.venv/` ve benzeri üretilenler | Alınmadı; kaynak değil, taşınabilir değil |
| `vds-local-tests/` | Alınmadı; boş klasör |
| `.config/`, `.sudo_as_admin_successful` | Alınmadı; çalışma ortamına ait kişisel/sistem durumu, proje kaynağı değil |
| `tests/native_publish_failure.log` | Pakette yok; önceki hata tanısı daha önce silinmişti. Yeni native fixture özel tanı logunu repoya bırakmıyor |
| VDS DB/state/token/anahtar/client/abonelik export'ları | Hiç alınmadı; sır/canlı veri. Bu çalışma alanında VDS'den bunları alma veya VDS'de silme yapılmadı |

### Tutulan ama eski olanlar neden silinmedi?

- İlk kurucu ve native paket, mevcut marker/DB/mount/servis yollarının nereden geldiğini ve temizliğin neyi hedeflediğini açıklıyor; test bağımlılıklarını koparmamak için kaynaklarıyla tutuldu. **ARŞİV / yeniden çalıştırma** etiketi rehberlerin başında ve envanterde var.
- WSS prototipi çalışan bir mühendislik denemesinin kaynağıdır; lisans/derleme/UI/test dosyalarını rastgele silmek projeyi eksik bırakırdı. Ayrı hedef olarak işaretlendi; güncel TUN diye pazarlanmıyor.
- Tarihli araştırma ve geçmiş test raporları tekrarlanan araştırma/hatalı başarı iddiasını önlemek için tutuldu. Yeni kontrollerden ayrı etiketliler.
- Nested Actions tarifleri otomatik etkinleşmediği için güvenli tarihsel şablon olarak kaldı; güncel repo kökü CI'ı varmış gibi gösterilmedi. İstenirse yeni görevde bilinçli olarak köke uyarlanabilir.
- Lisans ve third-party notices dosyaları yinelenen metin gibi görünse de ilgili alt projelerin dağıtım bütünlüğüdür; çıkarılmadı. Bütün repo tek yeni lisansla yeniden lisanslanmış sayılmaz.

### Devir kopyasında yapılan somut düzeltmeler

1. `durum.json` son kullanıcı bildirimine göre normalize edildi: **başarılı reboot biliniyor**, sağlık bağımsız ölçülmedi; sağlayıcı/SSH nedeni yalnız kullanıcı açıklaması. Bu son durum özgün aktif durum dosyasına da işlendi.
2. Üç fixture testindeki `/home/user/.cache` zorunluluğu kaldırıldı; standart geçici dizin kullanılıyor. Runtime yayın/temizlik/ilk-kurucu betikleri değiştirilmedi.
3. Native fixture açık binary seçimi + kesin hash + non-root + tüm dinleyiciler loopback + geçici DB/CA + isteğe bağlı yeni rapor kullanır. Canlı DB düzenleme talimatı değildir; kendi geçici ve henüz başlamamış DB'sinde listen adresini kısıtlar.
4. İlk-aşama belgesindeki yeniden kurulum/varsayılan parola talimatları ve Wattpad rehberindeki eski yeniden-installer/native-test/otomatik disable/kaldırma zinciri çıkarıldı.
5. Eski README/araştırma/test/CI dosyalarına tarihsel kapsam uyarıları eklendi; ham yükleme referansları “pakette yok” diye açıklandı. Raporlara tarihsel kanıt metadata'sı eklendi.
6. Kök `.gitignore`, bu tek kapsamlı README, yeni devir test raporu ve tam kök SHA-256 manifesti eklendi. Alt proje manifestleri içeriklere göre yenilendi.
7. Gerçek sır araması temiz paketin tüm dosyalarında yapıldı; private-key/provider-token/credential-URL ve şüpheli atama örüntüleri gözden geçirildi. Görülen sabit örnekler test/şablon/kod değerleri olarak ayrıldı. **Bu, eksiksiz bağımsız sır/güvenlik denetimi garantisi değildir.** Alan adı, public VDS IP'si ve `neo` kullanıcı adı bilinçli operasyon bağlamı olarak kaldı; anonimleştirilmiş paket değildir.

## 9. Testler: tarihsel sonuç ile yeni kontrol ayrımı

### Bu devirde gerçekten yeniden yapılanlar

| Kontrol | Sonuç / kapsam |
|---|---|
| Güncel yayın güvenlik testleri |16/16; offline mock |
| Eski native temizlik güvenlik testleri |20/20; offline mock |
| İlk-kurucu fixture testleri |14/14; yalnız bu sandbox'ta root + geçici hedef/lock + mock Docker/curl/ss |
| Eski native config/offline testleri |17/17; kurulum/ağ yok |
| Ön-kontrol fixture testleri |8/8; gerçek ağ/servis komutları mock |
| Eski WSS Python yardımcı testleri |12/12 |
| **Python toplamı** |**87/87** |
| Go `test -race -cover -count=1 ./...` |Geçti; config%93,5 / gateway%92,4. CLI'nin doğrudan unit coverage'ı%0; eski E2E raporu ayrıdır |
| Go `vet`, gateway derlemesi |Geçti; Go 1.27.4. Çıktı binary'si pakete alınmadı |
| Gerçek pinned core config şeması |Go testi içinde önceden resmî hash doğrulaması yapılmış sing-box 1.14.4 cache binary'siyle geçti; cache/binary pakette değil |
| Gerçek native S-UI fixture |Yeniden geçti: login/cookie/same-origin, SQLite yedeği, TLS/inbound/client, iki kez idempotent kurulum, admin parolası korunması, CA+hostname doğrulamalı Trojan TCP echo, özel örnek abonelikte doğru Trojan/domain. Geçici fixture durdu |
| Statik / bütünlük / paket hijyeni |Python/JSON/YAML/shell/JS ve rehber shell sözdizimi, manifestler, ignore örnekleri ve ZIP içerik denetimi; ayrıntı makine raporunda |

**Devirde tekrar yapılmayanlar:** Eski25 WSS internet E2E'si;15 izole NFQUEUE/protokol testi;3 yerel internet testi; nfqws2 runtime dry-run; canlı DNS/Access yeniden ölçümü; Docker/Compose build/run; gerçek CA/DNS token/Tunnel hesabı; VDS sağlık/yayın/yenileme; dış8443; gerçek Android/Windows TUN/UDP/ses/oyun/istikrar. Eski raporlar bu boşlukları doldurmuş sayılmaz.

### Yerelde güvenli tekrar — repo kökünden

Normal kullanıcıyla87 testin **73'ü** (root isteyen14 bootstrap fixture aşağıda ayrıdır):

```bash
(cd trojan-panel-plan && python3 -B -m unittest discover -s tests -p 'test_publish_safety.py' -v)
(cd trojan-panel-plan && python3 -B -m unittest discover -s tests -p 'test_cleanup.py' -v)
(cd tr-vds-kurulum && python3 -B -m unittest test_offline.py -v)
(cd vds-baslangic && python3 -B -m unittest test_preflight.py -v)
(cd free-vpn-engineering && python3 -B -m unittest discover -s tests -p 'test_*.py' -v)
```

**Yalnız atılabilir ayrı Linux test ortamında**, mevcut VDS'de değil: aşağıdaki14 test root ister; kurucu hedef/lock'u geçici fixture'a, Docker/curl/ss'yi mock'a çevirir. Üretim sunucusunda “tüm testleri sudo ile keşfet” önerilmez.

```bash
(cd trojan-panel-plan && sudo python3 -B -m unittest discover -s tests -p 'test_bootstrap.py' -v)
```

Native entegrasyon **opt-in**, normal kullanıcı ve Linux amd64 içindir. Resmî S-UI v1.6.7 Linux amd64 release arşivinin SHA-256'sı `7f6c6403eac713c2b08cd509540a9835596a7b4a79dedf23dfa71278d2f003c5`; içindeki `sui` binary SHA-256'sı `f57c3bc95b490f1c3154c5013451d98b8e74426174fd688c85052ce338413a11`. Binary pakette yoktur. Kaynağı doğrulayarak ayrı temin et; canlı panel binary/DB'sini fixture'a bağlama.

```bash
python3 -B trojan-panel-plan/tests/test_publish_native.py \
  --binary /guvenilir/test-dizini/sui
# İstersen yalnız YENİ bir JSON'a --report ver; mevcut rapor ezilmez.
```

Bu yol bir **yer tutucudur**; gerçek güvenilir test binary'sinin yoluyla değiştirilecek. `--binary` yerine `SUI_TEST_BINARY` de kullanılabilir. Test kendi geçici DB/cert'ini kurar; Docker, Cloudflare ve gerçek VDS'ye gitmez. Geçici sentetik CLI parolaları gerçek yönetici sırrı değildir.

Go 1.27.4 ve uygun yerel toolchain varsa:

```bash
(cd free-vpn-engineering && go test -race -cover -count=1 ./... && go vet ./...)
```

`SING_BOX_TEST_BINARY` verilmezse core şema alt testi skip olur; bunu çalıştı diye sayma. İsteğe bağlı `scripts/fetch_core.py` resmî/hash-kilitli binary indirir; bu ağ erişimi gerektirir. Eski WSS/NFQUEUE/internet testlerini sırf dosya adı `test_` diye canlı VDS'de topluca çalıştırma.

Bütünlük:

```bash
sha256sum -c SHA256SUMS
(cd trojan-panel-plan && sha256sum -c SHA256SUMS)
(cd tr-vds-kurulum && sha256sum -c SHA256SUMS)
(cd vds-baslangic && sha256sum -c SHA256SUMS)
(cd free-vpn-engineering && sha256sum -c PROJECT_MANIFEST.sha256)
```

Her düzenlemeden sonra ilgili alt manifesti, sonra kök manifesti yenile. Manifest hash'i dosya bozulmasını yakalar; paketin güvenilir bir kişiden geldiğini tek başına ispatlamaz. ZIP container sağlamlığı ve arşiv içerik eşitliği son paketlemede ayrıca denetlendi; izlenen dosya sayısı84'tür.

## 10. GitHub'a yapıyı bozmadan yükleme

Bu oturumdaki GitHub connector sorgusu **`unsupported`** döndü; uzak repo oluşturulmadı veya push yapılmadı. Kullanıcı yükleyecek. **ZIP dosyasını tek dosya olarak repoya yüklemek yerine içeriğini repo köküne koy.**

### Önerilen akış

1. Önce boş, tercihen **private** repo oluştur. Paket sır içermemesi için gözden geçirilse de public domain/IP ve operasyon bağlamı içeriyor. Public yapmadan önce son kişisel gözden geçirmeyi yap.
2. Temiz ZIP'i yeni boş yerel klasöre çıkar. Repo kökünde bu `README.md` ve beş proje klasörü yan yana görünmeli. Beş klasörün iç dosyalarını köke saçma, yeniden adlandırma. Fazladan `github-devri/` katmanını repo kökünün içine koyma.
3. Kök ve alt manifestleri doğrula. Gizli `.gitignore`, prototip `.env.example`, `.dockerignore` ve nested `.github` dosyalarının da kopyalandığını kontrol et.
4. GitHub web yüklemesinde `.gitignore` **uygulanmaz**; yalnız temiz ZIP'ten çıkan dosyaları seç. Ham uploads, `.cache`, eski ZIP'ler veya VDS klasörlerini sürükleme. `.gitignore`, daha önce track edilmiş sırları da geçmişten temizlemez.
5. CLI kullanıyorsan yalnız bu yeni temiz klasörde aşağıdaki örneği uygula; repo URL yer tutucusunu kendin değiştir. Token/parola URL'ye yazılmaz; kendi Git credential/SSH oturumunu kullan.

```bash
git init -b main
git add .
git status --short
git diff --cached --stat
# Bu noktada dosya listesini ve gerekirse içerik farklarını kendin gözden geçir.
git commit -m "Mualiy temiz kaynak ve yeni sohbet devri"
# Aşağıdaki URL'yi kendi GERÇEK repo URL'nle değiştir:
git remote add origin GERCEK_REPO_URL
git push -u origin main
```

Önceden sır yayımlanmışsa yalnız silme commit'i yeterli değildir: önce sırrı iptal/rotate et, sonra gerekirse geçmiş temizliğini ayrıca planla. Bu paket, daha önceki bir remote'un geçmişini taramış/temizlemiş sayılmaz; `.git/` geçmişi içermez.

### Actions ve deploy konusunda özellikle dikkat

- `free-vpn-engineering/.github/workflows/` **nested** olduğu için bu birleşik repoda GitHub tarafından root workflow olarak keşfedilmez. Otomatik CI/health/deploy açık değildir; bu bir hata gizleme değil bilinçli arşiv durumudur.
- İleride root CI istenirse yeni bir `.github/workflows/` tasarla, `working-directory`/`paths`/gerekli toolchain'i doğru ayarla ve yalnız istenen testleri etkinleştir. Eski health schedule veya Docker/Render deploy'u sessizce açma.
- `render.yaml`, Dockerfile ve Makefile eski alt ağacı root varsayar; birleşik repo düzenine uyarlanmadan deploy edildiği iddia edilmez.
- Yeni sohbete repo bağlantısını veya ZIP'i ver ve [Bölüm6'daki istemi](#6-yeni-sohbete-yapıştırılacak-ana-istem) yapıştır. Önce bu kök belge okunmalı; eski arşiv README'sinden başlanmamalı.

## 11. Resmî başvuru kaynakları ve sınırlar

Bu bağlantılar devirdeki kararların dayandığı resmî/sürüm sabitli kaynaklara giriş içindir; yeniden erişilip güncel koşulları kontrol edilmiş sayılmaz.

- S-UI v1.6.7 ve production uyarısı: <https://github.com/alireza0/s-ui/blob/v1.6.7/README.md> · <https://github.com/alireza0/s-ui/releases/tag/v1.6.7>
- Seçilen eski MikuBox release/EOL: <https://github.com/HatsuneMikuUwU/MikuBoxForAndroid/releases/tag/1.4.3-UwU-2>
- sing-box 1.14.4: <https://github.com/SagerNet/sing-box/releases/tag/v1.14.4> — canlı belgeler daha yeni alanları içerebilir; sürüm uyumu varsayılmaz.
- Cloudflare Access: <https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/>
- Tunnel run/token-file: <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/run-parameters/>
- Tunnel protokolleri: <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/protocols/>
- Cloudflare DNS-01 eklentisi/dar token: <https://certbot-dns-cloudflare.readthedocs.io/>
- Resmî zapret2 v1.0.7: <https://github.com/bol-van/zapret2/tree/v1.0.7> · <https://github.com/bol-van/zapret2/blob/v1.0.7/docs/manual.en.md>
- Ubuntu release upgrade ilkeleri: <https://ubuntu.com/server/docs/how-to/software/upgrade-your-release/> — bu bağlantı yükseltmeyi yeniden çalıştırma talimatı değildir.
- Ücretsiz sağlayıcı/Tor araştırmasının ayrıntılı, tarihli kaynakları: `vds-baslangic/ARASTIRMA.md`; tüm internet/onion alanını tüketen araştırma değildir.

**Kısa kapanış:** Kod ve güvenli yerel kanıt hazır. Kullanıcının Ubuntu 26.04.1'e geçiş/reboot ve mevcut panel/parola ilerlemesi korunacak. Gerçek public Trojan + Android/Windows cihaz geneli kabulü hâlâ bitirilecek iş. Yeni sohbet bu noktadan devam etmeli; başa dönmemeli.
