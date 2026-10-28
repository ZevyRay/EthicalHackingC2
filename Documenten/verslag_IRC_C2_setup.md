# Opstelling IRC C2-server (InspIRCd via Docker)

**Project:** Ethical Hacking — Applied Security  
**Student:** Ruben Van Mensel (s142486)  
**Doel:** IRC-server opzetten als C2-kanaal tussen operator (Kali) en RAT-agent (doel-VM)

---

## Inhoudsopgave

1. [Overzicht](#1-overzicht)
2. [Vereisten](#2-vereisten)
3. [Eerste installatie](#3-eerste-installatie)
4. [Container beheren na herstart](#4-container-beheren-na-herstart)
5. [IP-adres ophalen voor .secret](#5-ip-adres-ophalen-voor-secret)
6. [Verbinding testen](#6-verbinding-testen)
7. [.secret invullen](#7-secret-invullen)
8. [Hoe IRC als C2 werkt](#8-hoe-irc-als-c2-werkt)
9. [Veelvoorkomende fouten](#9-veelvoorkomende-fouten)

---

## 1. Overzicht

De C2-infrastructuur bestaat uit drie onderdelen:

```
[Kali VM — aanvaller]
  ├── Docker: InspIRCd IRC server  (poort 6667)
  └── C2Server.py (operator console)
            │
            │  IRC (TCP 6667)
            │
[Windows VM — doel]
  └── RAT.pyw → c2Agent thread (verbindt als bot)
```

De operator typt commando's in `C2Server.py`. Die worden als IRC `PRIVMSG` naar het kanaal gestuurd. De RAT-agent op de doel-VM leest die berichten en voert ze uit. Antwoorden komen terug via hetzelfde kanaal.

InspIRCd wordt als Docker-container gedraaid op de Kali-machine. Er is geen aparte IRC-client nodig — beide scripts (`C2Server.py` en `RAT.pyw`) praten rechtstreeks via TCP met de IRC-server.

---

## 2. Vereisten

- Docker geïnstalleerd op de Kali VM
- Kali VM en doel-VM op hetzelfde netwerk (host-only of NAT in VirtualBox/VMware)
- Python 3 op beide machines

Docker installeren (als dat nog niet gedaan is):
```bash
sudo apt update && sudo apt install docker.io -y
sudo systemctl enable docker
sudo systemctl start docker
```

---

## 3. Eerste installatie

Eenmalig uitvoeren om de container aan te maken en te starten:

```bash
sudo docker run --name ircd --restart unless-stopped -p 6667:6667 -p 6697:6697 inspircd/inspircd-docker
```

| Parameter | Betekenis |
|-----------|-----------|
| `--name ircd` | Geeft de container de naam `ircd` |
| `--restart unless-stopped` | Container herstart automatisch bij Docker-herstart, tenzij je hem zelf stopt |
| `-p 6667:6667` | IRC (onversleuteld) — gebruikt door `RAT.pyw` en `C2Server.py` |
| `-p 6697:6697` | IRC over TLS — voorlopig niet gebruikt, maar beschikbaar |
| `inspircd/inspircd-docker` | Officiële InspIRCd Docker image |

> **Let op:** dit commando werkt alleen de allereerste keer. Als de container al bestaat, geeft Docker de foutmelding `Conflict. The container name "/ircd" is already in use`. Gebruik dan de commando's in sectie 4.

---

## 4. Container beheren na herstart

Na een herstart van Kali is de container al aangemaakt — je hoeft hem alleen te starten:

```bash
sudo docker start ircd
```

Andere nuttige commando's:

| Situatie | Commando |
|----------|---------|
| Container starten | `sudo docker start ircd` |
| Container stoppen | `sudo docker stop ircd` |
| Status controleren | `sudo docker ps` |
| Alle containers zien (ook gestopte) | `sudo docker ps -a` |
| Logs bekijken | `sudo docker logs ircd` |
| Container verwijderen en opnieuw aanmaken | `sudo docker rm ircd` → dan stap 3 opnieuw |

**Automatisch opstarten bij Kali-herstart:**  
Dankzij `--restart unless-stopped` herstart de container automatisch als Docker zelf opstart. Controleer of Docker autostart heeft:

```bash
sudo systemctl enable docker
sudo systemctl status docker
```

---

## 5. IP-adres ophalen voor .secret

Het IP-adres van de Kali-machine is wat je als `c2_server` in `.secret` zet. De doel-VM gebruikt dit adres om verbinding te maken met de IRC-server.

```bash
hostname -I
```

Of meer detail per interface:
```bash
ip addr show
```

Zoek de interface op je interne netwerk (`eth0`, `wlan0`, of `ens33` in VMware). Het adres ziet er typisch zo uit: `192.168.x.x`.

> Gebruik **nooit** `127.0.0.1` als `c2_server` — dat is localhost en is niet bereikbaar vanuit de doel-VM.

---

## 6. Verbinding testen

**Op Kali zelf** — controleer of de IRC-server luistert:
```bash
nc -v 127.0.0.1 6667
```

Je ziet een welkomstbericht van InspIRCd als alles werkt:
```
:inspire.example.com NOTICE * :*** Looking up your hostname...
```
Sluit af met `Ctrl+C`.

**Vanuit de doel-VM (Windows)** — test de netwerkverbinding:
```powershell
Test-NetConnection -ComputerName 192.168.x.x -Port 6667
```

Een succesvolle output toont `TcpTestSucceeded : True`.

---

## 7. .secret invullen

Vul het `.secret` bestand in de projectmap aan met het Kali IP:

```
mail               = rvm855219@gmail.com
gmail_app_password = jctx ycdj inge tein
c2_server          = 192.168.x.x
c2_port            = 6667
c2_channel         = #c2
operator_nick      = operator
```

> `.secret` staat in `.gitignore` en wordt nooit naar de repository gepusht.

Zowel `RAT.pyw` als `C2Server.py` lezen dit bestand via een relatief pad — start beide scripts dus vanuit de map waar `.secret` staat (de projectroot).

---

## 8. Hoe IRC als C2 werkt

IRC (Internet Relay Chat) is een oud tekstprotocol dat ideaal is als C2-kanaal voor onderzoeksdoeleinden: het is eenvoudig, goed gedocumenteerd, en het verkeer is leesbaar (geen encryptie op poort 6667), wat transparantie bevordert.

**Communicatieflow:**

```
Operator typt: !shell whoami
        │
        ▼
C2Server.py stuurt:  PRIVMSG #c2 :!shell whoami
        │
        ▼
InspIRCd distribueert het bericht naar alle kanaalleden
        │
        ▼
RAT.pyw (c2Agent) ontvangt:  :operator!... PRIVMSG #c2 :!shell whoami
        │
        ├─ Afzender == operator_nick?  Nee → negeren
        │
        Ja ▼
handle_c2_command("!shell whoami", ...)
        │
        ▼
subprocess.check_output("whoami", shell=True)
        │
        ▼
RAT.pyw stuurt:  PRIVMSG #c2 :insi\Administrator
        │
        ▼
C2Server.py print:  [bot_Administrator] insi\Administrator
```

**Beveiligingslaag:** de agent accepteert alleen berichten van de nick die in `.secret` als `operator_nick` staat. Berichten van andere IRC-gebruikers worden stilzwijgend genegeerd.

**PING/PONG:** IRC-servers sturen periodiek `PING` om te controleren of clients nog verbonden zijn. Beide scripts antwoorden automatisch met `PONG` zodat de verbinding niet verbroken wordt.

---

## 9. Veelvoorkomende fouten

| Foutmelding | Oorzaak | Oplossing |
|-------------|---------|-----------|
| `Conflict. The container name "/ircd" is already in use` | Container bestaat al | `sudo docker start ircd` |
| `Cannot connect to the Docker daemon` | Docker-service staat niet aan | `sudo systemctl start docker` |
| Agent verbindt niet met IRC | Verkeerd IP in `.secret`, of firewall blokkeert poort 6667 | IP controleren met `hostname -I`, firewall uitschakelen in de test-omgeving |
| `c2Agent` start niet / doet niets | `c2_server` of `operator_nick` ontbreekt in `.secret` | `.secret` aanvullen en scripts herstarten |
| Operator ziet geen antwoord van de bot | Bot gebruikt andere `operator_nick` dan verwacht | `!status` sturen en nick in `.secret` controleren |
