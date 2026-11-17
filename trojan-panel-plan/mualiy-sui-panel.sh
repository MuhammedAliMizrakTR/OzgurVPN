#!/usr/bin/env bash
# Mualiy S-UI: first-stage, loopback-only panel bootstrap.
# This is NOT a Trojan migration, certificate installer or cloudflared installer.
# The existing ozgur-trojan.service, Minecraft, Crafty and Jitsi are not stopped.
set -Eeuo pipefail
umask 077

MODE="${1:---check}"
TARGET=/opt/mualiy-sui
PROJECT=mualiy-sui
IMAGE='alireza7/s-ui:v1.6.7@sha256:c262ebd5cd53fd098d3080089af46220473bacbaf1a113e767aa9aadd2eed36d'
TMP=
OWNED_TARGET=0
UP_ATTEMPTED=0
SUCCESS=0

fail() { printf 'DUR: %s\n' "$*" >&2; exit 1; }

compose_content() {
cat <<'YAML'
name: mualiy-sui
services:
  panel:
    image: alireza7/s-ui:v1.6.7@sha256:c262ebd5cd53fd098d3080089af46220473bacbaf1a113e767aa9aadd2eed36d
    platform: linux/amd64
    user: "10001:10001"
    restart: "no"
    init: true
    environment:
      TZ: Europe/Istanbul
      SUI_DB_FOLDER: /app/db
      SUI_LOG_LEVEL: warn
    ports:
      - "127.0.0.1:2095:2095/tcp"
      - "127.0.0.1:2096:2096/tcp"
    volumes:
      - type: bind
        source: ./db
        target: /app/db
        bind:
          create_host_path: false
      - type: bind
        source: ./cert
        target: /app/cert
        read_only: true
        bind:
          create_host_path: false
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    mem_limit: 512m
    cpus: "1.0"
    pids_limit: 256
    stop_grace_period: 20s
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
YAML
}

