> **DEVİR NOTU — ESKİ NATIVE KURULUM / YENİDEN ÇALIŞTIRMA.** Bu klasör eski `ozgur-trojan.service` / isteğe bağlı `ozgur-zapret.service` tasarımının kaynak ve test arşividir. Mevcut hedef **var olan Docker S-UI paneli ve değiştirilmiş yönetici şifresini korumaktır**. Aşağıdaki “henüz kurulmadı”, Ubuntu 24.04 ve SFA adımları tarihsel olup güncel talimat değildir. Kullanıcının güncel bildirimi Ubuntu 26.04.1 + başarılı reboot, Android istemcisi **MikuBox 1.4.3-UwU-2**. Bu paketi VDS'ye yeniden kurma; [kök README](../README.md) ve güncel yayın rehberini kullan. Test kaynakları ve eski yolları tanımak için tutuldu.

# Türkiye VDS → Trojan/TLS → Android TUN

**Paket 1.0.0 · 14 Kasım 2026 · Ubuntu 24.04 x86_64 için**

Bu paket, paylaştığın gerçek VDS ön-kontrol raporuna göre hazırlanmıştır. **Sunucuna erişilmedi; kurulum henüz yapılmadı.** Sunucu adresi/parola/sertifika pakete gömülü değildir. Bunlar VDS'de oluşturulur.

## Raporunun anlamı

- Ubuntu 24.04.4 LTS, x86_64, yaklaşık 16 GiB RAM: bu kurulum için uygun bir başlangıç.
- 80/443 dolu, cloudflared aktif. Portların hangi sürece ait olduğu ve dış erişimi rapordan bilinmiyor. **Hiçbirini değiştirmiyoruz.**
- 8443'te yerel dinleyici görülmedi. Bu, sağlayıcı güvenlik duvarı/NAT üzerinden erişilebildiği anlamına gelmez.
- Discord API ve Roblox HTTP/TLS isteği başarılı. Discord gateway kökünün 404 dönmesi TLS bağlantısının başarısız olduğu anlamına gelmiyor.
- Wattpad hem sistem DNS hem DoH ile TLS sırasında bağlantıyı sıfırladı. **DNS değiştirmek tek başına çözmedi; bu sonuç tek başına kesin DPI teşhisi değil.**
- TUN aygıtı ve NFQUEUE modül bilgisi mevcut; gerçek NFQUEUE kuyruğunun çalışması VDS'de henüz doğrulanmadı.

## Mimari ve sınırlar

```text
Android / SFA, cihaz çapında TUN
  └─ doğrulanmış Trojan/TLS, TCP 8443
       └─ Ubuntu'da ayrı ozgur-trojan kullanıcısı
            ├─ TCP ve UDP uygulama çıkışları → İnternet
            └─ isteğe bağlı zapret2: yalnız bu UID, TCP/443, wattpad.com
```

Bu sürüm **yeni bir Trojan sunucusu** kurar; başka bir Trojan sunucusuna istemci değildir. Ağ kapsamını ayrı UID ile sınırlamak için **yerel systemd kurulumu** kullanır; Docker kurulumu değildir. Eski proxy projesinin dosyaları/arşivi değiştirilmez.

Android profili yalnız HTTP/SOCKS kullanan uygulamalar için değildir: TUN hedefler. Ancak telefonunda henüz çalıştırılmadı. Trojan, TCP/UDP uygulama akışlarını taşır; WireGuard gibi her IP protokolünü taşıyan L3 tünel değildir. ICMP/ping ve hotspot'taki diğer cihazlar için kapsama sözü verilmez. UDP de bu tasarımda **TLS/TCP içinde** taşındığından kayıplı ağda oyun/ses gecikmesi artabilir.

**Türkiye IP'si değişmez bir engel değildir; fakat yabancı ülke çıkışı da sağlamaz.** Zapret2 ülke değiştirmez, hedefin Türkiye/datacenter IP reddini veya gerçek IP/rota engelini çözmez. İstemci→VDS bağlantısı ISP tarafından engelleniyorsa VDS'nin internet çıkışındaki zapret2 bunu düzeltmez.

## 0. Hazırlık ve güvenlik

