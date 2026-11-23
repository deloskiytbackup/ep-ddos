# Architektura

## Model

Koordynator (bot) nie wysyla ruchu. Rozdziela zadania na agentow.

1. `/start` -> walidacja URL, sprawdzenie limitu
2. `cluster.split()` -> podzial watkow wg wag
3. POST `/launch` do kazdego agenta
4. petla `_poll` co 1 s -> GET `/stats` -> agregacja
5. stop/czas -> POST `/stop/{id}`

## Bezpieczenstwo

- kazde zadanie agenta wymaga naglowka `X-Agent-Token`
- brak tokenu = 401
- agenci nie przyjmuja zadan spoza klastra

## Odpornosc

- health-check co 10 s, martwi agenci pomijani
- brak zywych agentow = blad, nie cichy atak
- kazdy agent ma wlasna pule workerow

## Skalowanie

Dodanie VPS = dopisanie do `AGENTS` z waga. Wiecej agentow = wiecej pasma.
Waga 1 = rownowartnie, waga 3 = trzy razy wiecej ruchu.
