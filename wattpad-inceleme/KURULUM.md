# Wattpad — kanıt, seçilen zapret2 adayı ve kontrollü devam

> **İlk kurulum rehberi değildir; yeniden install_easy.sh veya tam blockcheck çalıştırma.** Resmî `/opt/zapret2` kurulumu kullanıcı logunda zaten görüldü. Güncel öncelik mevcut Docker S-UI/Trojan yayınıdır; resmî zapret2'yi bu sırada değiştirme. Ana bağlam: [kök README](../README.md).

## Ne biliniyor?

Önceki kullanıcı logu `zapret2-wattpad.log` 11.157 satır ve 2.597 SUMMARY kaydı içeriyordu. Ham log, özel ağ/terminal ayrıntıları barındırabileceği için bu GitHub paketinde yoktur; `analiz.json` yalnız analiz özetidir. Bu paket, ham logdan baştan bağımsız yeniden üretim iddiasında değildir.

| Tarihsel kontrol | Log satırı | Sonuç |
|---|---|---|
| Müdahalesiz TLS 1.2 | 56–59 | curl 35 / connection reset |
| Müdahalesiz TLS 1.3 | 4305–4308 | curl 35 / connection reset |
| multisplit:pos=2 / TLS 1.2 | 95–96; SUMMARY8558 | AVAILABLE |
| multisplit:pos=2 / TLS 1.3 | 4344–4345; SUMMARY9856 | AVAILABLE |

**Seçilen tek aday:**

```text
--payload=tls_client_hello --lua-desync=multisplit:pos=2
```

`AVAILABLE`, HTTP 200 veya gerçek giriş/okuma başarısı demek değildir. 2.597 satır da 2.597 bağımsız, tarayıcıda doğrulanmış çözüm değildir. Kullanıcı logundaki Ubuntu 24.04/kernel6.8/VMware bilgisi tarihsel; son kullanıcı bildirimi Ubuntu 26.04.1 ve başarılı reboot'tur.

## Resmî kurulumdan gelen sonraki bilgi

Pakete alınmayan `output.txt`, **bol-van/zapret2 v1.0.7** kurucusunun `/opt/zapret2` hedefini, nftables/hostlist seçimini, nfqws2'ye Y yanıtını, hardware offload seçimini ve `get_refilter_domains.sh` indirmesini gösterdi. Servis ve liste zamanlayıcısı etkinleştirme adımlarına ulaşıldı. Bu, bugünkü servis durumu veya Docker çıkışının kapsandığı kanıtı değildir.

Daha sonra hedefli ayar düzeltmesi/geri dönüş zamanlayıcısı önerildi; VDS'de uygulanıp uygulanmadığı ve gerçek HTTP/TUN sonucu bilinmiyor. Önceki rehberdeki taze kurulum, `/opt/ozgur-vds/vds.py test`, otomatik `disable --now` ve kaldırıcı adımları bu devir kopyasından çıkarıldı: mevcut Docker mimarisine yanlışlıkla uygulanmamalılar.

Üç farklı yapıyı karıştırma:

1. **Resmî** `/opt/zapret2` → `zapret2.service` ve liste timer'ı: korunacak.
2. Eski özel native paket → `ozgur-zapret.service`, `/opt/ozgur-vds`: farklı kapsam.
3. Kullanıcının daha önce seçtiği Keift → `/opt/zapret` olasılığı: resmî zapret2 ile aynı şey değil; sessizce tekrar kurulmayacak/yan yana eklenmeyecek.

## Saklanan `.conf` neden otomatik uygulanmıyor?

`zapret2-wattpad-v1.0.7.conf`, resmî v1.0.7 `config.default` tabanlı, lisans bildirimi korunmuş **pasif aday örneğidir**; live config veya installer değildir.

- `NFQWS2_ENABLE=0` bilerek pasiftir.
- Yalnız TCP443 seçer; UDP'yi engellemez, işlemez.
- `MODE_FILTER=hostlist` / `<HOSTLIST>`; tek başına bir UID/container sınırlaması **değildir**.
- `GETLIST=` boş olması, önceden indirilmiş global/gzip listeleri kendiliğinden kaldırmaz. Global, user ve exclude listeleri birlikte etkilidir; gzip varsa düz metin dosyanın önüne geçebilir.
- `DISABLE_IPV6=1`, işletim sisteminin IPv6'sını değil zapret2'nin IPv6 işlemesini kapatır.
- Fake/TTL/OOB birleştirmesi yoktur.
- Mevcut `/opt/zapret2/config` üzerine yedeksiz kopyalama yapılmaz. Genel firewall flush, `pkill`, eski kurucuyu tekrar çalıştırma veya başarısızlıkta otomatik yeniden enable yoktur.

Değiştirilmemiş aday dosyanın SHA-256'sı:

```text
73630be4566251163de982b4379efba224d5a567f7a2af83ea3c9a3ccb671b0d  zapret2-wattpad-v1.0.7.conf
```

Önceki yerel `sh -n` ve gerçek nfqws2 `--dry-run` kaydı `analiz.json` içindedir; yeni devir kontrolleri ayrı kök rapordadır.

## Yayın çalıştıktan sonraki küçük görev

1. Yeni Trojan üzerinden cihaz geneli TUN + değişmiş çıkış IP'si kabulünü önce tamamla.
2. Mevcut resmî servis/ayar/liste durumunu **salt-okunur**, sırsız özetle belirle; kurulum ve kapsamı varsayma. Docker bridge/NAT trafiğinin gerçekten hangi hook/arayüzden geçtiğini gözlemeden eski native UID kurallarını taşıma.
3. Gerekiyorsa yalnız hedefli değişiklik için özel yedek, açık yetki ve systemd çalıştığı sürece işe yarayan geri dönüş zamanlayıcısı hazırla. SSH/ThinLinc/Minecraft/Jitsi ve diğer rotalar korunur.
4. Doğrudan VDS çıkışı ile **gerçek yeni Trojan + Android/Windows TUN çıkışında** aynı hedefi karşılaştır. Normal HTTPS GET'i, Wattpad giriş/okumayı ve Discord/Roblox gerçek kullanımını ayrı değerlendir.
5. Test başarısızsa yeni stratejileri rastgele yığma; yalnız kendi değişikliğini geri al. Ülke/datacenter IP reddi varsa zapret çıkış ülkesini değiştirmez; yabancı yedek ayrı konudur.

Yalnız normal HTTPS ölçümü örneği (ayar değiştirmez; VDS'de ağ isteği gönderir):

```bash
curl --disable --noproxy '*' -sS --connect-timeout 5 --max-time 15 \
  -o /dev/null -w 'HTTP=%{http_code} TLS=%{ssl_verify_result}\n' \
  https://www.wattpad.com/
```

curl 35/TLS kurulumu ile HTTP 403/429 gibi uygulama/CDN yanıtlarını aynı sorun sayma. HTTP 200 dahi gerçek giriş/okuma kabulünün yerini tutmaz. Telefon/PC'de uygulama testi olmadan “çözüldü” denmez.

Resmî kaynaklar:
- <https://github.com/bol-van/zapret2/tree/v1.0.7>
- <https://github.com/bol-van/zapret2/blob/v1.0.7/config.default>
- <https://github.com/bol-van/zapret2/blob/v1.0.7/docs/manual.en.md#config-file>
- <https://github.com/bol-van/zapret2/blob/v1.0.7/docs/manual.en.md#blockcheck2>
