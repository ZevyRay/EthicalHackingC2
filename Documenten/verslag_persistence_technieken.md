# Persistence Technieken — Van User-Level tot Firmware

**Ruben Van Mensel (s142486) — Ethical Hacking Projectopdracht**

---

## Inleiding

Persistence is de fase in de Cyber Kill Chain (stap 5: Installation) waarin een aanvaller ervoor zorgt dat hun toegang tot het doelsysteem behouden blijft na een herstart, uitloggen of zelfs een herinstallatie van het besturingssysteem. De technieken variëren van eenvoudige gebruiker-niveau methoden tot extreem geavanceerde firmware-implants die enkel door nation-state actors worden ingezet.

Dit verslag geeft een overzicht van de verschillende niveaus van persistence, gerangschikt van minst naar meest geavanceerd, met voor elk niveau de werking, een voorbeeld uit de praktijk, en de bijbehorende detectie- en verdedigingsmethoden.

---

## 1. User-Level Persistence

### 1.1 Registry Run Keys

**Werking:** Windows voert bij elke login automatisch de programma's uit die staan in bepaalde registry-sleutels. De meest gebruikte is `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`. Een waarde toevoegen aan deze sleutel zorgt ervoor dat het opgegeven programma bij elke login wordt gestart.

**Voordeel voor de aanvaller:** Vereist geen beheerdersrechten. Elke gebruiker kan naar zijn eigen `HKCU`-sleutel schrijven.

**Nadeel:** Gemakkelijk te detecteren via Regedit of door het uitvoeren van `reg query`. Veel antivirusprogramma's monitoren deze sleutels actief.

**MITRE ATT&CK:** T1547.001 — Boot or Logon Autostart Execution: Registry Run Keys

### 1.2 Scheduled Tasks (Taakplanner)

**Werking:** Windows Taakplanner maakt het mogelijk om taken te registreren die op specifieke triggers worden uitgevoerd, zoals bij het aanmelden van een gebruiker (`ONLOGON`), bij het opstarten van het systeem, of op een vastgelegd tijdstip. Via het commando `schtasks /create` kan een taak worden aangemaakt die een willekeurig script of programma uitvoert.

**Voordeel voor de aanvaller:** Biedt meer controle dan Registry Run Keys. De taak kan worden ingesteld met de hoogste privileges (`/rl highest`) en kan worden geconfigureerd om ook op batterijvoeding te draaien. Daarnaast kan de trigger flexibel worden ingesteld (bij login, bij boot, op een schema).

**Nadeel:** Vereist beheerdersrechten voor systeembrede taken. Elke aanmaak wordt geregistreerd in de Windows Event Log (Event ID 4698), wat het detecteerbaar maakt voor blue teams.

**Toepassing in dit project:** De ontwikkelde malware maakt gebruik van een scheduled task met `ONLOGON`-trigger en hoogste privileges om zichzelf bij elke login uit te voeren via `pythonw.exe`, zodat er geen zichtbaar consolvenster verschijnt.

**MITRE ATT&CK:** T1053.005 — Scheduled Task/Job: Scheduled Task

### 1.3 Startup Folder

**Werking:** Bestanden of snelkoppelingen geplaatst in de map `C:\Users\<gebruiker>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup` worden automatisch uitgevoerd bij het aanmelden van die gebruiker. Er bestaat ook een systeembrede variant onder `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup`.

**Voordeel voor de aanvaller:** Zeer eenvoudig te implementeren — een simpele bestandskopie volstaat.

**Nadeel:** Direct zichtbaar voor de gebruiker via Taakbeheer (tabblad Opstarten) en Windows Instellingen. Dit is een van de eerste plaatsen die wordt gecontroleerd bij een forensisch onderzoek.

**MITRE ATT&CK:** T1547.001 — Boot or Logon Autostart Execution: Registry Run Keys / Startup Folder

---

## 2. Systeem-Level Persistence

### 2.1 Windows Services

**Werking:** Een kwaadaardig programma kan zichzelf registreren als een Windows-service. Services draaien op de achtergrond, vaak met SYSTEM-privileges, en worden automatisch gestart bij het opstarten van het besturingssysteem — nog vóór een gebruiker inlogt.

**Voordeel voor de aanvaller:** Draait met de hoogste systeemprivileges. Wordt gestart vóór de gebruikerslogin. Kan zich vermommen als een legitiem klinkende servicenaam.

**Nadeel:** Vereist beheerdersrechten om aan te maken. Zichtbaar in `services.msc` en via `sc query`.

**MITRE ATT&CK:** T1543.003 — Create or Modify System Process: Windows Service

### 2.2 DLL Hijacking / Side-Loading

