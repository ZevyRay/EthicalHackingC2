# Cloaking & Evasion Technieken — Detectie Ontwijken

**Ruben Van Mensel (s142486) — Ethical Hacking Projectopdracht**

---

## Inleiding

Cloaking, ook wel evasion genoemd, omvat alle technieken die een aanvaller inzet om te voorkomen dat malware wordt gedetecteerd door beveiligingssoftware, systeembeheerders of de eindgebruiker. Waar persistence ervoor zorgt dat malware op het systeem *blijft*, zorgt cloaking ervoor dat het er niet *gevonden* wordt.

Dit verslag behandelt de verschillende niveaus van cloaking: van eenvoudige bestandsverberging tot geavanceerde technieken die door professionele malware-auteurs worden ingezet. Voor elk niveau wordt de werking, de effectiviteit, en de bijbehorende detectiemethoden besproken.

---

## 1. Bestandsniveau — Verbergen voor de Gebruiker

### 1.1 Hidden File Attributes

**Werking:** Windows kent het "hidden" attribuut toe aan bestanden en mappen via het commando `attrib +h`. Bestanden met dit attribuut worden niet weergegeven in Windows Explorer, tenzij de gebruiker expliciet de optie "Verborgen items weergeven" heeft ingeschakeld.

**Effectiviteit:** Zeer laag. Het attribuut is triviaal te omzeilen via de opdrachtprompt (`dir /a:h`) of door de Explorer-instelling aan te passen. Geen enkele beveiligingstool wordt hierdoor misleid.

