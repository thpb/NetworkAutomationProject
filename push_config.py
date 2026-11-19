import yaml
from pathlib import Path
from getpass import getpass
from jinja2 import Environment, FileSystemLoader
from netmiko import ConnectHandler

project_folder = Path(__file__).parent

with open(project_folder / "inventory.yaml") as f:
    data = yaml.safe_load(f)

devices = data["devices"]

env = Environment(loader=FileSystemLoader(project_folder / "templates"))
template = env.get_template("base.j2")

# 1. Preview what will be sent to every device
for device in devices:
    config = template.render(name=device["name"])
    print(f"===== {device['name']} =====")
    print(config)
    print()

# 2. Ask before changing anything
answer = input(f"Push this config to {len(devices)} devices? (yes/no): ")
if answer.lower() != "yes":
    print("Cancelled. Nothing was changed.")
    exit()

username = input("Username: ")
password = getpass("Password: ")

# 3. Push to each device
for device in devices:
    commands = template.render(name=device["name"]).splitlines()

    device_details = {
        "device_type": device["device_type"],
        "host": device["host"],
        "username": username,
        "password": password,
    }

    try:
        connection = ConnectHandler(**device_details)
        output = connection.send_config_set(commands)

        if "%" in output:
            print(f"ERROR    {device['name']}  (device rejected a command, not saved)")
            print(output)
        else:
            connection.save_config()
            print(f"OK       {device['name']}  (pushed and saved)")

        connection.disconnect()

    except Exception as error:
        print(f"FAILED   {device['name']}  (could not connect: {error})")

print("Done")