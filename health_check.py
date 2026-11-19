import json
import yaml
from pathlib import Path
from getpass import getpass
from datetime import datetime
from netmiko import ConnectHandler


# ---------- HELPER ----------

def get_value(row, possible_keys):
    """Return the value of the first key that exists in this dictionary.

    Different versions of the TextFSM templates use different key names
    for the same column, so we try each likely name in turn.
    """
    for key in possible_keys:
        if key in row:
            return row[key]
    raise KeyError(f"none of {possible_keys} found; keys available: {list(row.keys())}")


# ---------- CHECK FUNCTIONS ----------

def check_interfaces(connection):
    """Return a list of problems found on this device's interfaces."""
    problems = []
    interfaces = connection.send_command("show ip interface brief", use_textfsm=True)

    for intf in interfaces:
        name = get_value(intf, ["interface", "intf"])
        ip = get_value(intf, ["ip_address", "ipaddr"])
        status = get_value(intf, ["status"])
        proto = get_value(intf, ["proto", "protocol"])

        if ip == "unassigned":
            continue
        if status != "up" or proto != "up":
            problems.append(f"{name} is {status}/{proto}")

    return problems


def check_ospf(connection):
    """Return a list of OSPF problems on this device."""
    problems = []
    neighbors = connection.send_command("show ip ospf neighbor", use_textfsm=True)

    if not isinstance(neighbors, list) or len(neighbors) == 0:
        problems.append("no OSPF neighbours")
        return problems

    for neighbor in neighbors:
        neighbor_id = get_value(neighbor, ["neighbor_id", "neighbor", "neighbour_id"])
        state = get_value(neighbor, ["state"])
        if not state.upper().startswith("FULL"):
            problems.append(f"OSPF neighbour {neighbor_id} is {state}")

    return problems


def check_bgp(connection):
    """Return a list of BGP problems on this device."""
    problems = []
    neighbors = connection.send_command("show ip bgp summary", use_textfsm=True)

    if not isinstance(neighbors, list) or len(neighbors) == 0:
        problems.append("no BGP neighbours")
        return problems

    for neighbor in neighbors:
        neighbor_ip = get_value(neighbor, ["bgp_neigh", "bgp_neighbor", "neighbor", "neighbor_ip"])
        state = get_value(neighbor, ["state_pfxrcd", "state_or_prefixes_received",
                                     "state_pfx_rcd", "state_prefix_received", "state"])
        # A number means Established (it's the count of prefixes received).
        # A word like Idle or Active means the session is down.
        if not str(state).isdigit():
            problems.append(f"BGP neighbour {neighbor_ip} is {state}")

    return problems


# ---------- MAIN PROGRAM ----------

project_folder = Path(__file__).parent
with open(project_folder / "inventory.yaml") as f:
    data = yaml.safe_load(f)

devices = data["devices"]

report_folder = project_folder / "reports"
report_folder.mkdir(exist_ok=True)

username = input("Username: ")
password = getpass("Password: ")

now = datetime.now()
report_lines = [f"Health check report - {now:%Y-%m-%d %H:%M}", ""]
summary = {"OK": 0, "PROBLEM": 0, "FAILED": 0}
results = {}

for device in devices:
    device_details = {
        "device_type": device["device_type"],
        "host": device["host"],
        "username": username,
        "password": password,
    }

    # Step 1: connect. If this fails, the device is unreachable.
    try:
        connection = ConnectHandler(**device_details)
    except Exception as error:
        summary["FAILED"] += 1
        report_lines.append(f"FAILED   {device['name']}  (could not connect: {error})")
        results[device["name"]] = {"status": "FAILED", "problems": [f"could not connect: {error}"]}
        continue

    # Step 2: run the checks. If this fails, the script hit a problem reading the data.
    try:
        problems = check_interfaces(connection)

        if "ospf" in device.get("protocols", []):
            problems += check_ospf(connection)

        if "bgp" in device.get("protocols", []):
            problems += check_bgp(connection)

    except Exception as error:
        problems = [f"check error: {error}"]

    finally:
        connection.disconnect()

    if problems:
        summary["PROBLEM"] += 1
        results[device["name"]] = {"status": "PROBLEM", "problems": problems}
        report_lines.append(f"PROBLEM  {device['name']}")
        for problem in problems:
            report_lines.append(f"         - {problem}")
    else:
        summary["OK"] += 1
        results[device["name"]] = {"status": "OK", "problems": []}
        report_lines.append(f"OK       {device['name']}")

report_lines.append("")
report_lines.append(
    f"Summary: {summary['OK']} OK, {summary['PROBLEM']} with problems, {summary['FAILED']} failed"
)

report_text = "\n".join(report_lines)
print(report_text)

report_file = report_folder / f"health_{now:%Y-%m-%d_%H%M}.txt"
with open(report_file, "w") as f:
    f.write(report_text)

print(f"\nReport saved to {report_file}")

# Save the results as JSON too, so other scripts (like report.py) can read them
results_file = report_folder / "health_latest.json"
results_file.write_text(json.dumps(results, indent=2))
print(f"Results saved to {results_file}")
