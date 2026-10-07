# WMI query - werkt op elke Windows machine
import subprocess
result = subprocess.check_output(
    'wmic /namespace:\\\\root\\SecurityCenter2 path AntiVirusProduct get displayName',
    shell=True
).decode()  