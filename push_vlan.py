import yaml
from pathlib import Path
from getpass import getpass
from jinja2 import Environment, FileSystemLoader
from netmiko import ConnectHandler

project_folder = Path(__file__).parent

with open(project_folder / "inventory.yaml") as f:
    devices = yaml.safe_load(f)["devices"]

with open(project_folder / "vlans.yaml") as f:
    vlans = yaml.safe_load(f)["vlans"]

switches = [device for device in devices if device["role"] == "switch"]

env = Environment(loader=FileSystemLoader(project_folder / "templates"),
                  trim_blocks=True, lstrip_blocks=True)
template = env.get_template("vlans.j2")

# Preview
for switch in switches:
    print(f"===== {switch['name']} =====")
    print(template.render(vlans=vlans, trunk_interface=switch["trunk_interface"]))
    print()

answer = input(f"Push to {len(switches)} switches? (yes/no): ")
if answer.lower() != "yes":
    print("Cancelled. Nothing was changed.")
    exit()

username = input("Username: ")
password = getpass("Password: ")

for switch in switches:
    config = template.render(vlans=vlans, trunk_interface=switch["trunk_interface"])
    commands = [line for line in config.splitlines() if line.strip()]

    device_details = {
        "device_type": switch["device_type"],
        "host": switch["host"],
        "username": username,
        "password": password,
    }

    try:
        connection = ConnectHandler(**device_details)
        output = connection.send_config_set(commands)

        if "%" in output:
            print(f"ERROR    {switch['name']}  (not saved)")
            print(output)
        else:
            connection.save_config()
            print(f"OK       {switch['name']}  (VLANs added and saved)")

        connection.disconnect()

    except Exception as error:
        print(f"FAILED   {switch['name']}  (could not connect: {error})")