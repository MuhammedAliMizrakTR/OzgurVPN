> **DEVİR NOTU — TARİHSEL ÖN KONTROL.** “Kurulmadı / sürüm bilinmiyor / 443 bilinmiyor” ifadeleri ilk görüşmenin durumudur; güncel durumu anlatmaz. Kullanıcı sonradan Docker S-UI panelini açtığını, şifresini değiştirdiğini ve Ubuntu 26.04.1'e yükseltip başarıyla reboot ettiğini bildirdi. Yeni kurulum yerine [kök README](../README.md) ve `trojan-panel-plan/HIZLI_YAYIN.md` esas alınır. Betik hâlâ salt-okunur inceleme için kullanılabilir; raporun sonundaki “bu raporda KURULMADI” ifadesi betiğin kurulum yapmadığını söyler, kurulu hizmetleri yok saymaz.

# Türkiye VDS → sing-box Trojan + zapret2: ilk adım

**Durum: yalnız ön kontrol hazır. VDS'ye erişilmedi, Trojan/zapret2 kurulmadı.**

Kullanıcı seçimleri: **Ubuntu sunucu**, **Android TUN istemcisi**, **cloudflared ile kullanılan alan adı**, **443 durumu bilinmiyor**. Ubuntu sürümü, root/sudo yetkisi, gerçek DNS/Tunnel yapısı ve dış port erişimi henüz bilinmiyor.

## 1. Bu dosyayı VDS üzerinde çalıştır

`vds-on-kontrol.sh` dosyasını indirdikten sonra SSH/SFTP ile kendi VDS'ne aktar. Kendi bilgisayarında veya Arena çalışma alanında çalıştırman VDS'ni ölçmez.

```bash
bash vds-on-kontrol.sh
```

Alan adının DNS kayıtlarının varlığını da rapora eklemek istersen, örnek adı kendi alan adınla değiştir:

```bash
bash vds-on-kontrol.sh --hostname vpn.example.com
```

- Başlangıç için root zorunlu değildir. Betik sudo istemez veya kendiliğinden kullanmaz.
- Hiçbir paket/binary indirmez; kurulum, modprobe, servis başlatma/durdurma, firewall, DNS veya rota değişikliği yapmaz.
- Sistem bilgilerini okur; Discord, Roblox, Wattpad ve Cloudflare DNS-over-HTTPS hizmetine sınırlı DNS/HTTPS istekleri gönderir. Web hesabına giriş yapmaz.
- Yalnız mevcut dizinde sahibi tarafından okunabilir/yazılabilir (`0600`) rastgele adlı bir rapor oluşturur. Aynı raporun üzerine yazmaz.
- Parola, SSH anahtarı, `.env`, cloudflared token'ı, tünel kimlik dosyası, servis `ExecStart` veya süreç komut satırı okunmaz.
- Her HTTPS isteğinde süre ve gövde boyutu sınırı vardır. TLS sertifika doğrulaması kapatılmaz. curl ayar dosyası ve proxy ortam değişkenleri kullanılmaz.
- Sonuçlarda hedef IP'leri ve isteğe bağlı alan adı bulunabilir. Raporu paylaşmadan önce yine de gözden geçir.
- curl yoksa bunu raporlar; otomatik kurmaz. Gerekirse onu ayrı ve açık bir adımda kurarız.

Sadece yerel bilgi ve yalnız terminal çıktısı:

```bash
bash vds-on-kontrol.sh --no-network --stdout-only
```

Ağ testleri, yavaş/engelli bir bağlantıda birkaç dakika sürebilir. Oluşan `vds-on-kontrol.XXXXXX.txt` raporunu paylaş; **sunucu parolası, SSH özel anahtarı veya Cloudflare/Telegram token'ı paylaşma.**

## 2. cloudflared ve port 443

Gerçekten Cloudflare Tunnel kullanılıyorsa, cloudflared dışarı bağlantı kurduğundan VDS'nin 443 portunu dinlemiyor olabilir. Tersine, 443'te dinleyici görülmemesi o portun sağlayıcı firewall'unda açık olduğunu kanıtlamaz.

Ham Trojan/TLS, Cloudflare'ın HTTP hostname rotasına doğrudan yerleştirilemez. TCP yayınlama, istemcide `cloudflared access tcp` gibi farklı bir istemci akışı gerektirir; sıradan Android Trojan profiliyle aynı değildir. WebSocket taşıması ayrı bir mimaridir; teknik uyumluluk, uzun bağlantılar, UDP-over-stream ve sağlayıcı koşulları ayrıca değerlendirilir.

