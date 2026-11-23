# EP DDoS

Rozproszony bot Discord do testow obciazeniowych WWW (HTTP flood).
Koordynator + agenci na VPS. Architektura cogowa, slash komendy, panel na zywo.

## Jak to dziala

```
Discord  ->  BOT (koordynator)  ->  [vps1] [vps2] [vps3]
                    |                      |
              agregacja stats        ruch HTTP
```

Bot nie generuje ruchu sam - rozdziela atak na agentow proporcjonalnie
do ich wagi i zbiera od nich statystyki. Kazdy agent to osobne pasmo.

## Struktura

```
main.py            punkt wejscia koordynatora
config.py          konfiguracja z .env
core/models.py     Target, Stats, Attack
core/engine.py     orkiestracja ataku
core/cluster.py    klient klastra: health-check, podzial, agregacja
cogs/attack.py     /start /stop /status /lista
cogs/info.py       /ping /agenci /info /pomoc
utils/format.py    paski, wykresy, liczby
utils/views.py     panel ataku (komponenty v2)
agent/server.py    API agenta
agent/engine.py    lokalny silnik ruchu
```

## Szybki start (koordynator)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # wpisz token, AGENT_TOKEN, liste AGENTS
python3 main.py
```

## Agent na VPS

Zobacz [agent/README.md](agent/README.md). W skrocie: ten sam AGENT_TOKEN,
`python3 -m agent.server`, port 8787.

Format `AGENTS`: `nazwa|url|waga`, oddzielone `;`. Waga = udzial w ruchu.

## Komendy

| Komenda | Opis |
|---|---|
| `/start url [czas] [watki] [metoda]` | start |
| `/stop id` | stop |
| `/status id` | podglad |
| `/lista` | aktywne |
| `/agenci` | stan klastra |
| `/ping` `/info` `/pomoc` | diagnostyka |

## Parametry ataku

- czas 5-300 s
- watki 1-1000 (dzielone miedzy agentow)
- max 5 rownoleglych atakow
- metody: GET / HEAD / POST

## Ograniczenia

To flood warstwy 7. Nie omija Cloudflare ani WAF. Skutecznosc zalezy
od pasma agentow i limitow celu. Przy `no-store` kazde zadanie bije w backend.
