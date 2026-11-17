# Hızlı yayın: mevcut panel + Trojan/TLS

**Varsayılan yol yeni kurulum/parola sıfırlama değildir:** hazır Docker S-UI ve değiştirilmiş yönetici şifresi korunur. Ancak kullanıcı mevcut panelin bozuk olduğunu açıkça bildirip **sıfırdan kurulum** onayı verirse, aşağıdaki dar kapsamlı reset aracı eski Mualiy panel/tunnel state'ini silmeden root-özel arşive taşır ve yalnız sonra yeni panel kurar. Asistanın VDS'ye SSH erişimi yoktur. Aşağıdaki Cloudflare hazırlıklarından zaten yapılmış olanları yeniden oluşturma; yalnız eksik/doğrulanmamış olanları tamamla. Bu belge kodun ne yaptığını anlatır, tamamlanmış yayın raporu değildir.

## 0. Devir sonrası kaldığın yer

Ana bağlam [kök README](../README.md), makine özeti `durum.json`. Kullanıcı **Ubuntu 26.04.1 yükseltmesi ve başarılı reboot** bildirdi; artık “reboot bilinmiyor” diye başa dönülmez. Çalışan kernel/paket/servis sağlığı bağımsız ölçülmedi. Yayından önce yalnız kısa salt-okunur sağlık, mevcut panel health ve gerçek 8443 socket + Docker mapping kontrolü yeterli başlangıçtır; yükseltici, eski bootstrap veya geniş temizlik yeniden çalıştırılmaz.

İlk panel `restart: no` ile kurulmuştu. Reboot sonrası durmuşsa hedef projeyi/DB bağını doğrulayıp **yalnız mevcut paneli** başlat; yeniden kurma, DB/compose/private state silme. Eski native temizlik aracının VDS'de çalıştırılıp çalıştırılmadığı bilinmiyor; yayını gereksiz bir toplu temizlik turuna bağlama. Yayın betiği gerçek 8443 çakışmasını kendi sınırlı kurallarıyla denetler.

### Açık onaylı sıfırdan kurulum istisnası

Yalnız kullanıcı bozuk mevcut paneli bırakıp sıfırdan kurulum için açık onay verdiyse `mualiy-sifirla-ve-yayinla.py` kullanılabilir. Bu araç:

- sadece `.mualiy-managed` / `.managed` işareti ve Docker Compose label/mount eşleşmeleri doğru olan `mualiy-sui` ile `mualiy-sui-tunnel` kaynaklarına dokunur; bilinmeyen yapıda durur;
- eski DB, cert, compose ve varsa yayın state'ini **silmez**; `/opt` altında root-özel zaman damgalı reset arşivine taşır;
- yalnız doğrulanmış eski panel/connector container'ını kaldırır; ThinLinc, Minecraft/Crafty, Jitsi, SSH, genel Docker ve firewall'a dokunmaz;
- yeni paneli yalnız loopback `2095/2096` ile başlatır, admin hesabını yerel API üzerinden gizli girişle değiştirir ve ardından SHA-256 doğrulanmış normal yayın aracını çalıştırır.

Önce `sudo python3 /home/neo/mualiy-sifirla-ve-yayinla.py --check` ile yalnız kapsam denetlenir. `--apply`, TTY'de `SIFIRLA` onayı, yeni panel admin adı ve en az 12 karakterlik (boşluksuz, benzersiz) parolası ile sonrasında normal yayın aracının panel/Cloudflare/tunnel/sertifika sorularını ister. Token veya parola komut argümanına/repoya yazılmaz. Eski arşiv veya yarım kalan yeni dosyalar hata halinde silinmez.

## 1. Cloudflare — üç kısa hazırlık

### A. Önce yönetim panelini Access ile koru

Cloudflare Zero Trust → **Access controls → Applications → Create/Add application → Self-hosted (and private)**.

- Public hostname: **`panel.mualiy.net`**. Path alanını boş bırak; tüm hostname korunsun.
- Allow policy → Include → **Emails → yalnız kendi e-posta adresin**.
- Giriş yöntemi: One-time PIN veya zaten kullandığın güvenilir kimlik sağlayıcısı.
- `Everyone` / `Bypass` izni verme.

