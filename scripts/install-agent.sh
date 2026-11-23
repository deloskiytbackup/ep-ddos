#!/usr/bin/env bash
# install-agent.sh - automatyczna instalacja agenta EP DDoS na VPS.
#
# Uzycie:
#   curl -fsSL https://raw.githubusercontent.com/deloskiytbackup/ep-ddos/main/scripts/install-agent.sh | sudo bash -s -- --token TOKEN
#   sudo ./install-agent.sh --token TOKEN [--name vps1] [--port 8787] [--firewall]
#   sudo ./install-agent.sh --uninstall

set -Eeuo pipefail

REPO="https://github.com/deloskiytbackup/ep-ddos.git"
DIR="/opt/epagent"
USER_NAME="epagent"
SERVICE="epagent"
PORT="8787"
NAME="$(hostname -s 2>/dev/null || echo agent)"
TOKEN=""
FIREWALL=0
UNINSTALL=0

c_red=$'\e[31m'; c_grn=$'\e[32m'; c_ylw=$'\e[33m'; c_rst=$'\e[0m'
info() { echo "${c_grn}[+]${c_rst} $*"; }
warn() { echo "${c_ylw}[!]${c_rst} $*"; }
die()  { echo "${c_red}[x]${c_rst} $*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --token)     TOKEN="${2:-}"; shift 2 ;;
    --name)      NAME="${2:-}"; shift 2 ;;
    --port)      PORT="${2:-}"; shift 2 ;;
    --firewall)  FIREWALL=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help)   sed -n '2,8p' "$0"; exit 0 ;;
    *) die "nieznany argument: $1" ;;
  esac
done

[[ $EUID -eq 0 ]] || die "uruchom jako root (sudo)"

if [[ $UNINSTALL -eq 1 ]]; then
  info "usuwam agenta"
  systemctl disable --now "$SERVICE" 2>/dev/null || true
  rm -f "/etc/systemd/system/$SERVICE.service"
  systemctl daemon-reload
  rm -rf "$DIR"
  id "$USER_NAME" &>/dev/null && userdel "$USER_NAME" 2>/dev/null || true
  info "gotowe"
  exit 0
fi

[[ -n $TOKEN ]] || die "podaj --token (ten sam co u koordynatora)"
[[ $TOKEN =~ ^[A-Za-z0-9_-]{16,}$ ]] || warn "token krotki/nietypowy"

info "instaluje zaleznosci"
if command -v apt-get &>/dev/null; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq python3 python3-venv python3-pip git curl >/dev/null
elif command -v dnf &>/dev/null; then
  dnf install -y -q python3 python3-pip git curl >/dev/null
elif command -v yum &>/dev/null; then
  yum install -y -q python3 python3-pip git curl >/dev/null
else
  die "nie znam menedzera pakietow"
fi

id "$USER_NAME" &>/dev/null || useradd --system --home "$DIR" --shell /usr/sbin/nologin "$USER_NAME"

if [[ -d $DIR/.git ]]; then
  info "aktualizuje istniejaca instalacje"
  git -C "$DIR" fetch --quiet origin
  git -C "$DIR" reset --hard --quiet origin/main
else
  info "klonuje repozytorium"
  rm -rf "$DIR"
  git clone --quiet --depth 1 "$REPO" "$DIR"
fi

info "tworze srodowisko python"
[[ -d $DIR/.venv ]] || python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install --quiet --upgrade pip
"$DIR/.venv/bin/pip" install --quiet aiohttp python-dotenv

info "zapisuje konfiguracje"
mkdir -p "$DIR/agent"
cat > "$DIR/agent/.env" <<EOF
AGENT_TOKEN=$TOKEN
AGENT_NAME=$NAME
AGENT_PORT=$PORT
EOF
chmod 600 "$DIR/agent/.env"

info "instaluje usluge systemd"
cat > "/etc/systemd/system/$SERVICE.service" <<EOF
[Unit]
Description=EP DDoS Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER_NAME
Group=$USER_NAME
WorkingDirectory=$DIR
EnvironmentFile=$DIR/agent/.env
ExecStart=$DIR/.venv/bin/python -m agent.server
Restart=always
RestartSec=3
LimitNOFILE=65535

# hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$DIR
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true
MemoryDenyWriteExecute=false

[Install]
WantedBy=multi-user.target
EOF

chown -R "$USER_NAME:$USER_NAME" "$DIR"
chmod 755 "$DIR"

if [[ $FIREWALL -eq 1 ]]; then
  info "otwieram port $PORT"
  if command -v ufw &>/dev/null; then
    ufw allow "$PORT/tcp" >/dev/null 2>&1 || true
  elif command -v firewall-cmd &>/dev/null; then
    firewall-cmd --permanent --add-port="$PORT/tcp" >/dev/null 2>&1 || true
    firewall-cmd --reload >/dev/null 2>&1 || true
  else
    warn "brak ufw/firewalld - otworz port $PORT recznie"
  fi
fi

systemctl daemon-reload
systemctl enable --now "$SERVICE" >/dev/null 2>&1
sleep 2

if systemctl is-active --quiet "$SERVICE"; then
  IP="$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || echo '<twoje-ip>')"
  info "agent dziala"
  echo
  echo "  Dodaj do .env koordynatora:"
  echo "  AGENTS=$NAME|http://$IP:$PORT|1"
  echo
else
  die "usluga nie wstala - sprawdz: journalctl -u $SERVICE -n 30"
fi
