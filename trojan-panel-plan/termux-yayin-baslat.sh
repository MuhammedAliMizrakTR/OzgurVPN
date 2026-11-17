#!/usr/bin/env bash
# Mualiy Termux/VDS launcher for the checksum-pinned publisher.
# Run this as the ordinary VDS user, never as root and never through a pipe.
# It never accepts or prints panel, Cloudflare, tunnel, or Trojan secrets.
set -Eeuo pipefail

readonly SOURCE_COMMIT='a59ca8066976a2d904c010bdf9c7f1ba5ad8542f'
readonly SOURCE_SHA256='7e5d51dec9be2858abf5d6484602f2cf351b043c1fea77925f22929d7fb07f5e'
readonly SOURCE_URL="https://raw.githubusercontent.com/MuhammedAliMizrakTR/OzgurVPN/${SOURCE_COMMIT}/trojan-panel-plan/mualiy-yayinla.py"
# Do not replace a manually transferred or older launcher at ~/mualiy-yayinla.py.
readonly DESTINATION="${HOME:?HOME gerekli}/mualiy-yayinla-7e5d51de.py"

die() {
    printf 'DUR: %s\n' "$*" >&2
    exit 1
}

usage() {
    cat <<'USAGE'
Kullanim:
  bash ~/mualiy-yayin-baslat.sh --dry-run
  bash ~/mualiy-yayin-baslat.sh --apply

--dry-run yalnız GitHub'dan sabitlenmiş kaynak indirme + SHA-256 doğrular;
VDS paneli, Docker, Cloudflare veya yerel hedef dosya değişmez.
--apply doğrulanmış dosyayı ~/mualiy-yayinla-7e5d51de.py olarak kaydeder ve gizli
bilgileri yalnız VDS terminalinde soran yayın aracını sudo ile başlatır.
USAGE
}

mode="${1:-}"
case "$mode" in
    --dry-run|--apply) ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
esac

[ "$(id -u)" -ne 0 ] || die 'Bu baslaticiyi root olarak degil, normal VDS kullanicisi olarak calistir.'
case "$HOME" in
    /*) ;;
    *) die 'HOME mutlak bir kullanici dizini olmali.' ;;
esac
[ -d "$HOME" ] && [ ! -L "$HOME" ] || die 'HOME dizini guvenli bir normal dizin degil.'

if [ "$mode" = '--apply' ]; then
    [ -t 0 ] && [ -t 1 ] || die 'Gizli girisler icin pipe kullanma; dosyayi dogrudan VDS terminalinde calistir.'
fi

for tool in curl sha256sum python3 mktemp; do
    command -v "$tool" >/dev/null 2>&1 || die "Gerekli komut yok: $tool; otomatik paket kurulumu yapilmadi."
done
if [ "$mode" = '--apply' ]; then
    command -v sudo >/dev/null 2>&1 || die 'Gerekli komut yok: sudo; otomatik paket kurulumu yapilmadi.'
fi

verify_source() {
    printf '%s  %s\n' "$SOURCE_SHA256" "$1" | sha256sum --check --status -
}

temporary=''
cleanup() {
    [ -z "$temporary" ] || rm -f -- "$temporary"
}
trap cleanup EXIT HUP INT TERM

if [ -L "$DESTINATION" ]; then
    die "Hedef sembolik link; uzerine yazilmadi: $DESTINATION"
elif [ -e "$DESTINATION" ]; then
    [ -f "$DESTINATION" ] || die "Hedef normal dosya degil; uzerine yazilmadi: $DESTINATION"
    verify_source "$DESTINATION" || die "Var olan $DESTINATION beklenen sabit kaynak degil; uzerine yazilmadi."
    printf 'Mevcut yayin dosyasinin SHA-256 degeri dogrulandi.\n'
else
    temporary="$(umask 077; mktemp "$HOME/.mualiy-yayinla.XXXXXX")"
    printf 'Sabitlenmis yayin kaynagi indiriliyor ve SHA-256 dogrulaniyor...\n'
    curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
        --retry 2 --connect-timeout 15 --max-time 120 \
        "$SOURCE_URL" >"$temporary" || die 'GitHub kaynagi indirilemedi; VDS agini kontrol et. Hicbir yayin degisikligi yapilmadi.'
    verify_source "$temporary" || die 'Indirilen yayin kaynagi beklenen SHA-256 degerinde degil; hicbir yayin degisikligi yapilmadi.'
    chmod 0700 "$temporary"
fi

if [ "$mode" = '--dry-run' ]; then
    printf 'DRY-RUN BASARILI: sabit kaynak SHA-256 ile dogrulandi. Panel/Docker/Cloudflare/hedef dosya degismedi.\n'
    exit 0
fi

# Authenticate before writing the verified source locally. This still makes no service change.
sudo -v || die 'sudo yetkilendirmesi basarisiz; hicbir yayin degisikligi yapilmadi.'
if [ -n "$temporary" ]; then
    mv -- "$temporary" "$DESTINATION"
    temporary=''
    printf 'Dogrulanmis yayin dosyasi kaydedildi: %s\n' "$DESTINATION"
fi

printf '%s\n' 'Sadece bu VDS terminalinde sorulacak panel/Cloudflare/Tunnel bilgilerini gir. Bunlari sohbete gonderme.'
exec sudo python3 "$DESTINATION" --apply
