# Projectvoorstel Ethical Hacking — Ruben Van Mensel (s142486)

## Onderwerp

**Ontwikkeling van een Remote Access Trojan (RAT) met Command & Control infrastructuur**

## Beschrijving

Dit project onderzoekt hoe een aanvaller via een zelfgebouwde Remote Access Trojan (RAT) volledige controle kan krijgen over een doelsysteem. De focus ligt op het bouwen van een werkende Python-toolkit die de volledige Cyber Kill Chain doorloopt: van initiële infectie via een USB-drop (Rubber Ducky) tot persistente toegang, keylogging, screencapture en data-exfiltratie, aangestuurd vanuit een centrale Command & Control server.

De C2-server ondersteunt meerdere gelijktijdige sessies, waardoor het beheer van verschillende gecompromitteerde systemen vanuit één punt gedemonstreerd kan worden.

**Mogelijke uitbreiding:** indien de tijd het toelaat, wordt ook laterale verspreiding binnen een netwerk onderzocht (bv. via netwerkscanning en geautomatiseerde propagatie naar andere systemen).

## Relevantie

RATs vormen een van de meest voorkomende dreigingen in het huidige cybersecuritylandschap. Ze worden ingezet bij zowel gerichte aanvallen (APT's) als bij bredere campagnes. Door zelf een RAT te bouwen en te analyseren, ontstaat een diepgaand begrip van:

- Hoe post-exploitation in de praktijk werkt
- Welke persistence-technieken aanvallers gebruiken en hoe deze te detecteren zijn
- Hoe C2-communicatie functioneert en hoe blue teams deze kunnen identificeren
- De volledige Cyber Kill Chain vanuit het perspectief van de aanvaller

## Voorlopig plan

### Theoretisch onderzoek

- Analyse van bestaande RAT-families en hun technieken
- Werking van C2-architecturen (direct, beaconing, encrypted channels)
- Persistence-mechanismen op Windows (Task Scheduler, Registry Run keys)
- Detectie- en mitigatiemethoden vanuit blue team-perspectief

### Proof of Concept — Cyber Kill Chain mapping

| Fase                  | Invulling                                                           |
| --------------------- | ------------------------------------------------------------------- |
| Reconnaissance        | Netwerkscan om doelsystemen te identificeren                        |
| Weaponization         | RAT-agent bouwen in Python (keylogger, screencapture, remote shell) |
| Delivery              | USB-drop via Raspberry Pi als Rubber Ducky                          |
| Exploitation          | Payload-uitvoering op doelsysteem                                   |
| Installation          | Persistence via Task Scheduler en/of Registry                       |
| Command & Control     | Multi-session C2-server met sessie management                       |
| Actions on Objectives | Data-exfiltratie (keystrokes, screenshots) via e-mail of C2-kanaal  |

### Testomgeving

Alle testen worden uitgevoerd in geïsoleerde virtuele machines. Er wordt op geen enkel moment getest op systemen zonder expliciete toestemming.