Önce Access, sonra Tunnel route oluşturmak panelin arada korumasız kalmasını önler. [1](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/)

### B. ThinLinc'e dokunmadan yeni Tunnel aç

Zero Trust → **Networks/Connectors → Cloudflare Tunnels → Create tunnel → Cloudflared**. Ad: **`mualiy-panel`**.

- Docker/Linux kurulum ekranındaki komutu **çalıştırma**; `--token` sonrasındaki token'ı yerel kullanım için kopyala.
- **Published application route / Public hostname** ekle:
  - Subdomain: `panel`, Domain: `mualiy.net`
  - Service type: **HTTP**
  - URL: **`127.0.0.1:2095`**
  - Path: boş
- Ek uygulama ayarlarında **Protect with Access** seçeneği varsa oluşturduğun Access uygulamasıyla etkinleştir.
- Mevcut `thinlinc-tunel` tünelini veya DNS kayıtlarını değiştirme.

Yeni connector henüz başlamadığı için tunnel geçici olarak Disconnected görünebilir. Betik kendi ayrı Docker Compose projesini başlatacak; dashboarddaki `cloudflared service install` komutunu çalıştırmayacaksın. Token, argüman/ortam değişkeni yerine özel dosyadan okunur: `--token-file`. [1](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/run-parameters/#token-file)

Abonelik de hemen çalışsın istersen **aynı yeni tünele** ikinci route ekle:

| Hostname | Service type | URL |
|---|---|---|
| `sub.mualiy.net` | HTTP | `127.0.0.1:2096` |

**`sub.mualiy.net` için tarayıcı etkileşimli Access zorunluluğu koyma.** Uygulama abonelikleri bunu açamaz. Betik tahmin edilemeyen, gizli bir abonelik adresi üretir; adres bearer-secret gibi korunmalıdır. Yönetim Access uygulaması yalnız `panel.mualiy.net` olsun, `*.mualiy.net` olmasın.

### C. Sertifika için dar yetkili DNS API Token oluştur

[Cloudflare API Tokens](https://dash.cloudflare.com/profile/api-tokens) → Create Token → **Edit zone DNS** şablonu.

- Permission: **Zone → DNS → Edit**.
- Zone resources: **Include → Specific zone → `mualiy.net`**.
- Global API Key kullanma. Token'ı sohbete gönderme.

Certbot'un DNS-01 eklentisi bu dar kapsamlı token ile doğrulama yapabilir; 80/443'ü boşaltmak gerekmez. [1](https://certbot-dns-cloudflare.readthedocs.io/)

`vpn.mualiy.net` mevcut **A → `38.210.77.17`, DNS only / gri bulut** kaydı olarak kalacak. Bu hostname'i Tunnel'a yönlendirme. Doğru bir VDS IPv6 yayını hazırlamadık; `vpn` için yanlış/eski bir AAAA kaydı ekleme.

## 2. Termux için tek-yapıştır başlatıcı

Telefonda dosya aktarmak yerine bu paketteki `termux-yayin-baslat.sh` başlatıcısı kullanılabilir. Başlatıcı, yayın aracını GitHub'daki sabit **`452833b0e4a3bd91ee643de02a884731a052c572`** commit'inden HTTPS ile indirir ve **`ccf322cc91ea882fee62eed1e4d77a1f9b4d23690bde5a045c6bb0fb1ebdcf68`** SHA-256 değeriyle doğrular. `curl | sh` kullanmaz; önceki elle aktarılmış `~/mualiy-yayinla.py` dosyasına hiç dokunmaz. Doğrulanmış yeni kopya ayrı, sürüm sabitli `~/mualiy-yayinla-ccf322cc.py` yoluna yazılır; o yol zaten varsa da beklenmeyen veya sembolik linkli dosyanın üstüne yazmaz.

Önce yalnız indirme/bütünlük yolunu denemek için VDS'de normal kullanıcıyla, doğrudan terminalde:

```bash
bash ~/mualiy-yayin-baslat.sh --dry-run
```

Bu mod paneli, Docker'ı, Cloudflare'ı veya hedef dosyayı değiştirmez. Başarılı sonuçtan sonra, aynı doğrudan terminalde:

```bash
bash ~/mualiy-yayin-baslat.sh --apply
```

`--apply` doğrulanmış yayın dosyasını `~/mualiy-yayinla-ccf322cc.py` olarak kaydeder, yalnız yerel `sudo` şifresini ister ve sonra yayın aracını TTY'de başlatır. Bu başlatıcı **Access uygulaması, yeni Tunnel route'u veya DNS kaydını oluşturmaz**; Bölüm 1'deki yapılmamış Cloudflare ön koşulları önce tamamlanmalıdır. Başlatıcının kendisini VDS'ye aktaracak kopyala-yapıştır bloğu, paketle birlikte verilmelidir; token/parola/link o bloğa eklenmez.

## 3. Tek dosya, tek çalıştırma — manuel alternatif

Başlatıcı kullanılamıyorsa, `mualiy-yayinla.py` dosyasını VDS'de **`/home/neo/mualiy-yayinla.py`** konumuna aktar. Eski bootstrap/kurulum dosyasını tekrar çalıştırma.

VDS terminalinde:

```bash
printf '%s\n' 'ccf322cc91ea882fee62eed1e4d77a1f9b4d23690bde5a045c6bb0fb1ebdcf68  /home/neo/mualiy-yayinla.py' | sha256sum -c - &&
sudo python3 /home/neo/mualiy-yayinla.py --apply
```

Betik sırasıyla yerelde şunları sorar:

1. Mevcut panel kullanıcı adı ve **değiştirdiğin yeni şifre** — şifre kaydedilmez.
2. DNS API token — gizli giriş.
3. **Yeni** `mualiy-panel` tunnel token'ı — gizli giriş; komutun tamamını değil token'ı yapıştır.
4. Sertifika e-postası ve Let's Encrypt koşullarına `EVET` onayı.

Şifre/token girişlerinde yıldız veya karakter görünmemesi normaldir. Bunları buraya yazma. İndirme/DNS doğrulama beklemesi olabilir; betik bütünlüğü kontrol edildikten sonra doğrudan terminalde çalıştırılır, pipe üzerinden gizli giriş kullanılmaz.

### Betik ne yapar?

- Mevcut `mualiy-sui/panel` health ve DB/cert mount bilgilerini, sabit image/UID'yi ve loopback yönetim portlarını kontrol eder.
- İnternetten Access giriş yönlendirmesini görmeden yeni connector'ı başlatmaz. E-posta izin politikasını dashboardda yine sen doğru sınırlandırmalısın.
- Panel API'sinden tutarlı DB yedeği ve Compose yedeği alır; root'a özel tutar.
- DNS-01 ile `vpn.mualiy.net` için gerçek CA sertifikası alır; anahtar ve sertifikayı doğru UID/GID erişimiyle bağlar.
- Panelin kendi API'sinden `mualiy-vpn-tls`, `mualiy-trojan` inbound'u ve güçlü rastgele parolalı özel client oluşturur. Var olan yöneticinin parolasına dokunmaz. Abonelik temel adresini `https://sub.mualiy.net/sub/` yapar.
- **Yalnız yeni panel container'ını** TCP 8443 yayını için yeniden oluşturur. 2095/2096 yalnız 127.0.0.1'de kalır. Yeni panel ve yeni connector için `restart: unless-stopped` açılır.
- Eğer 8443 hâlâ kaldırılmasını istediğin eski native `ozgur-trojan` tarafından kullanılıyorsa, canlı PID/ExecStart/unit içeriği eşleşmesini kontrol ederek yalnız o eski birimi durdurup disable eder. Bilinmeyen süreç/Minecraft/Docker port sahibi varsa durur. Eski dizinleri burada silmez; önceki temizlik ayrı kapsamdır.
- Ayrı `mualiy-sui-tunnel` projesini başlatır; mevcut ThinLinc/cloudflared container/service/config'ine dokunmaz.
- CA + hostname doğrulamalı yerel Trojan TLS kontrolü yapar ve özel bağlantı dosyası üretir.
- Sertifika kontrolü için `mualiy-sui-cert.timer` oluşturur. Sertifika gerçekten değişirse yalnız bu yeni S-UI container'ı yeniden başlatılır; VPN'de kısa kesinti olabilir. Resmî zapret2 timer'ı değişmez.

Host 80/443, Docker Engine, Minecraft/Crafty/Jitsi, ThinLinc, resmî zapret2, SSH ve genel firewall/DNS kurallarında kurulum/değişiklik/flush yapılmaz. Docker'ın **8443 için yeni yayını** doğal olarak kendi yönlendirme kurallarını ekler. VDS sağlayıcı firewall'ında kapalıysa yalnız **TCP 8443** izni gerekecektir. DNS-01 sertifika doğrulaması yalnız geçici `_acme-challenge.vpn.mualiy.net` TXT kayıtları ekleyip kaldırır; diğer A/CNAME kayıtları betik tarafından değiştirilmez.

## 4. Kullan

- Panel: **`https://panel.mualiy.net/app/`** — önce Access, ardından mevcut S-UI girişi.
- Trojan: **`vpn.mualiy.net:8443`, TCP + TLS, SNI `vpn.mualiy.net`**. Sertifika doğrulaması açık.
- Betik `/home/neo/mualiy-baglanti-.../baglanti.txt` yolunu yazar. Bu özel dosyayı VDS dosya yöneticisinden aç; `trojan://...` satırını Android **MikuBox → panodan içe aktar** ile ekle. Root yedeği `/opt/mualiy-sui-live/baglanti.txt` içindedir.
- Android VPN izniyle, cihaz geneli **VPN/TUN / tüm trafik** modunda başlat; yalnız HTTP/SOCKS sistem proxy'si yeterli değil.
- **Telefonun tarayıcısından** VPN açıkken `https://api.ipify.org` adresini aç: beklenen VDS çıkışı **`38.210.77.17`**. ThinLinc/VDS tarayıcısında görmek cihaz VPN'ini kanıtlamaz.
- Sonra Discord/Roblox/Wattpad'in gerçek giriş/kullanımını ve DNS/IPv6/UDP davranışını test ederiz. Windows 10/11 TUN kabulü ayrıca yapılacak. Bu adımlar kendiliğinden tamamlanmış sayılmaz.

## Hata olursa

`DUR:` mesajını ve hangi aşamada olduğunu gönder; **token, parola, client linki, state.json, DB, cloudflare.ini veya özel log dosyasını yükleme**. İlk uygulama kısmen ilerlese de DB/parola sıfırlanmaz; aynı betik yeniden çalıştırıldığında kendi TLS/inbound/client kayıtlarını çoğaltmaz. Yedekler `/opt/mualiy-sui-live/` altındadır; bu klasörü silme. Yeni özel client'ın panelden elle değiştirilmesi/silinmesi veya yönetim yollarının değiştirilmesi durumunda körlemesine tekrar uygulama yapma.

**Doğrulama sınırı:** 16 çevrimdışı güvenlik testi ve gerçek yerel S-UI 1.6.7 ile API → TLS/inbound/client → kimlik doğrulamalı Trojan TCP echo testi geçti. Abonelik ve mevcut fixture yönetici şifresinin korunması da denetlendi. Sandbox'ta Docker/gerçek ACME/Cloudflare hesabı/VDS çalıştırması yapılmadı. S-UI upstream'in üretim uyarısı geçerlidir; ilk yayın yalnız kişisel denemedir, topluluk VPN'i olarak kabul edilmemiştir.


### Access kontrolünde yanlış uyarı düzeltmesi

Önceki `f6f65f…` sürümü varsayılan Python User-Agent ile bu hostname üzerinde 403 alıyordu; aynı herkese açık adres tarayıcı/curl veya `MualiySetup/1.1` kimliğiyle 302 Access giriş yönlendirmesi döndürüyor. Güncel sürüm kontrol isteğinde açık `MualiySetup/1.1` başlığı kullanır. Access doğrulaması kaldırılmadı: korumasız 200, 403 ve başka alana yönlendirmeler hâlâ reddedilir. Access uygulamasını tekrar oluşturma veya korumayı kapatma. Güncel dosyayı kullanabilir ya da sohbetteki tek satırlık kod düzeltmesini uygulayıp aynı `--apply` komutunu tekrar çalıştırabilirsin. Bu doğrulama yalnız Access giriş katmanını kanıtlar; Tunnel bağlantısını veya Trojan servisinin yayına alındığını kanıtlamaz.