1. Sağlayıcının VPN/proxy kullanımına izin verdiğini ve trafik kotanı kontrol et. Bu paket yeni/büyük bir kota yaratmaz.
2. Sağlayıcı konsoluna erişimini ve mümkünse snapshot'ını hazır tut. Mevcut SSH oturumunu açık bırak; ikinci oturumdan test et.
3. Paketi VDS'de normal kullanıcının dizinine çıkar. Güvenmediğin kaynaktan gelen root komutunu çalıştırma; kaynaklar bu pakette açık.
4. Python 3, OpenSSL, curl, systemd, useradd ve ss gerekir. Raporundaki kurulumda çoğu mevcut. Kurucu otomatik `apt upgrade`, reboot veya mevcut servis güncellemesi yapmaz.
5. **Parola, SSH anahtarı, cloudflared tokenı ve üretilen Android JSON dosyasını sohbete gönderme.**

Kullanılacaklar: sing-box **1.14.4**, zapret2 **v1.0.7**. Resmi sürümler ve SHA-256 değerleri `versions.json` içinde sabittir. Zapret2 arşivinin yanında nfqws2 binary'si de ayrıca doğrulanır. `master` veya `curl | bash` kullanılmaz.

İstersen port sahiplerini kendin salt okunur incele:

```bash
sudo ss -ltnp '( sport = :80 or sport = :443 or sport = :8443 )'
```

## 1. Önce yalnız Trojan kur

Arşivden çıkan `tr-vds-kurulum` dizininde:

```bash
cd tr-vds-kurulum
sha256sum -c SHA256SUMS
read -rp 'VDS genel IPv4 adresi: ' VDS_IP
sudo python3 vds.py install --endpoint "$VDS_IP" --port 8443 --apply
```

Buraya **sağlayıcı panelindeki genel IPv4 adresini** gir; alan adı, Cloudflare Tunnel adresi, 10.x/192.168.x veya CGNAT adresi değil. IP'yi sohbete göndermen gerekmez. NAT arkasındaysan sağlayıcıda aynı porta yönlendirme de gerekir. 8443 sonradan dolduysa kurucu durur; 80/443'e geçmez.

Kurucu:

- `/opt/ozgur-vds`, `/etc/ozgur-vds`, `/root/ozgur-vds-clients` oluşturur; var olanların üzerine yazmaz.
- Yeni `ozgur-trojan` sistem hesabı ve `ozgur-trojan.service` oluşturur.
- Kriptografik rastgele parola ve **IP SAN içeren 365 günlük özel TLS sertifikası** üretir.
- Sertifika güvenini Android profiline gömer. **`insecure` açılmaz; Android'in sistem sertifika deposuna CA yüklenmez.**
- Sunucu ve Android JSON'larını gerçek sing-box ile kontrol eder; servisi başlatıp yerel TLS kimliğini doğrular.
- SSH, cloudflared, 80/443, sistem DNS'i, varsayılan rotalar ve mevcut firewall kurallarını değiştirmez.

TLS sertifikası özel güvenilir sertifikadır; normal tarayıcı bunu kendiliğinden güvenilir saymaz. Bu beklenir, TLS denetimini kapatma gerekçesi değildir. Sertifika süresi/yenilemesi otomatik değildir; yenilenirse profil de güncellenmelidir.

### Dışarıdan TCP 8443 izni

Kurucunun yerel TLS kontrolü **dış erişim testi değildir**. Sağlayıcının güvenlik grubunda/güvenlik duvarında **gelen TCP 8443** izni gerekebilir.

UFW zaten **aktifse** ve bu izni vermek istiyorsan:

```bash
sudo ufw allow 8443/tcp comment ozgur-vds
```

UFW pasifse sırf bunun için `ufw enable` çalıştırma. Özel nftables/iptables yapın varsa kurallarını görmeden genel ACCEPT/flush ekleme. **UDP 8443 açılması gerekmez:** uygulama UDP'si Trojan/TLS'nin TCP bağlantısında taşınır.

Cloudflared üzerinden yayınlanan alan adının bulunması normal Android Trojan istemcisinin doğrudan çalışacağı anlamına gelmez. Bu ilk aşama, Cloudflare proxy/tunnel üzerinden değil **doğrudan genel IPv4:8443** üzerinden gider. Mevcut domain/tunnel ayarlarını değiştirmiyoruz.

## 2. Zapret2 olmadan ilk ölçüm

```bash
sudo python3 /opt/ozgur-vds/vds.py test
```