cleanup() {
  local code=$?
  trap - EXIT
  if [[ "$OWNED_TARGET" == 1 && "$UP_ATTEMPTED" == 1 && "$SUCCESS" != 1 ]]; then
    printf '\nYeni panelin kurulumu tamamlanamadi; yalniz bu yeni proje durduruluyor.\n' >&2
    docker compose --project-name "$PROJECT" --file "$TARGET/compose.yaml" stop >&2 || true
  fi
  if [[ -n "$TMP" && -d "$TMP" ]]; then
    rm -rf -- "$TMP"
  fi
  if [[ $code -ne 0 && "$OWNED_TARGET" == 1 ]]; then
    printf 'Dosyalar silinmedi: %s. Tekrar kurmaya veya dizini silmeye calisma; hatayi paylas.\n' "$TARGET" >&2
  fi
  exit "$code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

[[ "$MODE" == --check || "$MODE" == --apply ]] || fail 'Kullanim: sudo bash mualiy-sui-panel.sh [--check|--apply]'
[[ $# -le 1 ]] || fail 'Fazla arguman verildi.'
[[ $EUID -eq 0 ]] || fail 'VDS terminalinde sudo bash ile calistir.'
[[ "$(uname -m)" == x86_64 ]] || fail 'Bu sabit paket Linux x86_64 VDS icindir.'
for tool in docker ss python3 install mktemp flock curl; do
  command -v "$tool" >/dev/null 2>&1 || fail "Gerekli komut bulunamadi: $tool. Otomatik paket kurulumu yapilmadi."
done

# Never target an alternate remote Docker context inherited by the root shell.
unset DOCKER_CONTEXT DOCKER_TLS_VERIFY DOCKER_CERT_PATH
export DOCKER_HOST=unix:///var/run/docker.sock

# Serialise only our own bootstrap, not other Docker projects.
exec 9>/run/lock/mualiy-sui-panel.lock
flock -n 9 || fail 'Ayni panel icin baska bir kurulum calisiyor.'

[[ ! -e "$TARGET" && ! -L "$TARGET" ]] || fail "$TARGET zaten var; hicbir dosyanin uzerine yazilmadi."

ENGINE=$(docker version --format '{{.Server.Version}}') || fail 'Yerel Docker daemonuna erisilemiyor.'
python3 - "$ENGINE" <<'PY'
import re, sys
m = re.match(r'^(\d+)\.(\d+)', sys.argv[1])
if not m or int(m.group(1)) < 28:
    raise SystemExit('DUR: loopback port yayini icin Docker Engine 28+ gerekli. Docker otomatik guncellenmedi.')
PY

docker compose version >/dev/null
EXISTING=$(docker ps -aq --filter "label=com.docker.compose.project=$PROJECT")
[[ -z "$EXISTING" ]] || fail 'Ayni adli Compose projesi zaten var; mevcut konteynerlere dokunulmadi.'

LISTENERS=$(ss -H -lnt '( sport = :2095 or sport = :2096 )')
[[ -z "$LISTENERS" ]] || fail '2095/2096 portlarindan biri dinleniyor. Baska servis durdurulmadi.'

# Docker can publish a port using NAT without a listening docker-proxy socket.
# Inspect only its formatted port list, never environment variables or tokens.
PORTS=$(docker ps --format '{{.Ports}}')
python3 - "$PORTS" <<'PY'
import re, sys
for match in re.finditer(r':(\d+)(?:-(\d+))?->', sys.argv[1]):
    start = int(match.group(1))
    end = int(match.group(2) or start)
    if any(start <= p <= end for p in (2095, 2096)):
        raise SystemExit('DUR: Docker 2095/2096 portunu zaten yayinliyor. Mevcut proje degistirilmedi.')
PY

TMP=$(mktemp -d /tmp/mualiy-sui-check.XXXXXXXX)
compose_content > "$TMP/compose.yaml"
docker compose --project-name "$PROJECT" --file "$TMP/compose.yaml" config --quiet
printf 'On kontrol OK. Docker=%s; panel portlari bos; image digest sabit.\n' "$ENGINE"
printf 'Mevcut 8443 Trojan, Minecraft/Crafty/Jitsi ve cloudflared degistirilmeyecek.\n'

if [[ "$MODE" == --check ]]; then
  printf 'Kontrol bitti. Kurulum icin ayni dosyayi --apply ile calistir.\n'
  exit 0
fi

# Pull by immutable digest before creating our persistent directory.
# This does not update or restart any existing container/image deployment.
docker pull --platform linux/amd64 "$IMAGE"

# mkdir without -p intentionally refuses an existing directory/symlink.
mkdir -m 0750 -- "$TARGET"
OWNED_TARGET=1
install -d -m 0700 -o 10001 -g 10001 "$TARGET/db"
install -d -m 0750 -o root -g 10001 "$TARGET/cert"
install -m 0644 "$TMP/compose.yaml" "$TARGET/compose.yaml"
printf '%s\n' 'mualiy-sui-loopback-bootstrap-v1' > "$TARGET/.mualiy-managed"

docker compose --project-name "$PROJECT" --file "$TARGET/compose.yaml" config --quiet
UP_ATTEMPTED=1
docker compose --project-name "$PROJECT" --file "$TARGET/compose.yaml" \
  up -d --wait --wait-timeout 120

curl --disable --noproxy '*' --fail --silent --show-error \
  --connect-timeout 3 --max-time 15 --output /dev/null \
  --write-out 'Yerel panel HTTP=%{http_code}\n' \
  http://127.0.0.1:2095/app/

SUCCESS=1
printf '\nPanel ilk asamasi hazir.\n'
printf 'VDS ThinLinc Firefox adresi: http://127.0.0.1:2095/app/\n'
printf 'Ilk giris: admin / admin. HEMEN panel icinden kullanici adi ve parolayi degistir.\n'
printf 'Bunu yapmadan Cloudflare Tunnel veya herkese acik panel kaydi ekleme.\n'
printf 'Trojan portu yayinlanmadi; mevcut 8443 servisi ve sertifikasi degismedi.\n'
printf 'Yeni panelin otomatik baslangici bilerek kapali; mevcut diger projeler degismedi.\n'
printf 'Bu uygulama Docker icinde yeni bir bridge agi ve loopback port yonlendirmeleri olusturur.\n'
printf 'Yalniz bu paneli durdurmak icin:\n'
printf 'sudo docker compose --project-name mualiy-sui --file /opt/mualiy-sui/compose.yaml stop\n'
