> **DEVİR NOTU — TARİHLİ ARAŞTIRMA, GÜNCEL TAHSİS KANITI DEĞİL.** Aşağıdaki sağlayıcı/koşul bilgileri araştırma anının notlarıdır; yeniden doğrulanmadan teklif olarak sunulmaz. Sondaki “kurulum/sonuç yok” ifadesi o aşamaya aittir. Güncel ilk öncelik mevcut Docker panelinin yayınıdır; [kök README](../README.md). Tüm sağlayıcıları veya onion alanını tüketen kapsamlı bir tarama değildir.

# Ücretsiz VPS ve onion araştırması

Kontrol tarihi: **14 Kasım 2026**. Yalnız kamuya açık bilgiler okundu. Hesap açılmadı, ödeme yapılmadı, sunucu tahsis edilmedi, sağlayıcı desteğine mesaj gönderilmedi.

## Sonuç

**“Hax ve Woiden dışında ücretsiz VPS kesinlikle yok” denemez.** Başka topluluk, eğitim, sponsorluk ve promosyon modelleri vardır. Ancak ücretsiz, kartsız, sürekli, Docker çalıştıran, en az 100 GB/ay sağlayan ve istenen VPN kullanımına açık bir teklifin gerçekten tahsis edilebilmesi ayrı ayrı doğrulanmalıdır. İlan ile başarılı tahsis aynı şey değildir.

## İncelenen ek adaylar

### FreeVPS.org — gerçek, fakat topluluk şartlı

Resmî sayfa: https://freevps.org/

- NAT KVM; düzenli topluluk tahsisinde 1 çekirdek, 1 GB RAM, 20 GB disk, 250 GB trafik, 20 NAT IPv4 portu ve IPv6 ağı ilan ediliyor.
- LowEndTalk/LowEndSpirit hesabının en az 3 aylık olması, en az 50 anlamlı gönderi, en az 25 teşekkür ve devam eden katılım gerekiyor. Kapasiteye bağlı.
- Public VPN, Tor ağları ve torrent yasak. Kişisel VPN için de seçilen sponsorun AUP'si incelenmeli; açık bir genel izin varsayılmaz.
- SLA yok; topluluk tarafından geri alınabilir.
- Kullanıcı için hemen tahsis yapılabildiği doğrulanmadı.

### Azure for Students — öğrenci doğrulamalı, eğitim amaçlı

- https://azure.microsoft.com/en-us/free/students/
- https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0170p/
- https://azure.microsoft.com/en-us/pricing/details/bandwidth/

Resmî sayfa kart istemeyen uygun tam zamanlı yükseköğretim öğrencilerine 12 ay geçerli 100 ABD doları kredi ve seçili ücretsiz hizmetler sunuyor; seçili VM saatleri ilk 12 ay için. İnternet çıkışının ilk 100 GB/ay kısmı genel bant genişliği fiyatlandırmasında ücretsiz. Disk, genel IP, bölge ve VM boyutu maliyetleri ayrıca hesaplanmalı. Eğitim/test kullanım koşulları var; öğrenci olmayan genel kullanıcıya koşulsuz ücretsiz sunucu değildir. Kredi biterse ödeme planına yükseltilmedikçe abonelik devre dışı kalır. Topluluk VPN'i için genel izin verilmiş gibi sunulmaz.

### Evolution Host — onaylı sponsorluk

- https://evolution-host.com/free-vps.php
- https://evolution-host.com/tos.php

Ücretsiz VPS başvurusu var; web sitesinin popülerliği ve uygunluğu temel seçim ölçütü, başarılı başvurandan sitesinde sağlayıcıdan bahsetmesi isteniyor. Herkese otomatik tahsis değil. Verilecek planın süresi, trafik kotası ve plan özelinde VPN izni başvuru sonucu netleştirilmeli. Başvuru yapılmadı.

### GratisVPS — çelişen resmî sayfalar; uygunluğu doğrulanmadı

- https://gratisvps.net/
- https://gratisvps.net/cvps/
- https://gratisvps.net/terms.html

Ana sayfa: 2 vCPU/2 GB, ücretsiz ve sabit bitiş tarihi yok diye tanıtıyor.
Provisioner sayfası: 6 GB/120 GB/20 TB ve **120 günlük deneme** diyor.
Şartlar: ücretsiz katman için yüksek erişilebilirlik yok; panelde görülen ör. 300 dolarlık bakiyenin **arayüz testi için parasal değeri olmayan sanal token** olduğunu açıkça söylüyor.

Bunlar tek başına sahtekârlık hükmü verdirmez; ancak gerçek, sürekli, kullanılabilir tahsis kanıtı yerine geçmez. Böyle bir bakiyeyi gerçek bulut kredisi gibi değerlendirmiyoruz. Hesap açılmadı ve gerçek SSH erişimi denenmedi.

### AlaVPS — ilan var; tahsis/süre/koşullar doğrulanmadı

- https://alavps.com/vps.html
- https://manage.alavps.com/index.php?rp=/store/free-vps-hosting

Kartsız ücretsiz KVM ilanı ve kamuya açık ürün sayfası var. Ürün sayfası 20 TB trafik ilan ediyor, ayrıca “For Trial” diyor; pazarlama sayfası ücretsiz süresizlikten söz ederken başka yerde promosyon süre sınırları olabileceğini belirtiyor. VPN/proxy yeniden satışını yasaklıyor; bu, her çeşit VPN kullanımına açık izin demek değil. Gerçek tahsis, kesin süre ve plan koşulları doğrulanmadı. Kesin çözüm olarak önerilmiyor.

### VPSWala — 100 GB şartına uymuyor

https://vpswala.org/

