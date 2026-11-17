> **TARİHSEL KANIT:** eski native tasarımın izole/yerel testleri; mevcut Docker panelinin veya gerçek Android/Windows TUN'un doğrulanması değildir. Yeni devir kontrol özeti `../DEVIR_TEST_SONUCLARI.json`.

# Gerçek test sonuçları — 14 Kasım 2026

## Kesin ayrım

**Bunlar Arena çalışma ortamında yapılan testlerdir, kullanıcının VDS'sinde veya Android telefonunda yapılan kurulum testi değildir.** Kullanıcının Ubuntu raporu yalnız ön-kontrol aşamasını doğrular. Yeni paket sunucuya kurulmadı; SSH oturumu açılmadı, uzaktan firewall değiştirilmedi.

Yerel ortam: Debian 13/trixie, Linux 6.1.189+, x86_64, Python 3.13.18. Kullanıcının ortamı ise Ubuntu 24.04.4 / Linux 6.8.0-137-generic / VMware'dir. Gerçek VDS kabul testinin yerine konamaz.

## 1. Çevrimdışı güvenlik/yapılandırma testleri — 17/17 geçti

Komut: `python3 -m unittest -v test_offline`

- Yalnız genel IPv4 kabulü; domain/CGNAT/özel IP ve komut enjeksiyonu metni reddi.
- 80/443 ve geçersiz portların kurulum hedefi olmasının engellenmesi.
- `--apply` olmadan kurulum/profil değiştirme yan etkilerinin başlamaması.
- Mevcut dosya/dizin/symlink üzerine yazmama; var olan servis hesabını başka amaç için kullanmama.
- `umask 0077` altında istenen dosya izinlerinin açık biçimde uygulanması.
- Yanlış indirme hash'i ve boyut aşımı reddi.
- TUN, IPv4/IPv6 yakalama adresleri, direct fallback olmaması, uygulama listesiyle sınırlanmama.
- TLS doğrulama açık, IP kimliği ve gömülü özel güvenilir sertifika; 1.15 gerektiren alan yok.
- DNS'nin Trojan üzerinden DoH'ye yönlendirilmesi, AAAA boş cevap ve IPv6 reject politikası.
- LAN/metadata/SMTP ve IPv6 için sunucu reddi.
- nft kurallarının ayrı UID/TCP443/kuyruk kapsamı; global flush/SSH/UDP kuralı olmaması.
- Ayrı servis kimliği, zapret servisinden Trojan anahtar dizininin gizlenmesi.
- İzin verilen iki zapret profilinin komut argümanları ve sabit sürüm kayıtları.

Bu testler politikanın yapılandırmada bulunmasını doğrular; Android işletim sistemi üzerinde gerçekten uygulanmasını kanıtlamaz.

## 2. Sabit resmi indirmeler — geçti

**Paketin gerçek `download.py` fonksiyonları** ile yeniden indirildi, hash doğrulandı, binary'ler çalıştırıldı.

| Bileşen | Doğrulanan sürüm / SHA-256 |
|---|---|
| sing-box arşivi | 1.14.4 · `699a1b510aa4396b2176d32d1181920399ebf1e267835da6f3b598d0f7c24968` |
| zapret2 arşivi | v1.0.7 · `547a5dce3f4820721a425680ea3f7f3971b7e9c772b8c795dd2d623148da0928` |
| nfqws2 binary | `4bb2634f0266bcc3cbe5988f4fc8c5e824649dd11edc418e71a415096c2505b0` |

Zapret2'nin yayınladığı `sha256sum.txt` dosyası arşiv değil **tek tek binary** hash'leri içerir. Arşiv hash'i resmi GitHub sürüm varlığının digest'iyle, binary hash'i de yayınlanan binary listesiyle eşleştirildi. Bu, bağımsız üçüncü taraf imzası doğrulaması değildir; resmi HTTPS kaynağı ve sabit hash'lerle bütünlük/provenans kontrolüdür.

- sing-box: `1.14.4`, revision `c005f35300ce76427dc285481ec5695f5b179cd2`, CGO kapalı.
- nfqws2: `v1.0.7`, revision `038c97e5819df10f8e8c22a2f1fffe57f2f7379b`, Lua compat 6.
- Gerçek indirme sonrası `umask 0077` altında binary/dizinler 0755, Lua/lisans 0644 olarak kontrol edildi. Kurulumdaki özel config/anahtarlar bundan ayrıdır ve 0640/root-grup, istemci profili 0600 olacak şekilde üretilir.

## 3. İzole ağda gerçek protokol + NFQUEUE — 15/15 kontrol geçti

Kaynak: `test_netns.py`. Root yetkisi yalnız geçici **ayrı ağ namespace'i** içinde kullanıldı; ikinci hedef namespace'i/veth çifti ile gerçek egress yolu oluşturuldu. Kalıcı host firewall'ına kural eklenmedi. Hedef, bu kapalı ağdaki **sentetik HTTPS/UDP echo sunucusudur**, gerçek Wattpad sitesi değildir.

