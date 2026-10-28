# Documentatie: RAT.pyw

**Project:** Ethical Hacking — Applied Security  
**Student:** Ruben Van Mensel (s142486)  
**Bestand:** `RAT(script)/RAT.pyw`  
**Doel:** academisch onderzoek naar offensieve beveiligingstechnieken in een geïsoleerde VM-omgeving

---

## Inhoudsopgave

1. [Wat is RAT.pyw?](#1-wat-is-ratpyw)
2. [Mapstructuur op het doelsysteem](#2-mapstructuur-op-het-doelsysteem)
3. [Configuratie](#3-configuratie)
4. [Opstartflow](#4-opstartflow)
5. [Thread-model](#5-thread-model)
6. [Functies](#6-functies)
   - [read_secrets](#read_secrets)
   - [createParamJson / loadParams](#createparamjson--loadparams)
   - [add_defender_exclusion](#add_defender_exclusion)
   - [runOnLogin](#runonlogin)
   - [makeStructure](#makestructure)
   - [copyScript](#copyscript)
   - [zipAllPrevSessions](#zipallprevsessions)
   - [sendSingleMail / mailQueue](#sendsinglemailmailqueue)
   - [screenLogger](#screenlogger)
   - [keyLogger](#keylogger)
   - [handle_c2_command](#handle_c2_command)
   - [c2Agent](#c2agent)
   - [killSwitch](#killswitch)
7. [C2-commando's](#7-c2-commandos)
8. [Dataflow: van toetsaanslag tot inbox](#8-dataflow-van-toetsaanslag-tot-inbox)
9. [Gebruikte technieken en MITRE ATT&CK mapping](#9-gebruikte-technieken-en-mitre-attck-mapping)
10. [Beperkingen (bewust transparant gehouden)](#10-beperkingen-bewust-transparant-gehouden)

---

## 1. Wat is RAT.pyw?

RAT.pyw is een Python-gebaseerde Remote Access Tool (RAT) / spyware-agent, geschreven als studieopdracht. Het script draait onzichtbaar op een Windows-doelsysteem (`.pyw` = Python zonder consolevenster), verzamelt gegevens en communiceert met een aanvallende machine via twee kanalen:

- **E-mail (SMTP):** logs worden verzonden als zip-bijlage naar een Gmail-adres.
- **IRC C2:** de agent verbindt met een IRC-server en voert commando's uit die de operator typt.

Het script is bewust transparent gehouden: geen obfuscatie, herkenbare mapnaam met studentnummer, leesbare code. Dit maakt het geschikt voor academische evaluatie.

---

## 2. Mapstructuur op het doelsysteem

Na het eerste uitvoeren maakt het script de volgende structuur aan op `C:\Windows\`:

```
C:\Windows\
└── s142486_WormFolder\          ← verborgen map (attrib +h)
    ├── RAT.pyw                  ← kopie van zichzelf
    ├── Params.json              ← configuratiebestand
    ├── error.log                ← fatale fouten (alleen bij crash)
    ├── Logs_DD.MM.YYYY_HH.MM.SS\   ← sessie-map (per opstart)
    │   ├── keylog.txt           ← alle toetsaanslagen
    │   └── ScreenLogs\
    │       └── Screenlog_HH.MM.SS_N.jpg
    └── Logs_DD.MM.YYYY_HH.MM.SS.zip  ← vorige sessies gezipt, klaar voor mail
```

De map is verborgen via `attrib +h`, waardoor hij niet zichtbaar is in de Verkenner zonder "verborgen bestanden tonen" aan te zetten.

---

## 3. Configuratie

### `.secret` (naast het script, nooit in git)

```
mail               = jouw@gmail.com
gmail_app_password = xxxx xxxx xxxx xxxx
c2_server          = 192.168.x.x
c2_port            = 6667
c2_channel         = #c2
operator_nick      = operator
```

Het script leest dit bestand met `read_secrets()`. Als een sleutel ontbreekt, wordt een lege string gebruikt — functies die de sleutel nodig hebben, vallen dan stil.

### `Params.json` (op het doelsysteem in de verborgen map)

```json
{
  "TimeBetweenEachScreenshot": 300,
  "LogKeys": true,
  "LogScreen": true,
  "Logging": true,
  "EnableKillSwitch": true,
  "persistentMailInterval": 120
}
```

| Parameter                   | Beschrijving                                            | Standaard   |
| --------------------------- | ------------------------------------------------------- | ----------- |
| `TimeBetweenEachScreenshot` | Seconden tussen twee screenshots                        | 300 (5 min) |
| `LogKeys`                   | Keylogger aan/uit                                       | `true`      |
| `LogScreen`                 | Schermopname aan/uit                                    | `true`      |
| `Logging`                   | Algemene schakelaar (overschrijft de twee bovenstaande) | `true`      |
| `EnableKillSwitch`          | Ctrl+Alt+K killswitch inschakelen                       | `true`      |
| `persistentMailInterval`    | Seconden tussen mailpogingen                            | 120 (2 min) |

---

## 4. Opstartflow

Wanneer het script gestart wordt (door de gebruiker, de dropper of de Task Scheduler), voert het `__main__` de volgende stappen uit **vóór** het starten van de threads:

```
1. add_defender_exclusion()   → vraag Windows Defender om de map te negeren
2. runOnLogin()               → registreer een Task Scheduler taak (persistent)
3. makeStructure()            → maak de verborgen mapstructuur aan
4. copyScript()               → kopieer zichzelf naar de verborgen map
5. createParamJson()          → maak Params.json aan (als die nog niet bestaat)
6. zipAllPrevSessions()       → zip alle sessie-mappen van vorige runs
```

Daarna starten 5 threads parallel:

```
KeyLogger      → toetsaanslagen loggen
ScreenLogger   → screenshots nemen
KillSwitch     → wacht op Ctrl+Alt+K
MailQueue      → zips periodiek mailen  (daemon)
C2Agent        → IRC verbinding         (daemon)
```

De hoofdthread wacht (`join`) tot KeyLogger, ScreenLogger en KillSwitch stoppen. Daemon-threads (MailQueue, C2Agent) worden automatisch afgesloten als het hoofdproces stopt.

---

## 5. Thread-model

```
Main Thread
│
├── KeyLogger ──────────────────────────── non-daemon, join()
│   Blokkeert op keyboard.read_event()
│   Schrijft naar keylog.txt via logLock
│
├── ScreenLogger ───────────────────────── non-daemon, join()
│   Slaapt exitEvent.wait(timeBetweenScreenshots)
│   Schrijft screenshot + markering via logLock
│
├── KillSwitch ─────────────────────────── non-daemon, join()
│   Blokkeert op keyboard.wait("ctrl+alt+k")
│   Roept exitEvent.set() aan → stopt alle threads
│
├── MailQueue ──────────────────────────── daemon
│   Slaapt exitEvent.wait(persistentMailInterval)
│   Stuurt alle .zip bestanden per mail
│
└── C2Agent ────────────────────────────── daemon
    TCP socket naar IRC-server
    Herverbindt automatisch na 30s bij verbrekende verbinding
    Roept handle_c2_command() aan bij berichten van operator_nick
```

**Gedeelde toestand en synchronisatie:**

| Gedeelde variabele                | Beschermd door          | Beschrijving                                    |
| --------------------------------- | ----------------------- | ----------------------------------------------- |
| `keylog.txt` (bestand)            | `logLock`               | Zowel KeyLogger als ScreenLogger schrijven erin |
| `logKeys`, `logScreen`, `logging` | geen lock nodig (GIL)   | Worden gelezen/geschreven als simpele booleans  |
| `screenshotCount`                 | `logLock` bij schrijven | Integer, gelezen door C2Agent via `!status`     |

---

## 6. Functies

### `read_secrets`

```python
secrets = read_secrets('.secret')
```

Leest een `key = value` bestand en geeft een dictionary terug. Geeft een lege dictionary terug als het bestand niet bestaat (geen crash). Hierdoor staan gevoelige gegevens (e-mailadres, wachtwoord, C2-server IP) nooit hard-coded in de broncode.

---

### `createParamJson` / `loadParams`

`createParamJson` schrijft `Params.json` met standaardwaarden als het bestand nog niet bestaat — dus alleen bij de allereerste run.

`loadParams` leest het bestand en geeft de waarden terug als tuple. Als het bestand niet bestaat (kan bij de eerste run vóór `createParamJson`), worden de standaardwaarden gebruikt. De waarden worden opgeslagen als module-level globals zodat alle threads er direct bij kunnen.

---

### `add_defender_exclusion`

```python
Add-MpPreference -ExclusionPath "C:\Windows\s142486_WormFolder"
```

Voert een PowerShell-commando uit dat de verborgen map toevoegt aan de Windows Defender-uitsluitingen. Hierdoor scant Defender de map niet meer en worden de logbestanden en het script zelf niet als bedreiging gemarkeerd.

> **Vereist:** het script moet met verhoogde rechten draaien (wat het doet via Task Scheduler met `/rl highest`).

Eventuele fouten worden stil genegeerd (`except CalledProcessError: pass`) — de rest van het script blijft functioneren.

---

### `runOnLogin`

Maakt een **Windows Task Scheduler taak** aan met `schtasks`:

```
schtasks /create /sc ONLOGON /tn s142486_Worm
         /tr "pythonw.exe" "C:\Windows\s142486_WormFolder\RAT.pyw"
         /rl highest /F
```

| Vlag          | Betekenis                                              |
| ------------- | ------------------------------------------------------ |
| `/sc ONLOGON` | Taak wordt uitgevoerd bij elke inlog                   |
| `/rl highest` | Hoogste rechten (UAC-niveau)                           |
| `/F`          | Overschrijf eventuele bestaande taak met dezelfde naam |

Daarna past het via PowerShell de taakinstellingen aan zodat de taak ook op batterijstroom start en niet gestopt wordt als de batterij laag is (`AllowStartIfOnBatteries`, `DontStopIfGoingOnBatteries`).

Het script gebruikt `pythonw.exe` in plaats van `python.exe` zodat er geen consolevenster verschijnt bij elke inlog.

---

### `makeStructure`

Maakt de mapstructuur aan op `C:\Windows\s142486_WormFolder\`:

1. Hoofdmap aanmaken (als die nog niet bestaat)
2. `attrib +h` → map verbergen
3. Sessie-map aanmaken: `Logs_DD.MM.YYYY_HH.MM.SS\`
4. Als `logScreen` aan staat: ook `ScreenLogs\` aanmaken

De sessie-mapnaam bevat de starttijd, zodat elke run zijn eigen map heeft en logs nooit overschreven worden.

---

### `copyScript`

```python
shutil.copy(__file__, hiddenFolderPath)
```

Kopieert het script van zijn huidige locatie naar de verborgen map. Dit zorgt ervoor dat het script blijft bestaan ook als het originele bestand (op een USB of downloadmap) verwijderd wordt. De kopie wordt alleen gemaakt als de doellocatie nog niet bestaat.

---

### `zipAllPrevSessions`

Bij elke opstart worden alle **vorige sessie-mappen** (mappen die beginnen met `Logs_`, maar niet de huidige sessie) gezipt en daarna verwijderd:

```
Logs_01.01.2025_10.00.00\  →  Logs_01.01.2025_10.00.00.zip
```

De zip wordt bewaard totdat `mailQueue` hem verstuurd heeft. Door de originele map te verwijderen wordt ruimte vrijgemaakt en blijft de bewijslast beperkt tot gecomprimeerde bestanden.

---

### `sendSingleMail` / `mailQueue`

**`sendSingleMail(zipFile)`** stuurt één zip-bestand als e-mailbijlage:

- Maakt een nieuw `MIMEMultipart`-bericht aan per mail (geen globale hergebruikte message-object).
- Onderwerp = de inlognaam van de gebruiker (`os.getlogin()`), zodat je in je inbox meteen ziet van welk systeem de mail komt.
- Verbindt via SMTP met STARTTLS (poort 587) naar `smtp.gmail.com`.
- Geeft `True` terug bij succes, `False` bij elke fout.

**`mailQueue()`** draait als achtergrond-thread en:

1. Scant de verborgen map elke `persistentMailInterval` seconden op `.zip`-bestanden.
2. Stuurt elk gevonden zip-bestand via `sendSingleMail`.
3. Verwijdert het bestand na een succesvolle verzending.
4. Als er geen zips zijn of de verzending mislukt (geen internet), wacht het en probeert het later opnieuw.

Dit is robuuster dan een eenmalige verzending: zelfs als het doelsysteem tijdelijk offline is, worden de logs alsnog verstuurd zodra de verbinding hersteld is.

---

### `screenLogger`

Maakt periodiek een screenshot en slaat die op als `.jpg`:

```
Screenlog_HH.MM.SS_N.jpg   (N = oplopend nummer)
```

Na elke screenshot wordt ook een markering in `keylog.txt` geschreven:

```
|== SCREENSHOT #3 | 14.32.05 ==|
```

Hierdoor kan je in de keylog zien wat de gebruiker aan het typen was op het moment van een screenshot, en vice versa.

**Live toggling:** de `if not (logScreen and logging)` check staat _binnen_ de while-lus. Als de C2-operator `!spy screen off` stuurt, pauzeert de thread na maximaal 5 seconden (de `exitEvent.wait(5)` in de pauze-branch). Schermopnames worden hervat zodra `!spy screen on` verstuurd wordt.

---

### `keyLogger`

Logt elke toetsaanslag naar `keylog.txt`. Speciale toetsen worden omgezet naar leesbare labels via `key_map`:

| Toets      | Gelogd als              |
| ---------- | ----------------------- |
| Spatiebalk | (spatie)                |
| Enter      | ` ENTER` + nieuwe regel |
| Backspace  | `*BACKSPACE*`           |
| Ctrl       | `*CTRL*`                |
| Pijltjes   | `*ARROW_UP*` etc.       |

Na elke Enter wordt de huidige tijd toegevoegd (`<<HH:MM>>`), waardoor je in de log kan zien wanneer de gebruiker iets bevestigd heeft.

**Live toggling:** `keyboard.read_event()` is een blokkerende aanroep — hij wacht tot er een toets ingedrukt wordt. Zodra een toets binnenkomt, wordt de vlag `logKeys and logging` gecheckt. Als die `False` is, wordt de event gewoon weggegooid en gaat de thread door met wachten. De thread stopt dus niet, maar logt niet meer. Dit maakt het mogelijk om keylogging live aan/uit te zetten via C2 zonder de thread te herstarten.

Beide threads (ScreenLogger en KeyLogger) schrijven naar hetzelfde `keylog.txt` bestand. Een `threading.Lock` (`logLock`) voorkomt dat ze tegelijk schrijven en het bestand corrumperen.

---

### `handle_c2_command`

Ontvangt een IRC-bericht van de operator en voert de bijbehorende actie uit. Antwoorden worden teruggestuurd naar het IRC-kanaal via `send_fn`. Lange antwoorden worden opgesplitst in stukken van 400 tekens (IRC heeft een regellengte-limiet van ~512 bytes).

Zie [sectie 7](#7-c2-commandos) voor een volledig overzicht van de commando's.

---

### `c2Agent`

De IRC C2-agent. Werking stap voor stap:

1. **Laad config** uit `.secret`: server IP, poort, kanaal, operator-nick. Als `c2_server` of `operator_nick` leeg is, stopt de functie meteen (C2 is optioneel).

2. **Verbind** met de IRC-server via een TCP socket (`socket.AF_INET`).

3. **Identificeer** met het IRC-protocol:

   ```
   NICK bot_<gebruikersnaam>
   USER bot_<gebruikersnaam> 0 * :bot_<gebruikersnaam>
   ```

4. **Wacht op welkomstbericht** (numerieke code `001`) en joint dan het kanaal:

   ```
   JOIN #c2
   ```

5. **Leeslus:** ontvangt berichten in een buffer, splitst op `\r\n`. Per regel:
   - `PING` → antwoord met `PONG` (verplicht om niet uitgegooid te worden)
   - `001` → join het kanaal (eenmalig)
   - `PRIVMSG` → parse de afzender. Alleen berichten van `operator_nick` worden verwerkt → doorsturen naar `handle_c2_command`

6. **Herverbinding:** als de socket verbroken wordt (netwerkfout, server herstart), wacht het 30 seconden en probeert het opnieuw. Dit gaat door totdat `exitEvent` gezet wordt (killswitch).

De socket heeft een timeout van 1 seconde zodat de lus `exitEvent.is_set()` kan controleren zonder voor altijd te blokkeren.

---

### `killSwitch`

```python
keyboard.wait("ctrl+alt+k")
exitEvent.set()
```

Blokkeert totdat de toetscombinatie `Ctrl+Alt+K` ingedrukt wordt. Dan zet het `exitEvent`, waardoor alle threads die op `exitEvent.wait()` staan direct wakker worden en netjes stoppen. De keylogger- en screenlogger-threads stoppen bij de volgende iteratie van hun lus.

Kan uitgeschakeld worden via `EnableKillSwitch: false` in `Params.json`.

---

## 7. C2-commando's

De operator typt deze commando's in `C2Server.py`. Ze worden via IRC naar de agent gestuurd.

| Commando                 | Beschrijving                            | Voorbeeld                                         |
| ------------------------ | --------------------------------------- | ------------------------------------------------- |
| `!shell <cmd>`           | Voer een shell-commando uit op het doel | `!shell whoami`                                   |
| `!download <pad>`        | Ontvang een bestand als base64          | `!download C:\Windows\System32\drivers\etc\hosts` |
| `!upload <pad> <base64>` | Schrijf een bestand naar het doel       | `!upload C:\temp\test.txt SGVsbG8=`               |
| `!spy keylog on\|off`    | Keylogger aan/uit                       | `!spy keylog off`                                 |
| `!spy screen on\|off`    | Schermopname aan/uit                    | `!spy screen on`                                  |
| `!spy mail on\|off`      | E-mail exfiltratie aan/uit              | `!spy mail off`                                   |
| `!status`                | Toon hostname en huidige instellingen   | `!status`                                         |
| `!help`                  | Toon commando-overzicht                 | `!help`                                           |

**Bestandsoverdracht (`!download`):**  
Bestanden worden als base64-string teruggestuurd met het formaat `FILE:<naam>:<base64>`. In `C2Server.py` kan je het ontvangen bestand opslaan door `save <bestandsnaam>` te typen.

**Live toggles:**  
`!spy screen` en `!spy mail` werken direct. `!spy keylog` werkt ook direct: de keylogger-thread gooit inkomende events weg totdat keylogging weer aangezet wordt.

---

## 8. Dataflow: van toetsaanslag tot inbox

```
[Gebruiker drukt toets]
        │
        ▼
keyboard.read_event()        ← KeyLogger thread
        │
        ├─ logKeys && logging?  Nee → event weggooien, wachten
        │
        Ja ▼
key_map opzoeken
        │
        ▼
keylog.txt (via logLock)     ← ook ScreenLogger schrijft hier markering

[Elke N seconden]
        │
        ▼
pyautogui.screenshot()       ← ScreenLogger thread
        │
        ▼
Screenlog_HH.MM.SS_N.jpg
        │
        ▼
markering in keylog.txt

[Bij volgende opstart]
        │
        ▼
zipAllPrevSessions()         ← comprimeert vorige sessie-map
        │
        ▼
Logs_DD.MM.YYYY_HH.MM.SS.zip

[Elke 2 minuten]
        │
        ▼
mailQueue()                  ← scant op .zip bestanden
        │
        ▼
sendSingleMail()             ← SMTP STARTTLS naar smtp.gmail.com:587
        │
        ▼
[Inbox van aanvaller]
```

---

## 9. Gebruikte technieken en MITRE ATT&CK mapping

| Techniek                       | Functie in RAT.pyw                 | MITRE ATT&CK                                       |
| ------------------------------ | ---------------------------------- | -------------------------------------------------- |
| Persistence via Task Scheduler | `runOnLogin()`                     | T1053.005 — Scheduled Task                         |
| Verborgen map                  | `makeStructure()` + `attrib +h`    | T1564.001 — Hidden Files                           |
| Zelf-kopiëren                  | `copyScript()`                     | T1105 — Ingress Tool Transfer                      |
| Keylogging                     | `keyLogger()`                      | T1056.001 — Keylogging                             |
| Schermopname                   | `screenLogger()`                   | T1113 — Screen Capture                             |
| Exfiltratie via e-mail         | `mailQueue()` / `sendSingleMail()` | T1048.003 — Exfiltration Over Unencrypted Protocol |
| AV-uitsluiting                 | `add_defender_exclusion()`         | T1562.001 — Disable or Modify Tools                |
| C2 via IRC                     | `c2Agent()`                        | T1071.003 — Application Layer Protocol: IRC        |
| Remote shell                   | `handle_c2_command()` → `!shell`   | T1059 — Command and Scripting Interpreter          |
| Bestandsoverdracht via C2      | `!download` / `!upload`            | T1105 — Ingress Tool Transfer                      |

---

## 10. Beperkingen (bewust transparant gehouden)

Dit script is opzettelijk **niet** geobfusceerd of geoptimaliseerd voor echte detectie-omzeiling. Concrete transparantiekeuzes:

- **Mapnaam bevat studentnummer** (`s142486_WormFolder`) — triviaal attribueerbaar.
- **Geen encryptie van logbestanden** — keylog.txt is leesbare plaintext.
- **SMTP-verkeer is zichtbaar** — elk netwerkmonitoringssysteem ziet `smtp.gmail.com:587`.
- **IRC-verbinding is onversleuteld** — poort 6667, geen TLS.
- **Credential-comment in code** — de comment op regel 42 legt expliciet uit waarom het e-mailadres zichtbaar is.
- **Geen process-hollowing of DLL-injectie** — het script draait als zichtbaar Python-proces in Taakbeheer.

Deze keuzes maken het script geschikt voor academische beoordeling en demonstratie, maar ongeschikt voor gebruik buiten een gecontroleerde testomgeving.