Bu komut geçici, **loopback-only** test istemcisiyle gerçek Trojan bağlantısından Discord/Roblox/Wattpad'e HTTPS GET gönderir; raporu `/root/ozgur-vds-test-*.json` dosyasına kaydeder. Geçici istemci ve özel test dosyaları kapanışta temizlenir.

- Sunucu tarafı çözümleme Cloudflare DoH üzerinden yapılır; `socks5h` sayesinde curl hedefi yerel DNS ile çözmez.
- Bu ölçüm VDS'nin kendi içinden yapılır: telefon→VDS dış erişimini veya cihaz TUN'unu kanıtlamaz.
- `TLS=0`, tek başına HTTP başarısı anlamına gelmez; HTTP kodu ve `curl_exit` birlikte okunur.
- HTTP 403/429 uygulama/CDN politikası veya rate limit olabilir. HTTP 200 de giriş yapma, oyun oturumu, ses veya okuma testi değildir.
- Üçü de curl 0 + HTTP 200 + TLS 0 verirse komut 0, aksi halde 1 çıkış kodu verir; rapor yine kaydedilir. Bu bir sansür teşhis kodu değildir.
- Sayfa 512 KiB sınırını aşarsa curl 63 verebilir; görünen HTTP/TLS kodunu ayrıca değerlendir.

## 3. Android'e cihaz çapında TUN profili aktar

VDS raporundaki normal kullanıcı `neo` idi. Hesabın farklıysa komutta değiştir:

```bash
sudo python3 /opt/ozgur-vds/vds.py export-client --user neo
```

Komut, kullanıcının ev dizininde rastgele adlandırılmış, yalnız o hesaba açık bir klasör oluşturur ve içine `android-tun.json` kopyalar. Kaynak `/root/ozgur-vds-clients/android-tun.json` root'a özel kalır.

1. Üretilen dosyayı **SFTP gibi güvenilir bir kanalla yalnız kendi telefonuna** aktar. Web sunucusuna, herkese açık Git deposuna veya sohbete yükleme. Dosya parola içerir.
2. Resmi **sing-box for Android (SFA)** kur. Bu profil **1.14.4** çekirdeğiyle doğrulandı; en az 1.14 alanlarını destekleyen istemci gerekir. İndirme: <https://sing-box.sagernet.org/clients/android/>. Sabit sürüm: <https://github.com/SagerNet/sing-box/releases/tag/v1.14.4>. Android uygulama dosyaları `SFA-...apk` ile başlar; `linux_...apk` dosyaları Android uygulaması değildir.
3. Yerel yapılandırma/dosyadan içe aktarma seçeneğiyle JSON'u aç, profili seç ve VPN iznini ver. Uygulama isimleri sürüme/dile göre değişebilir. Uygulama-bazlı dahil/haric listesi ekleme.
4. Android Ayarlar → VPN → SFA bölümünde cihazın sunuyorsa **Her zaman açık VPN** ve **VPN olmadan bağlantıları engelle** seçeneklerini aç. Yalnız JSON'daki `strict_route` Android kill switch garantisi değildir.
5. Pil optimizasyonundan çıkar. Aktarım için açılan normal kullanıcı kopyasını ve telefondaki geçici indirilen kopyayı, profilin içe aktarıldığını doğruladıktan sonra sil. Kök kullanıcıdaki asıl profili güvenle yedekle.

### DNS / IPv6 / UDP politikası

| Konu | Bu profil |
|---|---|
| IPv4 TCP | TUN → Trojan → VDS çıkışı; doğrudan fallback yok |
| IPv4 UDP | TUN → Trojan/TLS/TCP → VDS UDP çıkışı; yerel sentetik echo testi geçti |
| DNS | TUN'daki DNS hijack → Trojan içinden Cloudflare DoH; sunucunun isim çözümlemesi de DoH |
| IPv6 | TUN'a IPv6 adresi de verilir, IPv6 akışları reddedilir, AAAA sorguları boş cevaplanır; yerel IPv6'ya direct fallback tanımlanmaz |
| ICMP / diğer ham IP | Desteklenme sözü yok; ping'i tek başarı ölçütü yapma |
| LAN / metadata / SMTP | VDS'nin yerel/özel/metadata IP'lerine ve 25/465/587 portlarına çıkış reddedilir; LAN erişimi hedeflenmez |

