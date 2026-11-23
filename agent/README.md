# Agent

Lekki serwer na VPS. Wykonuje ruch lokalnie, sterowany przez koordynatora.

## Instalacja na VPS

```bash
sudo apt update && sudo apt install -y python3-venv
cd /opt && sudo mkdir epagent && sudo chown $USER epagent && cd epagent
git clone https://github.com/deloskiytbackup/ep-ddos.git .
python3 -m venv .venv && . .venv/bin/activate
pip install aiohttp python-dotenv
cp agent/.env.example agent/.env
nano agent/.env   # ustaw AGENT_TOKEN i AGENT_NAME
```

## Uruchomienie

```bash
. .venv/bin/activate
python3 -m agent.server
```

## systemd (produkcja)

```ini
[Unit]
Description=EP Agent
After=network.target

[Service]
User=epagent
WorkingDirectory=/opt/epagent
EnvironmentFile=/opt/epagent/agent/.env
ExecStart=/opt/epagent/.venv/bin/python -m agent.server
Restart=always

[Install]
WantedBy=multi-user.target
```

## Wymagania

- publiczny port 8787 (albo za reverse proxy)
- AGENT_TOKEN musi byc **ten sam** co u koordynatora
- warto podniesc limity: `ulimit -n 65535`
