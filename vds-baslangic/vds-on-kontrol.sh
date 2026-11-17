#!/usr/bin/env bash
# VDS on kontrolu: ag/sistem ayarlarini degistirmez, kurulum yapmaz.
# Istege bagli HTTPS/DNS istekleri ve yalnizca ozel izinli bir rapor dosyasi.
# Parola, .env, SSH anahtari, cloudflared token'i veya servis ExecStart'i okunmaz.
set -uo pipefail
umask 077
unset SSLKEYLOGFILE
export LC_ALL=C SYSTEMD_PAGER=cat SYSTEMD_COLORS=0

VERSION='1.0.0'
NETWORK=1
SAVE_REPORT=1
PUBLIC_HOST=''

usage() {
  cat <<'EOF'
Kullanim: bash vds-on-kontrol.sh [secenekler]

  --hostname ALAN_ADI  Istege bagli: sana ait genel alan adinin DNS'ini de goster.
                      Protokol, URL, token, yol veya parola verme.
  --no-network        DNS/HTTPS testi yapma; sadece yerel on kontrol.
  --stdout-only       Rapor dosyasi olusturma; sadece terminale yaz.
  -h, --help          Bu yardim.

Bu dosyayi kendi Ubuntu VDS'nin SSH terminalinde calistir.
Hicbir sey kurmaz; firewall, rota, DNS ve servis ayarlarini degistirmez.
Varsayilan ag testleri Discord, Roblox, Wattpad ve Cloudflare DoH'ye gider.
HTTP 200/403 veya TLS basarisi tek basina tum uygulamanin calistigini kanitlamaz.
EOF
}

