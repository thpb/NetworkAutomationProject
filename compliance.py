import json
import yaml
from pathlib import Path
from datetime import datetime

project_folder = Path(__file__).parent
backup_folder = project_folder / "backups"
report_folder = project_folder / "reports"
report_folder.mkdir(exist_ok=True)

# Lines that MUST be in every config
REQUIRED = {
    "SSH version 2 enabled": "ip ssh version 2",
    "VTY lines allow SSH only": "transport input ssh",
    "Login banner set": "banner motd",
    "Log timestamps enabled": "service timestamps log datetime msec",
    "Local log buffer enabled": "logging buffered",
}

# Lines that must NOT be in any config
FORBIDDEN = {
    "Telnet allowed on VTY lines": "transport input telnet",
    "All protocols allowed on VTY lines": "transport input all",
    "Plain-text enable password": "enable password",
}


def check_compliance(config):
    """Return a list of rules this config breaks."""
    failures = []

    for rule, line in REQUIRED.items():
        if line not in config:
            failures.append(f"missing: {rule}")

    for rule, line in FORBIDDEN.items():
        if line in config:
            failures.append(f"not allowed: {rule}")

    return failures


def latest_backup(device_name):
    """Return the newest backup file for this device, or None if there isn't one."""
    files = sorted(backup_folder.glob(f"{device_name}_*.txt"))
    if files:
        return files[-1]
    return None


with open(project_folder / "inventory.yaml") as f:
    devices = yaml.safe_load(f)["devices"]

now = datetime.now()
report_lines = [f"Compliance report - {now:%Y-%m-%d %H:%M}", ""]
summary = {"PASS": 0, "FAIL": 0, "NO BACKUP": 0}
results = {}

for device in devices:
    backup_file = latest_backup(device["name"])

    if backup_file is None:
        summary["NO BACKUP"] += 1
        results[device["name"]] = {"status": "NO BACKUP", "failures": [], "backup_file": None}
        report_lines.append(f"NO BACKUP  {device['name']}  (run backup.py first)")
        continue

    config = backup_file.read_text()
    failures = check_compliance(config)

    if failures:
        summary["FAIL"] += 1
        results[device["name"]] = {"status": "FAIL", "failures": failures, "backup_file": backup_file.name}
        report_lines.append(f"FAIL       {device['name']}  ({backup_file.name})")
        for failure in failures:
            report_lines.append(f"           - {failure}")
    else:
        summary["PASS"] += 1
        results[device["name"]] = {"status": "PASS", "failures": [], "backup_file": backup_file.name}
        report_lines.append(f"PASS       {device['name']}  ({backup_file.name})")

report_lines.append("")
report_lines.append(
    f"Summary: {summary['PASS']} pass, {summary['FAIL']} fail, {summary['NO BACKUP']} with no backup"
)

report_text = "\n".join(report_lines)
print(report_text)

report_file = report_folder / f"compliance_{now:%Y-%m-%d_%H%M}.txt"
report_file.write_text(report_text)
print(f"\nReport saved to {report_file}")

# Save the results as JSON too, so other scripts (like report.py) can read them
results_file = report_folder / "compliance_latest.json"
results_file.write_text(json.dumps(results, indent=2))
print(f"Results saved to {results_file}")
