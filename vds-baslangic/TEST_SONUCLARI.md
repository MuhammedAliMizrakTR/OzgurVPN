> **TARİHSEL KANIT:** ilk ön-kontrol fixture raporu. Yeniden çalıştırılan devir testleri `../DEVIR_TEST_SONUCLARI.json` içindedir; gerçek VDS sağlık raporu değildir.

# Ön kontrol betiğinin test sonuçları

Tarih: 2026-11-14

Komut:

```bash
python3 test_preflight.py
```

**8 test / 8 başarılı.** Ağ ve servis araçları mock edildi; Discord, Roblox veya Wattpad'e bu testlerde gerçek ağ isteği yapılmadı.

1. Bash sözdizimi.
2. Yardım seçeneği: hiçbir denetim/ağ çağrısı veya rapor oluşturmaz.
3. Geçersiz alan adı reddi; girilen örnek token hata çıktısına yansıtılmaz.
4. `--no-network --stdout-only`: ağ sorgusu ve rapor dosyası yok.
5. Rapor dosyası `0600`; yerel bind IP'leri ve servis `ExecStart`/token bilgisi sorgulanmaz.
6. IPv6 varsa 5 IPv4 + 5 IPv6 + 3 DoH sorgusu oluşturulur; sertifika kontrolü kapatılmaz; curlrc/proxy/SSLKEYLOGFILE kullanılmaz. Büyük curl yardım çıktısında DoH tespiti korunur.
7. Her istek zaman aşımına uğrasa bile sonraki testler devam eder; IPv6 rota ipucu yokken 5 IPv4 + 3 DoH ile devam edilir.
8. Bilinmeyen seçenek hiçbir denetim başlatmadan reddedilir.

Ek olarak `bash vds-on-kontrol.sh --no-network --stdout-only` Arena'nın Debian 13 çalışma alanında çalıştırıldı; çıktı başarıyla üretildi. **Bu, kullanıcının Ubuntu VDS'sinde çalışma veya bağlantı testi değildir.**

## Henüz yapılmayanlar

- Kullanıcının VDS'sine SSH bağlantısı, işletim sistemi sürümü/yetki doğrulaması.
- Gerçek VDS'de ön kontrol betiği.
- Trojan/sing-box veya zapret2 kurulumu, Docker çalıştırma.
- Android TUN kurulumu; Discord ses, Roblox oyun, Wattpad okuma oturumu.
- DNS/IPv6 kaçak, kill switch, gerçek UDP ve uzun süreli kararlılık testi.
- Hax/Woiden veya başka sağlayıcıda tahsis/yenileme, Telegram botu entegrasyonu.

Araştırma amaçlı Tor bağlantısı ve başarısız onion erişim denemeleri ayrıdır; bunlar için `ARASTIRMA.md`ye bak.