**Toepassing in dit project:** De ontwikkelde malware gebruikt `attrib +h` om de opslagmap in `C:\Windows\` te verbergen voor de gemiddelde gebruiker. Dit is bewust gekozen als demonstratie van de techniek, met het besef dat het geen bescherming biedt tegen forensisch onderzoek.

**MITRE ATT&CK:** T1564.001 — Hide Artifacts: Hidden Files and Directories

### 1.2 Bestandsnaamgeving en Locatiekeuze

**Werking:** Malware kiest vaak bestandsnamen en locaties die lijken op legitieme systeembestanden of -processen. Voorbeelden zijn het plaatsen van bestanden in `C:\Windows\System32\` met namen als `svchost.exe`, `csrss.exe` of `conhost.exe` — namen die ook door het besturingssysteem zelf worden gebruikt.

**Effectiviteit:** Gemiddeld. Een onervaren gebruiker of systeembeheerder kan de kwaadaardige bestanden over het hoofd zien. Beveiligingstools kijken echter naar meer dan alleen de naam: ze controleren digitale handtekeningen, bestandslocaties, en of het bestand overeenkomt met bekende hashes.

**MITRE ATT&CK:** T1036.005 — Masquerading: Match Legitimate Name or Location

### 1.3 Alternate Data Streams (ADS)

**Werking:** Het NTFS-bestandssysteem ondersteunt Alternate Data Streams: extra datastromen die aan een bestand kunnen worden gekoppeld zonder dat de bestandsgrootte in Explorer verandert. Een aanvaller kan kwaadaardige code opslaan in een ADS van een legitiem bestand. Het commando `notepad.exe bestand.txt:hidden.exe` opent bijvoorbeeld een verborgen datastroom.

**Effectiviteit:** Gemiddeld tot hoog. ADS zijn onzichtbaar in Windows Explorer en worden niet weergegeven bij een standaard `dir`-commando. Het commando `dir /r` toont ze wel, en moderne antivirussoftware scant ADS actief.

**MITRE ATT&CK:** T1564.004 — Hide Artifacts: NTFS File Attributes

---

## 2. Procesniveau — Verbergen voor Taakbeheer en Monitoring

### 2.1 Windowless Execution (.pyw / pythonw.exe)

**Werking:** Python-scripts die worden uitgevoerd via `pythonw.exe` in plaats van `python.exe` (of met de extensie `.pyw`) draaien zonder een zichtbaar consolvenster. Het proces is nog steeds zichtbaar in Taakbeheer, maar er verschijnt geen venster op het scherm dat de aandacht van de gebruiker trekt.

**Effectiviteit:** Laag tot gemiddeld. Het voorkomt dat de gebruiker een verdacht consolvenster opmerkt, maar het proces `pythonw.exe` is zichtbaar in Taakbeheer. Een oplettende gebruiker of systeembeheerder kan dit opmerken.

**Toepassing in dit project:** De malware wordt uitgevoerd via `pythonw.exe` door het bestand de `.pyw`-extensie te geven en in de Task Scheduler te verwijzen naar `pythonw.exe`.

### 2.2 Process Injection

**Werking:** In plaats van een eigen proces te starten, kan malware zijn code injecteren in een reeds draaiend, legitiem proces. Veelgebruikte doelwitten zijn `explorer.exe`, `svchost.exe` of `notepad.exe`. Technieken hiervoor zijn onder andere DLL injection (via `CreateRemoteThread` en `LoadLibrary`), process hollowing (een legitiem proces starten in suspended state, het geheugen vervangen door kwaadaardige code, en het hervatten), en APC injection (Asynchronous Procedure Call).

**Effectiviteit:** Hoog. Geen afzonderlijk verdacht proces zichtbaar. De kwaadaardige code erft de reputatie en privileges van het hostproces. Detectie vereist geavanceerde EDR-oplossingen die API-aanroepen monitoren.

**MITRE ATT&CK:** T1055 — Process Injection (met subtechnieken .001 t/m .015)

### 2.3 Living off the Land (LOLBins)

**Werking:** In plaats van eigen tools mee te brengen, maakt de aanvaller gebruik van programma's die standaard op het systeem aanwezig zijn. Deze worden "Living off the Land Binaries" (LOLBins) genoemd. Voorbeelden op Windows:

| LOLBin | Legitiem gebruik | Misbruik door aanvallers |
|--------|-----------------|--------------------------|
| `certutil.exe` | Certificaatbeheer | Bestanden downloaden, base64 decode |
| `mshta.exe` | HTML-applicaties uitvoeren | Scripts uitvoeren vanuit een URL |
| `regsvr32.exe` | DLL's registreren | Scriptlets laden vanuit extern |
| `bitsadmin.exe` | Achtergronddownloads | Bestanden downloaden zonder browser |
| `powershell.exe` | Systeembeheer | In-memory code uitvoeren |
| `wmic.exe` | Systeeminformatie | Processen starten, laterale beweging |

**Effectiviteit:** Hoog. Omdat deze programma's legitiem zijn en door Microsoft zijn ondertekend, worden ze niet geblokkeerd door application whitelisting. Het onderscheid tussen legitiem en kwaadaardig gebruik vereist gedragsanalyse.

**MITRE ATT&CK:** T1218 — System Binary Proxy Execution

---

## 3. Netwerkniveau — Communicatie Verbergen

### 3.1 Encrypted C2 Channels

**Werking:** Command & Control-communicatie wordt versleuteld met TLS/SSL, waardoor de inhoud van het verkeer onzichtbaar is voor netwerk-gebaseerde detectiesystemen. De malware maakt een HTTPS-verbinding naar de C2-server, wat er voor netwerkmonitoring uitziet als normaal webverkeer.

**Effectiviteit:** Hoog. Zonder TLS-inspectie (SSL interception) kan een netwerk-IDS de inhoud van de communicatie niet analyseren. De meeste organisaties inspecteren niet al het HTTPS-verkeer.

**Toepassing in dit project:** De huidige versie gebruikt SMTP (e-mail) voor data-exfiltratie, wat eenvoudig detecteerbaar is door uitgaand verkeer naar `smtp.gmail.com` op poort 587 te monitoren. Een overstap naar HTTPS-gebaseerde C2 zou de detectie aanzienlijk bemoeilijken.

**MITRE ATT&CK:** T1573 — Encrypted Channel

### 3.2 Domain Fronting

**Werking:** De malware stuurt verkeer naar een legitiem domein (bijvoorbeeld een CDN zoals cloudfront.net of azure.com), maar specificeert in de HTTP Host-header een ander, door de aanvaller gecontroleerd domein. Het CDN routeert het verkeer naar het juiste backend-domein. Voor een netwerk-inspecteur lijkt het verkeer gericht aan een vertrouwd domein.

**Effectiviteit:** Zeer hoog. Het verkeer lijkt afkomstig van of gericht aan een groot, vertrouwd platform. Blokkeren van het domein zou ook het legitieme platform blokkeren. Steeds meer CDN-providers verbieden deze techniek echter.

**MITRE ATT&CK:** T1090.004 — Proxy: Domain Fronting

### 3.3 DNS Tunneling

**Werking:** Data wordt gecodeerd in DNS-queries en -responses. De aanvaller controleert een autoritatieve DNS-server voor een domein. De malware stuurt DNS-queries met gecodeerde data als subdomeinen (bijv. `dGVzdGRhdGE.attacker-domain.com`), en ontvangt antwoorden met gecodeerde instructies in de DNS-response records.

**Effectiviteit:** Hoog. DNS-verkeer wordt zelden geblokkeerd omdat het essentieel is voor de werking van het netwerk. Veel organisaties monitoren de inhoud van DNS-queries niet actief. Detectie vereist het analyseren van afwijkende patronen in DNS-verkeer (ongewoon lange subdomeinen, hoog volume naar één domein).

**MITRE ATT&CK:** T1071.004 — Application Layer Protocol: DNS

### 3.4 Beaconing via Legitieme Diensten

**Werking:** In plaats van een eigen C2-server te gebruiken, misbruikt de malware legitieme diensten als communicatiekanaal. Voorbeelden zijn:

| Dienst | Methode |
|--------|---------|
| Google Sheets | Commando's lezen uit cellen, output terugschrijven |
| Telegram | Bot API gebruiken voor bidirectionele communicatie |
| Twitter/X | Commando's verbergen in tweets of direct messages |
| Slack | Webhook of Bot API als C2-kanaal |
| GitHub | Commando's in commits of issues, output in repository |
| Dropbox | Bestanden uploaden/downloaden als C2-communicatie |

**Effectiviteit:** Zeer hoog. Het verkeer gaat naar vertrouwde domeinen (google.com, telegram.org, github.com) via HTTPS. Blokkeren is vaak niet mogelijk zonder bedrijfsprocessen te verstoren.

**MITRE ATT&CK:** T1102 — Web Service

---

## 4. Code-niveau — Analyse Bemoeilijken

### 4.1 Obfuscation (Verduistering)

**Werking:** De broncode of bytecode van de malware wordt opzettelijk onleesbaar gemaakt om reverse engineering te bemoeilijken. Technieken omvatten het hernoemen van variabelen en functies naar willekeurige tekens, het encrypten van strings die pas at runtime worden ontsleuteld, het toevoegen van dode code die nooit wordt uitgevoerd, en het opsplitsen van logica over meerdere lagen van functieaanroepen.

**Effectiviteit:** Gemiddeld. Vertraagt handmatige analyse maar stopt een ervaren reverse engineer niet. Automatische deobfuscation-tools bestaan voor de meeste technieken.

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information

### 4.2 Polymorphism

**Werking:** Elke keer dat de malware zich kopieert of verspreidt, genereert het een structureel andere versie van zichzelf. De functionaliteit blijft identiek, maar de bytecode, variabelenamen, en encryptiesleutels veranderen. Dit betekent dat geen twee kopieën dezelfde hash hebben.

**Effectiviteit:** Hoog tegen signature-based detectie. Antivirussoftware die vertrouwt op het herkennen van bekende hashes of byte-patronen kan de malware niet identificeren. Heuristische en gedragsgebaseerde detectie is nodig.

**MITRE ATT&CK:** T1027.001 — Obfuscated Files or Information: Binary Padding (gerelateerd)

### 4.3 Packing

**Werking:** De originele malware wordt gecomprimeerd en/of versleuteld in een "packed" formaat. Een kleine "unpacker" stub wordt toegevoegd die bij uitvoering de originele code in het geheugen uitpakt en uitvoert. Bekende packers zijn UPX, Themida, en VMProtect.

**Effectiviteit:** Gemiddeld tot hoog. De packed versie heeft een andere signature dan de originele malware. Veel packers zijn echter bekend bij AV-leveranciers, en het gebruik van een packer is op zichzelf al een verdacht signaal (heuristic flag).

**MITRE ATT&CK:** T1027.002 — Obfuscated Files or Information: Software Packing

### 4.4 In-Memory Execution (Fileless Malware)

**Werking:** De malware schrijft zichzelf nooit naar de harde schijf. De volledige payload wordt in het geheugen geladen en uitgevoerd, vaak via PowerShell, WMI, of macro's in Office-documenten. Omdat er geen bestand op schijf staat, is er niets voor traditionele antivirussoftware om te scannen.

**Effectiviteit:** Zeer hoog tegen traditionele AV. Overleeft geen herstart (tenzij gecombineerd met een persistence-mechanisme dat de in-memory payload opnieuw laadt). Detectie vereist memory scanning, gedragsanalyse, of AMSI (Antimalware Scan Interface) in het geval van PowerShell.

**MITRE ATT&CK:** T1059.001 — Command and Scripting Interpreter: PowerShell (vaak gebruikt voor fileless execution)

---

## 5. Antivirus Evasion — Specifieke Technieken

### 5.1 AV-Detectie en Identificatie

**Werking:** Voordat malware evasion-technieken toepast, identificeert het eerst welke beveiligingssoftware op het systeem draait. Op Windows kan dit via een WMI-query naar de `SecurityCenter2`-namespace:

```
wmic /namespace:\\root\SecurityCenter2 path AntiVirusProduct get displayName
```

Op basis van het resultaat kan de malware specifieke evasion-strategieën kiezen of besluiten om bepaalde acties niet uit te voeren als een bekende EDR-oplossing wordt gedetecteerd.

**MITRE ATT&CK:** T1518.001 — Software Discovery: Security Software Discovery

### 5.2 Defender Exclusions

**Werking:** Windows Defender biedt de mogelijkheid om mappen, bestanden of processen uit te sluiten van scanning. Via PowerShell kan dit worden ingesteld met het commando `Add-MpPreference -ExclusionPath`. Als een aanvaller beheerdersrechten heeft, kan deze een exclusie toevoegen voor de map waarin de malware zich bevindt.

**Effectiviteit:** Hoog tegen Defender, maar irrelevant tegen andere AV-producten. De actie wordt gelogd in de Windows Event Log (Event ID 5007) en is een bekende indicator of compromise (IOC). Tamper Protection, indien ingeschakeld, voorkomt dat exclusies programmatisch worden toegevoegd.

**Toepassing in dit project:** De malware voegt een Defender-exclusie toe voor de verborgen opslagmap. Dit wordt uitgevoerd binnen een try/except-blok zodat het script niet crasht wanneer Tamper Protection actief is.

**MITRE ATT&CK:** T1562.001 — Impair Defenses: Disable or Modify Tools

### 5.3 Timestomping

**Werking:** De aanvaller wijzigt de tijdstempels van kwaadaardige bestanden (creation time, modification time, access time) zodat ze overeenkomen met die van legitieme systeembestanden in dezelfde map. Dit bemoeilijkt tijdlijnanalyse tijdens forensisch onderzoek.

**Effectiviteit:** Gemiddeld. De standaard tijdstempels in de $STANDARD_INFORMATION-attribute van NTFS zijn eenvoudig te wijzigen, maar de $FILE_NAME-attribute (zichtbaar via forensische tools) wordt door het bestandssysteem beheerd en is moeilijker te manipuleren. Discrepanties tussen deze twee attributen zijn een indicator van timestomping.

**MITRE ATT&CK:** T1070.006 — Indicator Removal: Timestomp

---

## 6. Vergelijkend Overzicht

| Techniek | Niveau | Effectiviteit vs. gebruiker | Effectiviteit vs. AV/EDR | Complexiteit |
|----------|--------|----------------------------|--------------------------|-------------|
| Hidden attributes | Bestand | Gemiddeld | Geen | Zeer laag |
| Naamgeving/locatie | Bestand | Gemiddeld | Laag | Laag |
| ADS | Bestand | Hoog | Gemiddeld | Laag |
| Windowless (.pyw) | Proces | Gemiddeld | Geen | Zeer laag |
| Process injection | Proces | Hoog | Hoog | Hoog |
| LOLBins | Proces | Hoog | Hoog | Gemiddeld |
| Encrypted C2 | Netwerk | N.v.t. | Hoog | Gemiddeld |
| Domain fronting | Netwerk | N.v.t. | Zeer hoog | Hoog |
| DNS tunneling | Netwerk | N.v.t. | Hoog | Gemiddeld |
| Obfuscation | Code | N.v.t. | Gemiddeld | Laag |
| Polymorphism | Code | N.v.t. | Hoog | Hoog |
| In-memory | Code | Hoog | Zeer hoog | Hoog |
| Defender exclusion | AV-specifiek | N.v.t. | Hoog (Defender) | Zeer laag |

---

## 7. Toepassing in dit Project

De ontwikkelde malware past de volgende cloaking-technieken toe:

| Techniek | Implementatie |
|----------|---------------|
| Hidden file attributes | `attrib +h` op de opslagmap |
| Locatiekeuze | Opslag in `C:\Windows\`, een map die gebruikers zelden handmatig doorbladeren |
| Windowless execution | Uitvoering via `pythonw.exe` / `.pyw`-extensie |
| AV exclusion | Defender-exclusie toevoegen voor de opslagmap |

Deze technieken zijn bewust gekozen op basis van eenvoud en demonstreerbaarheid. Ze illustreren de basisbeginselen van evasion, maar bieden geen bescherming tegen een forensisch onderzoek of een geavanceerde EDR-oplossing. Dit is een bewuste keuze: het doel van dit project is het begrijpen van de technieken, niet het bouwen van ondetecteerbare malware.

Voor een volledige evasion-strategie in een professionele pentest zouden technieken als in-memory execution, process injection en encrypted C2-kanalen worden gecombineerd. Dit valt buiten de scope van dit project maar is relevant voor het theoretische begrip van het dreigingslandschap.

---

## Bronnen

- MITRE ATT&CK Framework — Defense Evasion Tactics (TA0005): https://attack.mitre.org/tactics/TA0005/
- LOLBAS Project — Living Off The Land Binaries, Scripts and Libraries: https://lolbas-project.github.io/
- Microsoft Documentation — Windows Defender Exclusions
- Microsoft Documentation — Alternate Data Streams (NTFS)
- Elastic Security Labs — Fileless Malware Detection
