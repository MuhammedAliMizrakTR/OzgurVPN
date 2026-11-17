# Eski native servisleri kaldırma — yeni Docker S-UI korunur

Panelin açıldığını ve şifresini değiştirdiğini bildirdin. Kurulumu veya parola sıfırlamayı yeniden çalıştırma. Araç teslim edildi; **kullanıcının VDS'de uygulama sonucu bilinmiyor**, asistanın SSH erişimi/uygulaması olmadı. Bu belge yalnız yetki verilmiş **ESKİ native** kapsam içindir; yeni panelin yayınını gereksiz bir geniş temizlik turuna bağlamaz. Güncel öncelik [kök README](../README.md) ve `HIZLI_YAYIN.md` içindedir. Reboot sonrası yeni panel durmuşsa önce yalnız mevcut panel/DB bağını doğrula; kurucuyu yeniden çalıştırma.

## Kapsam

Hedefler tam adlarıyla `ozgur-trojan.service`, `s-ui.service`, olası yazım varyantı `s.ui.service` ve `sing-box.service`.

- Mevcut Docker `mualiy-sui` paneli önce çalışır/healthy olmalı; DB bağlaması `/opt/mualiy-sui/db` olmalı.
- Eski birimlerin gerçek fragment/ExecStart bilgileri ve drop-in içerikleri incelenir. Container/tünel komutu, yeni panele referans, beklenmeyen native binary veya paket/vendor birimi varsa otomatik temizlik durur.
- Bulunmayan eski birim hata değildir. Bulunan hedefler durdurulur ve etkin otomatik başlangıçları kapatılır.
- Bilinen eski dizinler `/opt/ozgur-vds`, `/etc/ozgur-vds`, `/root/ozgur-vds-clients`, `/usr/local/s-ui` ve eski S-UI komut dosyaları; hedeflere ait yerel systemd birimleri/drop-in'ler kontrol edilerek canlı konumlardan taşınır.
- Taşınacak bir yol, çalışan **veya durmuş** bir Docker container'ının mount kaynağıyla çakışıyorsa işlem durur. Eski yolları hâlâ kullanan başka süreç varsa dosyalar taşınmaz; süreç adına göre öldürme yapılmaz.
- `ozgur-zapret.service` bulunursa `/opt/ozgur-vds` ortak bağımlılığı nedeniyle hiçbir eski servis durdurulmadan işlem durur. Resmî `/opt/zapret2` bundan farklıdır ve temizliğin hedefi değildir.

Yeni `/opt/mualiy-sui` dizini, değiştirdiğin parolanın bulunduğu DB, Docker container/image/volume'ları, Minecraft/Crafty, Jitsi, ThinLinc/cloudflared ve resmî zapret2 temizliğin dışındadır. Firewall/DNS düzenleme, paket kaldırma ve Docker yeniden başlatma yapılmaz.

**Eski Trojan durdurulunca eski VPN profili çalışmaz. Yeni panelde Trojan inbound henüz hazırlanmadığı için VPN'de geçici kesinti beklenir.**

## VDS'de çalıştırma

`mualiy-eski-servis-temizle.py` dosyasını indirip SFTP/ThinLinc ile `/home/neo/mualiy-eski-servis-temizle.py` yoluna koy.

Önce dosya bütünlüğünü ve temizlik planını kontrol et:

```bash
printf '%s\n' 'cc6e788ab286ecd83997872eccbd5837eccf5428274a6e5326162efab99d6bb8  /home/neo/mualiy-eski-servis-temizle.py' | sha256sum -c - &&
sudo python3 /home/neo/mualiy-eski-servis-temizle.py --check
```

Kontrol başarılıysa uygula; `DUR:` mesajı varsa zorlamadan çıktıyı paylaş:

```bash
sudo python3 /home/neo/mualiy-eski-servis-temizle.py --apply
```

Betiğin normal terminal çıktısı parola veya unit/config içeriği basmaz. **Arşivi, DB'yi, özel anahtarları veya client JSON'larını sohbete yükleme.**

## Son kontrol ve arşiv

- Betik yeni Docker panelinin health durumunu tekrar kontrol eder, eski birim durumlarını ve 8443 TCP socket bilgisini raporlar. Socket görünmemesi tek başına Docker NAT yayını/firewall/dış erişim kanıtı değildir; yeni inbound yayını öncesi port tekrar kontrol edilir.
- ThinLinc Firefox'ta `http://127.0.0.1:2095/app/` adresini **yeni şifrenle** açıp doğrula.
- Eski dosyalar kalıcı silinmez; root'un özel `/root/mualiy-eski-servisler-.../` dizininde tutulur (0700). `manifest.json` önceki birim durumlarını ve taşınan yolları, `files/` eski dosyaları içerir. Birim/drop-in metinleri de özel snapshot dosyalarında saklanır. Arşiv eski parolalar/anahtarlar içerebilir.
- Hata bir servis durdurulduktan sonra oluşursa eski VPN kapalı kalabilir. Betik hiçbir şeyi otomatik geri başlatmaz; yeni panel verisini silmez. Çıktıyı paylaş, arşivi sakla. Geri dönüş gerekirse yalnız manifestteki eski yollar incelenerek geri konur; toplu olarak `/opt` üzerine kopyalama yapılmaz.
- Login yapamayan sistem hesapları ve ortak paketler güvenlik için bilerek bırakılır; başka bileşenlerin kullanabileceği genel `sing-box` paket/binary/config dosyaları körlemesine silinmez. Kullanıcı ev dizinlerindeki export/ZIP dosyaları taranıp silinmez. Bu, sistem genelindeki her dosyayı yok eden bir silme aracı değil, bilinen eski native kurulumu devreden çıkaran sınırlı temizliktir.

## Yerel doğrulama

20 çevrimdışı fixture testi geçti; Python derleme ve root olmadan çalıştırmayı reddetme kontrolü geçti. Docker/systemctl testlerde taklittir; VDS'nin gerçek temizliği ve son sağlık sonucu kullanıcı çıktısı gelene kadar doğrulanmış sayılmaz.