1. Sunucu ve Android TUN şemaları sing-box 1.14.4 tarafından kabul edildi.
2. Özel TLS güveni ve doğru IP SAN ile doğrulama geçti.
3. Yanlış TLS kimliği reddedildi.
4. Güvenilmeyen sertifika reddedildi.
5. İç HTTPS/TCP verisi, dış doğrulanmış/authenticated Trojan bağlantısından taşındı.
6. SOCKS UDP → Trojan/TLS → karşı ağ UDP echo: aynı payload geri alındı.
7. Yanlış Trojan parolasıyla hedefe ulaşılamadı.
8. Sunucunun loopback adresine erişim reddedildi.
9. Kapsamı dar nft kuralları gerçek kernel ile `--check` kontrolünü geçti.
10. Gerçek NFQUEUE + `split` Lua profili yüklendi; kuyruk sayaçları arttı, HTTPS aktarımı başarılı oldu.
11. `split` nfqws2 süreci durdurulunca queue `bypass` sayesinde Trojan aktarımı devam etti.
12. Gerçek NFQUEUE + `disorder` Lua profili yüklendi; HTTPS aktarımı başarılı oldu.
13. `disorder` durdurulunca bypass aktarımı devam etti.
14. Paketin gerçek `firewall_off` fonksiyonu, kendi tablosunu kaldırırken başka nft tablosunu korudu.
15. Aynı adlı ama paket sahiplik etiketi olmayan nft tablosunun silinmesi reddedildi.

Ek olarak ayrı UID'nin olmayan HTTPS akışı kuyruk kapsamı açısından kontrol edildi. nfqws2 denemesi `NoNewPrivileges` ve yalnız NET_ADMIN/NET_RAW/SETUID/SETGID/SETPCAP bounding set'iyle çalıştırıldı. Bu, systemd unit'indeki tüm izolasyon seçeneklerinin gerçek Ubuntu'da başlatılmasıyla aynı test değildir.

Testlerin tüm alt süreçleri sonlandırıldı; namespace/veth/nft kaynakları namespace kapanışıyla temizlendi. Yeni test süreci kalmadığı kontrol edildi.

## 4. Canlı internet üzerinden yerel Trojan + DoH — 3/3 geçti

Kaynak: `test_internet.py`. Çalışma ortamında iki geçici, yalnız loopback'e bağlı sing-box süreci; hedef isimleri sunucu tarafında gerçek Cloudflare DoH üzerinden çözüldü. **Zapret2 kapalıydı.**

| Hedef | Sonuç |
|---|---|
| `https://discord.com/api/v10/gateway` | curl 0 · HTTP 200 · TLS 0 |
| `https://games.roblox.com/v1/games?universeIds=1` | curl 0 · HTTP 200 · TLS 0 |
| `https://www.wattpad.com/` | curl 0 · HTTP 200 · TLS 0 |

**Bu son satır kullanıcının Türkiye VDS'sinde Wattpad'in düzeldiği anlamına gelmez.** Çıkış ve ağ yolu farklıdır. Kullanıcının paylaştığı gerçek VDS raporundaki Wattpad TLS reset sonucu henüz yeni kurulumla tekrar ölçülmedi.

## 5. Statik araç kontrolleri — geçti

- Beş Python dosyası `py_compile` ile kontrol edildi.
- `vds.py --help` çalıştı; açık kurulum/profil alt komutları mevcut.
- systemd unit sözdizimi `systemd-analyze verify` ile kontrol edildi. Doğrulama kopyalarında binary yolları bu ortamda bulunan gerçek binary'lere uyarlandı; hedef `/opt/ozgur-vds` kurulumu başlatılmadı.
- ZIP bütünlüğü ve `SHA256SUMS` final paket oluşturulurken ayrıca kontrol edilir.
- Önceki iki arşivin hash'i tekrar kontrol edildi, değiştirilmedi:
  - `ozgur-ag-vpn-engineering.zip`: `bae3097d761d3e90239b43a65403f504fea4d13cd5912bd7e64833733ce35000`
  - `vds-baslangic-paketi.zip`: `8dcf3b1657ce511fdc99f76ee8f7637f44682df7d2eaecf93d0c27dc316b9aad`

## Henüz yapılmayan / kanıtlanmayan

- Ubuntu VDS'de kurucunun/systemd unit'lerinin fiilen çalıştırılması.
- VDS'de yeni servis UID'siyle NFQUEUE ve zapret stratejisinin gerçek sansür yoluna etkisi.
- Telefon/başka ISP'den genel IP:8443 erişimi; sağlayıcı firewall/NAT/çıkış UDP kuralları.
- Android'de TUN başlatma, gerçek çıkış IPv4 değişimi, Wi-Fi/mobil DNS/IPv6 sızıntısı, OS lockdown/kill switch.
- Discord ses, Roblox oyun oturumu, Wattpad okuma/giriş; uygulamaların kullandığı tüm alan adları/CDN/UDP/QUIC yolları.
- ECH, packet loss, MTU/offload, uzun süreli performans, yeniden başlatma ve sertifika yenileme.
- Docker build/deployment, yabancı yedek, bağımsız 100 GB hak, Hax stok/provizyon/izin ve Telegram otomatik yenileme.

Dolayısıyla sonuç **“kurulum adayı yerelde protokol ve güvenlik kontrollerini geçti”** düzeyindedir; **“VDS kuruldu / Android çalışıyor / Wattpad ve bütün internet açıldı” değildir.**