VDS'nin IPv6 varsayılan rotası raporda yoktu; bu nedenle IPv6'yı tünel dışına bırakmak yerine **bilinçli olarak kapatan** ilk profil üretildi. Bu politika yapılandırmada tanımlıdır; **Android'de gerçek sızıntı/lockdown testi henüz yapılmadı.** Android'in ayrıcalıklı sistem trafiği, iş profili, tethering ve uygulama istisnaları ayrıca değerlendirilir.

### Telefonda kabul testi

- VPN kapalı/açık aynı IP gösterme hizmetini aç. Açıkken internet çıkışı, VDS'nin dışarı görünen IPv4'ü olmalı; ülke Türkiye kalabilir.
- DNS ve IPv6 sızıntısını Wi-Fi ve mobil veride ayrı ayrı dene. IPv6'nın burada çalışmaması beklenir; telefonun yerel IPv6'sı görünmemeli.
- Discord: oturum + mesaj + sesli kanal. Roblox: gerçek bir oyun oturumu. Wattpad: sayfa + okuma + gerekiyorsa giriş. Yalnız ana sayfanın 200 dönmesi yeterli değildir.
- Lockdown açıkken yalnız kendi yeni servisini durdur: `sudo systemctl stop ozgur-trojan.service`. Telefonda yeni internet bağlantısı kurulamamalı. Ardından `sudo systemctl start ozgur-trojan.service`. Bu test başarıyla yapılmadan kill switch var deme.
- Telefonun Wi-Fi↔mobil veri geçişini ve ekran kapalı davranışını dene. Hata mesajlarını paylaşabilirsin; profilin tamamını paylaşma.

## 4. Sonra isteğe bağlı, kapsamı dar zapret2

Önce yukarıdaki ilk ölçümü kaydet. NFQUEUE işlemi ağ katmanını değiştirir; bu adım bilinçli olarak ayrıdır:

```bash
sudo python3 /opt/ozgur-vds/vds.py zapret-install --profile split --apply
sudo python3 /opt/ozgur-vds/vds.py test
```

`nft` veya `modprobe` yoksa kurucu durur. Gerekiyorsa dağıtım paketlerini ayrı adımda kur: `sudo apt-get install nftables kmod`. Kurulum çıktısını incele; bu paket mevcut sistem firewall politikasını senin yerine seçmez.

Zapret2'nin kapsamı:

- Yeni `ozgur-zapret` hesabı, ayrı `ozgur-zapret.service`, `/etc/ozgur-zapret` dizini.
- Önce mevcut nft ruleset'in yalnız root'a açık kopyası alınır; **mevcut kurallar flush edilmez** ve yedeği bütün sisteme otomatik geri yüklenmez.
- Yalnız `ozgur-trojan` UID'sinin **dışarı TCP/443** akışları kuyruklanır. nft tablosu yalnız `inet ozgur_vpn_zapret`, kuyruk 61234'tür; çakışmada durur.
- Lua işleme hostlist'i varsayılan olarak yalnız `wattpad.com` ve alt alanlarıdır. Diğer HTTPS akışları kuyruktan geçse de bu profil tarafından değiştirilmez. **SSH, cloudflared ve diğer kullanıcıların trafiği bu UID kuralına girmez.**
- Tüm hosta, FORWARD'a, varsayılan rotalara, genel UDP/QUIC trafiğine veya 80/443 dinleyicilerine kural eklenmez.
- `split` ilk denemedir, garantili Türkiye stratejisi değildir. Aynı istemci/URL ile önce-sonra karşılaştır.
- NFQUEUE dinleyicisi yoksa `bypass` trafiğin devamını sağlar. Bu zapret2 için **fail-open** tercihtir, Android VPN kill switch'i değildir.
- nfqws2 için NET_ADMIN/NET_RAW kernel yetkileri gerekir. UID kuralı işlenen trafiği sınırlar; bu yetkileri yalnız bir UID'nin paketlerine hapseden ayrı bir güvenlik sınırı değildir.

İlk strateji Wattpad'i açmazsa, tek bir ikinci profili kontrollü karşılaştır:

```bash
sudo python3 /opt/ozgur-vds/vds.py zapret-profile --profile disorder --apply
sudo python3 /opt/ozgur-vds/vds.py test
```

Elle değiştirilmiş service dosyasının üzerine yazılmaz. Bu iki profil de başarısızsa otomatik olarak tüm hosta agresif strateji uygulanmaz: sonuçları değerlendirip hedefe/ISS'ye özgü teşhis gerekir. ECH/SNI görünürlüğü, CDN davranışı, yol MTU'su, TLS uygulaması veya gerçek IP engeli stratejinin sonucunu değiştirebilir.