İlk tercih, mevcut siteleri/tünelleri bozmayan ayrı bir alt alan adıyla doğrudan Trojan/TLS bağlantısını değerlendirmektir. Mevcut DNS veya Tunnel ayarı bu pakette değiştirilmez. Cloudflare Origin Certificate doğrudan bağlantıda otomatik olarak genel güvenilir sertifika sayılmaz; `insecure: true` ile doğrulamayı kapatmayacağız.

Kaynak: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/protocols/

## 3. Sonraki aşamalar — henüz uygulanmadı

1. Ön kontrol sonucuna göre uygun port, sertifika ve taşıma seçilir. Sunucudaki mevcut hizmetler korunur.
2. Resmî sing-box sürümü ve doğrulama bilgileri sabitlenir. Ayrı kullanıcılı, kimlik doğrulamalı Trojan servisi hazırlanır; açık proxy kurulmaz.
3. Android'de VPN izni kullanan TUN profili hazırlanır. Önceki Render prototipi yalnız HTTP/SOCKS uygulama proxy'siydi; bu projede aynı şeyin tamamlandığı varsayılmaz.
4. **zapret2 kapalıyken** aynı hedefler ve uygulamalar test edilir.
5. Gerekliyse resmî zapret2 sürümü/commit'i incelenip sabitlenir. KVM/NFQUEUE ve yetkiler doğrulanır. `blockcheck2` gibi firewall değiştirebilen araçlar tanılama betiğinin parçası DEĞİLDİR; ayrı, geri dönüş planı olan adımda kullanılır.
6. Strateji VDS'nin hedeflere çıkan trafiğinde denenir. Rastgele bir ülke/ISS için yayımlanmış genel ayar körlemesine uygulanmaz; SSH ve cloudflared trafiği korunur.
7. Aynı ölçüm zapret2 açıkken tekrarlanır. Yanlış etki veya erişim kaybında yalnız bizim eklediğimiz kurallar geri alınır; mevcut firewall asla topluca temizlenmez.

## Kabul testi

| Deneme | Kabul için bakılacak şey |
|---|---|
| Trojan | TLS doğrulaması açık; yanlış parola reddediliyor; dış IP VDS çıkışıyla uyuşuyor |
| Android TUN | Tarayıcıya özel proxy değil; cihaz VPN bağlantısı aktif |
| Discord | Giriş, Gateway/WebSocket bağlantısı ve gerçek sesli görüşme ayrı ayrı |
| Roblox | Giriş, bir oyuna katılma ve oturum sürdürme; yalnız ana sayfa değil |
| Wattpad | İçerik açma/okuma ve gerekiyorsa giriş; yalnız ilk HTTP yanıtı değil |
| DNS / IPv6 | DNS yolu, IPv4/IPv6 ve uygulamaların tünel dışına çıkışı kontrol edilmeli |
| Kesinti | Sunucu/tünel kapanınca Android'in tünel dışına düşüp düşmediği ayrıca ölçülmeli |
| UDP | DNS, ses ve oyun akışları test edilmeli; ICMP/ping desteği varsayılmaz |

**Bu üç hizmetin çalışması bütün sansürün kalktığını kanıtlamaz.** IP/rota engeli, hedefin ülke politikası veya yeni DPI kuralları farklı sonuç verebilir. Ülke kısıtı için gerçekten başka ülkedeki bir çıkış gerekir; zapret2 bunu tek başına sağlayamaz.

## Yedek sunucu

Hax için doğru araştırılan alan adı **hax.co.id**'dir; `hax.id` aynı hizmet diye varsayılmaz. Hax tahsisi, stok, IPv6/IPv4 erişimi, mevcut yenileme şartları ve gerçek çalışırlık henüz doğrulanmadı. Başka sağlayıcıda bir sunucu bulunmadan ikinci bağımsız trafik hakkı veya otomatik yedekleme kurulmuş sayılmaz.

Hax/Woiden resmî kanalı geçmişte otomatik yenileme scriptlerinin etkisinden şikâyet etmiş. Resmî, izin verilen yenileme yöntemi doğrulanmadan üçüncü taraf otomasyona güvenmeyeceğiz. Telegram üzerinden hatırlatma mümkündür; CAPTCHA/insan kontrolünü aşan yenileme otomasyonu bu pakette yoktur.

Araştırma ayrıntıları ve kaynaklar: `ARASTIRMA.md`.

## Yerel testler

```bash
python3 test_preflight.py
```

8 çevrimdışı test geçmiştir. Gerçek VDS, Android TUN, Trojan, zapret2 ve uygulama testleri henüz yapılmamıştır. Ayrıntılar: `TEST_SONUCLARI.md`.
