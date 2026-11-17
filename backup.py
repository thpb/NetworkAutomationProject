import yaml
from datetime import date
from getpass import getpass
from netmiko import ConnectHandler

with open("inventory.yaml") as file:
    data = yaml.safe_load(file)

devices = data["devices"]

username = input("Username: ")
password = getpass("Password: ")
today = date.today()

for device in devices:
    device_details = {
        "device_type": device["device_type"],
        "host": device["host"],
        "username": username,
        "password": password
    }
    try:    
        connection = ConnectHandler(**device_details)
        output = connection.send_command("show running-config")
        connection.disconnect()

        filename = f"backups/{device['name']}_{today}.txt"
        with open(filename, "w") as backup_file:
            backup_file.write(output)


        print(f"OK: Backup for {device['name']} -> {filename}")

    except Exception as error:
        print(f"ERROR: Backup for {device['name']} -> {error}")

print("Backup completed.")