Güncel sayfadaki ücretsiz Starter ilanı **10 GB trafik**, 500 MB disk, ARM64 1 vCPU/2 GB diyor; 1 TB trafikli seçenek 30 günlük deneme. Pazarlama metnindeki genel özellikleri ücretsiz plana mal etmiyoruz. İlanın çalışırlığı ayrıca test edilmedi; zaten istenen 100 GB şartını sağlamıyor.

### IBM LinuxONE

https://www.ibm.com/community/z/ibm-linuxone-community-cloud/ isteği 403 döndü. Üçüncü tarafların 120 günlük deneme iddiaları güncel resmî sayfadan doğrulanamadığı için uygun çözüm sayılmadı.

## Hax / Woiden ve yenileme

- Araştırılan Hax alan adı: **https://hax.co.id/**. Kullanıcının yazdığı `hax.id` ile aynı hizmet diye varsayılmaz.
- https://hax.co.id/create-vps/ : VPN Server seçeneği, IPv6, yedek/teknik destek yok; madencilik, spam, torrent ve DDoS yasağı.
- https://wiki.hax.co.id/ipv6-servers/getting-started/ : bir haftalık, yenilenebilir VPS; Data Center yalnız “-select-” ise boş yer yok; tahsis IPv6-only.
- https://t.me/haxserver/156 : 8 Mayıs 2023 tarihli duyuruda işletmeci otomatik yenileme scriptlerinin ziyaretçi/reklam kaybına etkisini gerekçe gösteriyor. Sonraki duyurularda Woiden hizmetinin farklı süreli biçimlerde devam ettiği görülüyor; bu eski kapanış duyurusu bugünkü tam kapanış kanıtı değildir.
- https://t.me/haxserver/169 : 13 Ocak 2024 tarihli bazı konumlarda Docker kısıtlaması.
- https://t.me/haxserver/182 : 26 Mayıs 2025 tarihli kritik veri tabanı arızası. Erişilebilen kanal akışında daha yeni bir düzeltme duyurusu görülmedi; bu tek başına bugünkü çalışırlık hakkında kesin hüküm verdirmez.

Bu oturumda Hax/Woiden oturumu açılmadı, stoklu sunucu tahsis edilmedi, yenileme yapılmadı. Resmî izin verilen otomasyon yöntemi doğrulanmadı; bir Telegram botunun varlığı tüm yenileme mekanizmasının otomasyona açık/izinli olduğunu kanıtlamaz. Hatırlatma, insan onayı ve varsa resmî API akışı ile CAPTCHA aşma birbirinden farklıdır.

## Tor / onion: gerçekten ne yapıldı?

Araştırma, kullanıcının VDS'sinde değil **Arena çalışma alanında** yapıldı. Kullanıcının sunucusuna Tor kurulmadı.

1. Debian'ın paket deposundan Tor istemcisi 0.4.9.15 indirildi, sistem geneline kurmadan geçici önbelleğe açıldı.
2. Yalnız yerel SOCKS portunda araştırma istemcisi başlatıldı; Tor rölesi/çıkış düğümü veya onion sunucusu kurulmadı.
3. Tor bootstrap %100 tamamlandı. SOCKS üzerinden https://check.torproject.org/api/ip isteği HTTP 200 ve **IsTor=true** döndürdü. IP adresi bu rapora alınmadı.
4. https://ahmia.fi/ adresinin yayımladığı resmî v3 onion adresine “free vps”, “free hosting”, “virtual private server” aramaları gönderildi. İlk 15 saniyelik denemeler, ardından 45 saniyelik bağlantı zaman aşımı sınırıyla yapılan tek sorgu denemesi **zaman aşımına uğradı (curl 28, HTTP 000)**.
5. https://anondrop.net/ adresinin kendi yayımladığı onion ana sayfası da 45 saniyelik bağlantı zaman aşımına uğradı.
6. Ahmia'nın clearnet arama URL'si hem doğrudan hem Tor üzerinden ana sayfaya yönlendi; elde edilen sayfa JavaScript olmayan sürümün bulunmadığını söylüyordu. Başarılı canlı onion arama sonuç sayfası okunamadı.
7. Genel web aramasında indekslenmiş onion sonuçları da kontrol edildi. Yetkisiz erişim/“cracking” içerikli ilanlar meşru bir ücretsiz VPS sağlayıcısı olarak sayılmadı; bu forumlara giriş yapılmadı, hesap/kimlik bilgisi/ürün edinilmedi.
8. Arama sonucunda görülen AnonDrop “Free VPS” açıklaması, güncel ana sayfada çalışan ücretsiz tahsis olarak doğrulanamadı: ana sayfa dosya paylaşımı ve başka ücretli VPS sağlayıcılarına indirim bağlantıları gösteriyor.

**Sonuç:** Tor'a çıkış doğrulandı, ancak denenen onion sayfaları okunamadı. “Dark web'in tamamı tarandı” veya “orada kesin başka yok” denemez. Bu araştırmada oradan doğrulanmış, yasal tahsisli ve kriterleri sağlayan ek bir ücretsiz VPS bulunmadı. CAPTCHA veya giriş engeli aşılmadı; bilinmeyen sitelerden çalıştırılabilir dosya/script alınmadı. Geçici Tor işlemi araştırma sonunda kapatıldı.

Ahmia'nın özgün adresi ve onion duyurusu için: https://ahmia.fi/

## Öncelik

Yeni bir sağlayıcıdan sunucu alınmasını beklemek yerine kullanıcının **Ubuntu VDS'si + Android TUN** üzerinde ilk ölçümü yap. Başarılı kurulum veya sansür aşma sonucu henüz yoktur.