valid_host() {
  local host=$1 label
  [[ ${#host} -ge 1 && ${#host} -le 253 && $host == *.* ]] || return 1
  [[ $host != *..* && $host != .* && $host != *. ]] || return 1
  [[ $host != *[!A-Za-z0-9.-]* ]] || return 1
  local -a labels
  IFS='.' read -r -a labels <<< "$host"
  for label in "${labels[@]}"; do
    [[ ${#label} -ge 1 && ${#label} -le 63 ]] || return 1
    [[ $label =~ ^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?$ ]] || return 1
  done
}

while (( $# > 0 )); do
  case "$1" in
    --hostname)
      if (( $# < 2 )) || ! valid_host "$2"; then
        printf '%s\n' 'Hata: --hostname icin yalnizca gecerli ASCII/punycode alan adi gerekli.' >&2
        exit 2
      fi
      PUBLIC_HOST=$2; shift 2 ;;
    --no-network) NETWORK=0; shift ;;
    --stdout-only) SAVE_REPORT=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Bilinmeyen secenek. --help kullan.\n' >&2; exit 2 ;;
  esac
done

section() { printf '\n=== %s ===\n' "$1"; }
has() { command -v "$1" >/dev/null 2>&1; }

# Ubuntu'daki GNU timeout kullanilir; yoksa belirsiz sureli sorgu calistirilmaz.
bounded() {
  if has timeout; then
    timeout --signal=TERM --kill-after=1s 8s "$@"
  else
    printf '%s\n' 'ATLANDI: timeout araci yok.' >&2
    return 125
  fi
}

version_line() {
  local name=$1
  shift
  if has "$name"; then
    bounded "$name" "$@" 2>&1 | head -n 2 || true
  else
    printf '%s: bulunamadi\n' "$name"
  fi
}

ports_summary() {
  local proto=$1 flag=$2 text
  if ! has ss; then printf 'ss bulunamadi; %s portlari okunamadi.\n' "$proto"; return; fi
  if ! text=$(bounded ss -H "$flag" 2>/dev/null); then
    printf '%s dinleme listesi okunamadi.\n' "$proto"; return
  fi
  # Yerel IP adreslerini ve surec argumanlarini rapora almadan ozetle.
  printf '%s\n' "$text" | awk -v proto="$proto" '
    BEGIN { split("80 443 8443 18080 19080", wanted, " ") }
    NF >= 4 {
      n=split($4,a,":"); p=a[n]
      if(p ~ /^[0-9]+$/) seen[p]=1
    }
    END {
      for(i=1;i<=5;i++) {
        p=wanted[i]
        printf "%s %s: %s\n", proto, p, (seen[p] ? "dinlemede" : "bu ag ad alaninda dinleyici gorulmedi")
      }
    }'
}

https_probe() {
  local mode=$1 url=$2 family=$3 result code
  shift 3
  printf '\n[%s] %s\n' "$mode" "$url"
  # --disable ilk secenektir: kullanicinin .curlrc dosyasini okumaz.
  # Proxy ortam degiskenleri kullanilmaz, sertifika dogrulamasi kapatilmaz.
  # Yonlendirmeler izlenmez; govde kaydedilmez. Her istek <=10 saniye.
  result=$(curl --disable --noproxy '*' --proto '=https' "$family" \
    --silent --show-error --connect-timeout 4 --max-time 10 \
    --max-filesize 524288 --output /dev/null \
    --write-out 'http=%{http_code} hedef_ip=%{remote_ip} tls_sonucu=%{ssl_verify_result} sure=%{time_total}s' \
    "$@" "$url" 2>&1)
  code=$?
  printf '%s\ncurl_exit=%s\n' "$result" "$code"
  if (( code == 63 )); then
    printf '%s\n' 'NOT: 512 KiB govde sinirina ulasildi; bu hata tek basina baglanti engeli degildir.'
  fi
}

main() {
  printf 'VDS ON KONTROL %s\n' "$VERSION"
  printf '%s\n' 'Kurulum yapilmaz; ag/sistem yapilandirmasi degistirilmez.'
  printf '%s\n' 'Parola/token/anahtar/.env/servis komut satiri okunmaz.'
  printf 'UTC: '; date -u '+%Y-%m-%dT%H:%M:%SZ'

  section 'Isletim sistemi ve kaynaklar'
  if [[ -r /etc/os-release ]]; then
    grep -E '^(PRETTY_NAME|ID|VERSION_ID|VERSION_CODENAME)=' /etc/os-release || true
  fi
  printf 'Mimari: '; uname -m
  printf 'Cekirdek: '; uname -r
  printf 'root olarak calisiyor: '; if (( EUID == 0 )); then echo evet; else echo hayir; fi
  printf 'sudo araci mevcut: '; if has sudo; then echo evet; else echo hayir; fi
  printf '%s\n' 'NOT: sudo bulunmasi, kullanicinin sudo yetkisi oldugunu kanitlamaz.'
  if [[ -r /proc/meminfo ]]; then awk '/^MemTotal:/ {printf "Toplam RAM: %s KiB\n",$2}' /proc/meminfo; fi
  if has df; then df -h / 2>/dev/null | awk 'NR==1 {print "Disk /: toplam kullanilan bos doluluk"} NR==2 {print $2,$3,$4,$5}'; fi
  if has systemd-detect-virt; then
    printf 'Sanallastirma: '; bounded systemd-detect-virt 2>/dev/null || true
  fi

  section 'Araclarin surumleri'
  version_line curl --version
  version_line cloudflared --version
  version_line sing-box version
  version_line nft --version
  version_line iptables --version

  section 'Mevcut servislerin sadece durum bilgisi'
  if has systemctl; then
    local unit state
    for unit in cloudflared.service sing-box.service zapret2.service; do
      state=$(bounded systemctl is-active "$unit" 2>/dev/null) || true
      printf '%s: %s\n' "$unit" "${state:-okunamadi}"
    done
  else
    printf '%s\n' 'systemctl yok.'
  fi
  printf 'cloudflared adli surec goruldu: '
  if has pgrep; then
    if bounded pgrep -x cloudflared >/dev/null 2>&1; then echo evet; else echo hayir; fi
  else echo bilinmiyor; fi
  local cfg
  for cfg in /etc/cloudflared/config.yml /etc/cloudflared/config.yaml; do
    if [[ -e $cfg ]]; then printf '%s mevcut; icerigi okunmadi.\n' "$cfg"; fi
  done
  printf '%s\n' 'Farkli adla, kullanici servisiyle veya container icinde calisan servisler bu listede gorunmeyebilir.'
  printf '%s\n' 'Tunnel tokenlari ve ExecStart ozellikle sorgulanmaz.'

  section 'Portlar (yalniz mevcut ag ad alani)'
  ports_summary TCP -lnt
  ports_summary UDP -lnu
  printf '%s\n' 'Dinleyici gorulmemesi; portun firewall, NAT veya saglayici tarafinda acik oldugu anlamina gelmez.'

  section 'zapret2 / NFQUEUE icin yerel ipuclari'
  if [[ -d /sys/module/nfnetlink_queue ]]; then
    printf '%s\n' 'nfnetlink_queue: yuklu modul goruldu.'
  elif has modinfo && bounded modinfo nfnetlink_queue >/dev/null 2>&1; then
    printf '%s\n' 'nfnetlink_queue: modul bilgisi var; yuklu oldugu dogrulanmadi.'
  else
    printf '%s\n' 'nfnetlink_queue: bu yetkiyle dogrulanamadi. Destek yok sonucu cikarilamaz.'
  fi
  printf '/dev/net/tun karakter aygiti: '
  if [[ -c /dev/net/tun ]]; then echo var; else echo gorulmedi; fi
  printf '%s\n' 'Trojan sunucusu icin TUN zorunlu degildir; Android TUN modu ayri konudur.'
  printf '%s\n' 'NFQUEUE kurali, modprobe veya firewall degisikligi YAPILMADI.'

  section 'IPv6 rota ipucu'
  local has_v6=0
  if has ip; then
    if bounded ip -6 route show default 2>/dev/null | grep -q .; then
      has_v6=1; printf '%s\n' 'Varsayilan IPv6 rotasi goruldu; internet erisimi henuz kanitlanmadi.'
    else
      printf '%s\n' 'Varsayilan IPv6 rotasi gorulmedi; IPv6 baglanti denemeleri atlanacak.'
    fi
  else
    printf '%s\n' 'ip araci yok; IPv6 rota kontrolu ve IPv6 denemeleri atlanacak.'
  fi

  if (( NETWORK == 0 )); then
    section 'Ag testleri'; printf '%s\n' '--no-network nedeniyle DNS/HTTPS testi yapilmadi.'
    return 0
  fi
  if ! has curl; then
    section 'Ag testleri'; printf '%s\n' 'curl yok. Otomatik kurulum yapilmadi; HTTPS testleri atlandi.'
    return 0
  fi

  section 'Sistem DNS ile adres ailelerinin varligi'
  local host family count
  local -a hosts=(discord.com gateway.discord.gg www.roblox.com games.roblox.com www.wattpad.com)
  if [[ -n $PUBLIC_HOST ]]; then hosts+=("$PUBLIC_HOST"); fi
  if has getent; then
    for host in "${hosts[@]}"; do
      for family in ahostsv4 ahostsv6; do
        count=$(bounded getent "$family" "$host" 2>/dev/null | awk '{print $1}' | sort -u | awk 'NF {n++} END {print n+0}')
        printf '%s %s kayit_sayisi=%s\n' "$host" "$family" "$count"
      done
    done
  else printf '%s\n' 'getent yok; DNS ozetleri atlandi.'; fi
  printf '%s\n' 'Kayit_sayisi=0 DNS engeli kaniti degildir; zaman asimi/IPv6 yapilandirmasi da neden olabilir.'

  section 'Dogrudan HTTPS baz olcumu; mevcut zapret/WARP zaten calisiyorsa bu olcumu etkiler'
  local -a urls=(
    'https://discord.com/api/v10/gateway'
    'https://gateway.discord.gg/'
    'https://www.roblox.com/'
    'https://games.roblox.com/v1/games?universeIds=1'
    'https://www.wattpad.com/'
  )
  local url
  for url in "${urls[@]}"; do
    https_probe sistem-dns-ipv4 "$url" -4
    if (( has_v6 == 1 )); then https_probe sistem-dns-ipv6 "$url" -6; fi
  done

  section 'Cloudflare DoH ile karsilastirma; yalniz DNS yolu degisir'
  if bounded curl --disable --help all 2>/dev/null | grep -F -- '--doh-url' >/dev/null; then
    for url in 'https://discord.com/api/v10/gateway' 'https://www.roblox.com/' 'https://www.wattpad.com/'; do
      https_probe doh-ipv4 "$url" -4 \
        --doh-url https://cloudflare-dns.com/dns-query \
        --resolve cloudflare-dns.com:443:1.1.1.1
    done
  else
    printf '%s\n' 'Bu curl surumunde DoH secenegi dogrulanamadi; karsilastirma atlandi.'
  fi

  section 'Sonuclari yorumlama'
  printf '%s\n' \
    'curl_exit=0: istek tamamlandi; HTTP 403/451/5xx uygulama veya engel kaynakli olabilir.' \
    'HTTP 200 bile baska bir engelleme sayfasi olabilir; yalniz HTTP koduyla karar verme.' \
    'curl_exit=6 DNS, 7 baglanti, 28 zaman asimi, 35 TLS, 60 sertifika hatasi olabilir.' \
    'TLS sonucunu curl_exit ile birlikte yorumla; TLS kurulmadan da tls_sonucu=0 gorulebilir.' \
    'Bu testler WebSocket el sikismasi, Discord ses/UDP, Roblox oyun oturumu veya Wattpad giris/okuma testi DEGILDIR.' \
    'Uc sitenin acilmasi tum sansurun kalktigini, kill switch veya DNS/IPv6 sizintisizligini kanitlamaz.' \
    'Bu raporda Trojan/zapret2 KURULMADI; kurulum icin ortamin dogrulanmasi gerekir.'
}

if (( SAVE_REPORT == 1 )); then
  if ! has mktemp || ! has tee; then
    printf '%s\n' 'Hata: mktemp ve tee gerekli. --stdout-only ile dosyasiz calistirabilirsin.' >&2
    exit 1
  fi
  report=$(mktemp './vds-on-kontrol.XXXXXX.txt') || {
    printf '%s\n' 'Hata: bu dizinde rapor olusturulamadi; yazilabilir dizin sec veya --stdout-only kullan.' >&2
    exit 1
  }
  main 2>&1 | tee "$report"
  result=${PIPESTATUS[0]}
  printf '\nRapor dosyasi: %s (izin: yalniz dosya sahibi)\n' "$report"
  printf '%s\n' 'Paylasmadan once yine de gozden gecir; ozel alan adi/IP bilgilerini gizleyebilirsin.'
  exit "$result"
else
  main
fi