**Werking:** Veel Windows-applicaties laden dynamische bibliotheken (DLL's) zonder het volledige pad te specificeren. Windows zoekt DLL's in een vooraf bepaalde volgorde: eerst de map van de applicatie, dan systeemmappen. Door een kwaadaardige DLL met de juiste naam in de applicatiemap te plaatsen, wordt deze geladen in plaats van de legitieme versie.

**Voordeel voor de aanvaller:** De kwaadaardige code draait binnen het proces van een legitiem programma, wat detectie bemoeilijkt. Geen afzonderlijk proces zichtbaar in Taakbeheer.

**Nadeel:** Vereist kennis van welke DLL's kwetsbaar zijn voor hijacking. Kan de hostapplicatie laten crashen als de DLL niet compatibel is.

**MITRE ATT&CK:** T1574.001 — Hijack Execution Flow: DLL Search Order Hijacking

### 2.3 WMI Event Subscriptions

**Werking:** Windows Management Instrumentation (WMI) biedt de mogelijkheid om permanente event-abonnementen aan te maken. Deze bestaan uit drie componenten: een Event Filter (de trigger), een Event Consumer (de actie), en een Binding (de koppeling). Hiermee kan een aanvaller code laten uitvoeren wanneer een specifieke systeemgebeurtenis plaatsvindt, zoals het opstarten van het systeem of het aanmaken van een proces.

**Voordeel voor de aanvaller:** Moeilijker te detecteren dan registry keys of scheduled tasks. Overleeft herstarten. Geen bestanden op schijf nodig voor de triggerlogica.

**Nadeel:** Complex om op te zetten. Kan worden gedetecteerd door WMI-specifieke monitoringtools.

**MITRE ATT&CK:** T1546.003 — Event Triggered Execution: Windows Management Instrumentation Event Subscription

---

## 3. Boot-Level Persistence

### 3.1 Bootkits (MBR/VBR)

**Werking:** Een bootkit infecteert de Master Boot Record (MBR) of Volume Boot Record (VBR) van de harde schijf. Omdat deze code wordt uitgevoerd vóór het besturingssysteem laadt, kan de bootkit het OS manipuleren terwijl het opstart, bijvoorbeeld door beveiligingsmechanismen uit te schakelen of rootkit-code in het geheugen te laden.

**Voorbeeld uit de praktijk:** TDL4 (ook bekend als TDSS) was een wijdverspreid bootkit dat de MBR overschreef om een rootkit te laden vóór Windows opstartte. Het was in staat om antivirussoftware te omzeilen omdat het actief was vóór de AV-software geladen werd.

**Overleeft:** Herinstallatie van het besturingssysteem (de MBR wordt niet standaard overschreven bij een herinstallatie).

**Verdediging:** Secure Boot (UEFI) voorkomt het laden van niet-ondertekende bootcode. Volledige disk wipe (niet alleen een formattering, maar het overschrijven van de MBR) verwijdert de infectie.

**MITRE ATT&CK:** T1542.003 — Pre-OS Boot: Bootkit

### 3.2 UEFI Firmware Implants

**Werking:** Moderne systemen gebruiken UEFI (Unified Extensible Firmware Interface) in plaats van het traditionele BIOS. De UEFI-firmware wordt opgeslagen op een SPI flash-chip op het moederbord. Een aanvaller die erin slaagt om een kwaadaardig UEFI-module te schrijven naar deze chip, heeft persistence die onafhankelijk is van de harde schijf. Bij elke opstart leest het systeem de UEFI-firmware, waardoor de kwaadaardige module wordt uitgevoerd nog vóór het besturingssysteem.

**Voorbeeld uit de praktijk:** LoJax, ontdekt in 2018 en toegeschreven aan de Russische APT28-groep (Fancy Bear), was het eerste gedocumenteerde geval van een UEFI-rootkit die in het wild werd aangetroffen. Het schreef een kwaadaardige module naar de SPI flash-chip, waardoor het persistent bleef zelfs na een volledige herinstallatie van het besturingssysteem en het vervangen van de harde schijf.

Een recenter voorbeeld is CosmicStrand (2022), dat werd aangetroffen in UEFI-firmware van bepaalde ASUS- en Gigabyte-moederborden. Dit implant manipuleerde de opstartketen om een kernel-level driver te laden in Windows.

**Overleeft:** Herinstallatie van het besturingssysteem, volledige disk wipe, en zelfs het vervangen van de harde schijf. Enkel het reflashen van de SPI-chip met schone firmware verwijdert de infectie.

**Verdediging:** Secure Boot met correct geconfigureerde sleutels, TPM-attestation (Trusted Platform Module) om de integriteit van de firmware te verifiëren, en firmware-updates van de fabrikant.

**MITRE ATT&CK:** T1542.001 — Pre-OS Boot: System Firmware

---

## 4. Hardware-Level Persistence

### 4.1 HDD/SSD Firmware

**Werking:** Harde schijven en SSD's bevatten hun eigen firmware — software die de controller van het opslagmedium aanstuurt. Een aanvaller die deze firmware kan herprogrammeren, kan kwaadaardige code verbergen op een niveau dat volledig onzichtbaar is voor het besturingssysteem. De gemanipuleerde firmware kan leesverzoeken onderscheppen, data verbergen, of extra code laden bij het opstarten.

**Voorbeeld uit de praktijk:** De Equation Group (gelinkt aan de NSA) ontwikkelde firmware-implants voor harde schijven van vrijwel alle grote fabrikanten (Western Digital, Seagate, Toshiba, Samsung). Deze implants konden een onzichtbare opslagruimte creëren op de schijf die niet toegankelijk was via normale middelen en die een volledige disk format overleefde.

**Overleeft:** Formattering, partitie-wipe, herinstallatie van het besturingssysteem. Enkel het vervangen van het opslagmedium of het herprogrammeren van de controller-firmware (indien mogelijk) verwijdert de infectie.

**MITRE ATT&CK:** T1542.002 — Pre-OS Boot: Component Firmware

### 4.2 Netwerk Interface Card (NIC) Firmware

**Werking:** Netwerkkaarten bevatten hun eigen processor en firmware. Aangepaste firmware op een NIC kan netwerkverkeer manipuleren, verborgen communicatiekanalen opzetten, of als een onafhankelijk platform functioneren dat volledig buiten het zicht van het besturingssysteem opereert.

**Voorbeeld uit de praktijk:** Beveiligingsonderzoeker Arrigo Triulzi demonstreerde in 2008 een proof of concept waarbij aangepaste firmware op een Intel-netwerkkaart werd gebruikt om een verborgen communicatiekanaal op te zetten. Hoewel dit een PoC was en geen in-the-wild malware, toonde het de haalbaarheid van deze aanvalsvector.

**Overleeft:** Alles behalve het fysiek vervangen van de netwerkkaart.

### 4.3 GPU Memory (Vluchtig)

**Werking:** Het videogeheugen (VRAM) van een grafische kaart kan worden gebruikt om kwaadaardige code op te slaan en uit te voeren. Aangezien antivirussoftware doorgaans geen GPU-geheugen scant, biedt dit een methode om detectie te omzeilen.

**Voorbeeld uit de praktijk:** Het proof-of-concept project "Jellyfish" demonstreerde een Linux-rootkit die in GPU-geheugen draaide via OpenCL. De code was onzichtbaar voor traditionele beveiligingstools die enkel het systeemgeheugen (RAM) scannen.

**Beperking:** VRAM is vluchtig geheugen — de code overleeft een volledige uitschakeling (power off) niet, maar blijft wel aanwezig bij een reboot. Dit maakt het geschikt als runtime-verbergingsmechanisme maar niet als langetermijn-persistence zonder aanvullende technieken.

---

## 5. Vergelijkend Overzicht

| Niveau | Techniek | Vereist admin | Overleeft herstart | Overleeft OS herinstallatie | Overleeft disk wipe | Detectie-moeilijkheid |
|--------|----------|---------------|--------------------|-----------------------------|---------------------|-----------------------|
| User | Registry Run Keys | Nee | Ja | Nee | Nee | Laag |
| User | Scheduled Tasks | Ja (systeem) | Ja | Nee | Nee | Laag |
| User | Startup Folder | Nee | Ja | Nee | Nee | Zeer laag |
| Systeem | Windows Services | Ja | Ja | Nee | Nee | Gemiddeld |
| Systeem | DLL Hijacking | Varieert | Ja | Mogelijk | Nee | Gemiddeld |
| Systeem | WMI Subscriptions | Ja | Ja | Nee | Nee | Hoog |
| Boot | Bootkit (MBR) | Ja | Ja | Ja | Nee | Hoog |
| Firmware | UEFI Implant | Ja + exploit | Ja | Ja | Ja | Zeer hoog |
| Hardware | HDD Firmware | Ja + exploit | Ja | Ja | Ja | Extreem hoog |

---

## 6. Toepassing in dit Project

De malware ontwikkeld in het kader van dit project maakt gebruik van Scheduled Tasks (user-level persistence). Deze keuze is gemaakt omdat:

1. Het voldoende is om het concept van persistence te demonstreren.
2. Het beheerdersrechten vereist die al beschikbaar zijn via de initiële infectie (Rubber Ducky met admin-payload).
3. Het realistisch is — een groot deel van de malware in het wild gebruikt dezelfde techniek.

Geavanceerde technieken zoals UEFI-implants of firmware-modificaties vallen buiten de scope van dit project, maar zijn theoretisch onderzocht om een volledig beeld te schetsen van het persistence-landschap.

---

## Bronnen

- MITRE ATT&CK Framework — Persistence Tactics (TA0003): https://attack.mitre.org/tactics/TA0003/
- ESET Research — LoJax: First UEFI rootkit found in the wild (2018)
- Kaspersky — Equation Group: The Crown Creator of Cyber-Espionage (2015)
- Kaspersky — CosmicStrand: the discovery of a sophisticated UEFI firmware rootkit (2022)
- Arrigo Triulzi — Project Maux: NIC firmware exploitation (2008)
- Jellyfish — GPU rootkit proof of concept: https://github.com/LittleHann/Jellyfish