Yalnız Wattpad düzeldi diye “bütün internet sansürsüz” sonucu çıkarma. Ayrıca datacenter çıkışı ile telefonunun ISS yolu farklıdır.

## 5. Durum, geri alma, kısmi hata

```bash
sudo systemctl status ozgur-trojan.service ozgur-zapret.service --no-pager
sudo nft list table inet ozgur_vpn_zapret
```

İkinci komut zapret kurulmadıysa/devre dışıysa tablo bulunamadı diyebilir; bu normaldir.

**Yalnız zapret2'yi geri al:**

```bash
sudo systemctl disable --now ozgur-zapret.service
```

`ExecStopPost` yalnız paketin kendi nft tablosunu kaldırır; aynı adlı ama paket sahiplik etiketi olmayan tabloyu silmeyi reddeder. Gerekirse, yalnız paketin oluşturduğunu doğruladığın bu sabit tabloyu temizle:

```bash
sudo python3 /opt/ozgur-vds/vds.py firewall-off
```

**Yeni Trojan servisini de durdur:**

```bash
sudo systemctl disable --now ozgur-trojan.service
```

Bu işlemler cloudflared/SSH'ı durdurmaz. Dosyalar, TLS anahtarı ve kullanıcılar bilinçli olarak korunur; yeniden açmak istersen `enable --now` kullanabilirsin. UFW'de kendin eklediğin 8443 iznini kaldırmak istersen `sudo ufw delete allow 8443/tcp` komutunu yalnız bunun sana ait izin olduğunu doğrulayarak kullan. Sağlayıcı güvenlik grubu değişikliğini de panelden geri al.

Kurulum yarıda kalırsa **aynı dosyaların üzerine yazıp sürdürmez**. Ağ indirmesi/servis izni/modül hatasını incele. Kısmi dizinleri veya servis hesaplarını körlemesine silip yeniden deneme; dosya listesini ve durum çıktısını incelemek daha güvenlidir. Gizli JSON/key dosyalarını paylaşma. Paket otomatik silme, genel firewall restore/flush veya reboot yapmaz.

## 6. Sürüm, kişisel kullanım ve kalan işler

- Parola sertifika profili **tek sahip için** üretilir. Topluluk hizmeti için kullanıcı başına kimlik, iptal/rotasyon, kota, abuse politikası ve sağlayıcı izni ayrıca gerekir.
- Uyarı logları journald'a gidebilir; “hiç log yok” garantisi verilmez.
- Sabit sürümler tekrarlanabilirlik sağlar, sonsuza dek güvenli oldukları anlamına gelmez. Güvenlik güncellemeleri otomatik uygulanmaz; sürüm ve hash birlikte bilinçli güncellenir. Sertifika süresi de izlenmelidir.
- **Hax yabancı yedek, Telegram yenileme, yedek Docker deployment ve bağımsız ≥100 GB hak bu pakette yoktur.** Stok, VPN/Docker izni, kota ve yenileme mekanizması ayrıca doğrulanmalıdır. İki container aynı sağlayıcı kotasını ikiye katlamaz.

## Kaynaklar ve test ayrımı

- sing-box Trojan: <https://sing-box.sagernet.org/configuration/inbound/trojan/>
- TLS özel güven: <https://sing-box.sagernet.org/configuration/shared/tls/>
- TUN ve Android: <https://sing-box.sagernet.org/configuration/inbound/tun/> · <https://sing-box.sagernet.org/clients/android/>
- Sabit sing-box kaynağı/sürümü: <https://github.com/SagerNet/sing-box/tree/v1.14.4>
- Sabit zapret2 sürümü/kaynağı: <https://github.com/bol-van/zapret2/tree/v1.0.7> · <https://github.com/bol-van/zapret2/blob/v1.0.7/docs/manual.en.md>
- Cloudflare yayınlanan uygulama protokolleri: <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/protocols/>

Canlı sing-box belgeleri daha yeni sürümlerin alanlarını da içerir. Bu paket **1.14.4 ile fiilen kontrol edildi**, 1.15 gerektiren `certificate_sha256` alanını kullanmaz. Detaylı gerçek test sonuçları ve yapılmayanlar `TEST_SONUCLARI.md` içindedir.
