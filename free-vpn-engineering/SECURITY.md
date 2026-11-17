# Güvenlik modeli ve operasyon sınırları

Bu bir prototiptir; bağımsız denetim, penetrasyon testi veya yüksek riskli
kullanım için uygunluk değerlendirmesi yapılmadı.

## Korunan sınırlar

1. **Public internet → Go gateway:** yalnızca tanımlı HTTP yolları; exact WS
   yolu, sınırlı header boyutu, header okuma süresi, global handshake/tünel
   limitleri. Public forward proxy ve CONNECT yöntemi yok.
2. **Go → sing-box:** yalnızca loopback; istemcinin gönderdiği forwarding,
   Cookie ve Authorization header'ları iç servise taşınmaz. Trojan
   kimlik doğrulaması WS açıldıktan sonra çekirdekte yapılır. Bir HTTP 101
   yanıtı tek başına başarılı kimlik doğrulama anlamına gelmez.
3. **Trojan → hedef:** UDP/ICMP ve izinli liste dışındaki portlar reddedilir.
   Domain önce DoH ile çözülür, ardından private/reserved IP kuralları
   uygulanır. IPv4 mapped IPv6 ve NAT64 özel kaçış yüzeyleri engellenir.
4. **Sırlar:** config env'den okunur, hatalar ham JSON/parolayı yazdırmaz.
   Core'a orijinal TROJAN_* secret env değerleri aktarılmaz. Config dosyası
   özel geçici dizinde 0600'dır. Process memory/env ve Docker/Render
   yöneticileri bir gizlilik sınırı değildir; operatör bunlara erişebilir.
5. **Süreç yaşamı:** core düşerse gateway de hata ile çıkar. SIGTERM yeni
   hazırlığı kapatır, upgraded socket'leri kapatır, core'u sonlandırıp reap
   eder ve geçici dosyaları kaldırır. SIGKILL/host kaybında temizlik garantisi
   yoktur; disk/volume şifreleme ve sağlayıcı güveni ayrıca değerlendirilir.

## Kapsam dışında kalanlar

- Tam cihaz TUN/VPN, kill switch, UDP/QUIC, oyun/VoIP, WebRTC ve DNS sızıntısı
  önleme; proxy kullanmayan uygulamalar doğrudan internete çıkabilir.
- Kullanıcı başına kalıcı aylık GB kotası, hız limiti, faturalandırma,
  abuse otomasyonu, üyelik ve MFA.
- Render veya başka sağlayıcının TLS edge, ağ, hypervisor ve log sistemleri.
- Global bağlantı sınırı altında dahi bant genişliği/CPU tüketimi;
  kimlik doğrulanmadan açılmış WS oturumları idle timeout'a kadar slot tutabilir.
- İçerik filtreleme: TCP 80/443 izni, o porttaki her protokolün HTTP olduğu
  anlamına gelmez. Yetkili bir kullanıcı yine kötüye kullanım yapabilir.
- Host seviyesinde egress firewall ve sağlayıcı metadata izolasyonu.
  Uygulama kuralları savunma katmanıdır, bağımsız sert sınır değildir.
- Sürekli anonimlik veya “no-logs”: core hata logları hedef, kullanıcı ve
  bağlantı ayrıntıları içerebilir. Render da kendi metadata/loglarını tutabilir.
- Sansür altında tespit edilemezlik veya erişilebilirlik garantisi.

## Operatör kontrol listesi

- [ ] Sağlayıcıdan proxy/VPN ve üçüncü kişi erişimi için uygunluk doğrulandı.
- [ ] Uzaktan erişim yalnızca geçerli TLS ile; plaintext origin public değil.
- [ ] Her kullanıcıya farklı, kriptografik rastgele parola; ortak parola yok.
- [ ] Render/hesap yetkileri ve MFA; sırlar repoda/issue'da/logda değil.
- [ ] Saat, bant genişliği, build ve ek ücretler Dashboard'da izlendi.
- [ ] Aylık kalıcı kota yoksa geniş herkese açık kayıt açılmadı.
- [ ] Log saklama/erişim/kişisel veri politikası yayımlandı.
- [ ] İptal/rotasyon sonrası aktif oturumların gerçekten kapandığı test edildi.
- [ ] Güvenlik güncellemeleri için core, Go, Alpine ve Actions pin'leri izlendi.
- [ ] Gerçek Render veya hedef sağlayıcı üzerinde ayrıca doğrulama yapıldı.

## Bir açık bulursan

Bu paketin bir bakımcısı veya hazır güvenlik e-postası tanımlı değildir.
Projeyi yayınlayan operatör özel bir güvenlik iletişim kanalı eklemelidir.
Parola, kişisel trafik veya gerçek kullanıcı verisini public issue'ya koyma.
