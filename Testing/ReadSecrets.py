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

secrets = read_secrets('.secrets')
PASSWORD = secrets.get('gmail_app_password', '')