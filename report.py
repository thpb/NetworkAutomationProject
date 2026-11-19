
import csv
import json
import yaml
from pathlib import Path
from datetime import datetime
 
project_folder = Path(__file__).parent
backup_folder = project_folder / "backups"
report_folder = project_folder / "reports"
report_folder.mkdir(exist_ok=True)
 
 
def load_json(path):
    """Return the data in a JSON file, or an empty dictionary if the file doesn't exist."""
    if path.exists():
        return json.loads(path.read_text())
    return {}
 
 
def latest_backup(device_name):
    """Return the newest backup file for this device, or None if there isn't one."""
    files = sorted(backup_folder.glob(f"{device_name}_*.txt"))
    if files:
        return files[-1]
    return None
 
 
# ---------- LOAD EVERYTHING ----------
 
with open(project_folder / "inventory.yaml") as f:
    devices = yaml.safe_load(f)["devices"]
 
health = load_json(report_folder / "health_latest.json")
compliance = load_json(report_folder / "compliance_latest.json")
 
if not health:
    print("Note: no health results found. Run health_check.py first.")
if not compliance:
    print("Note: no compliance results found. Run compliance.py first.")
 
 
# ---------- BUILD ONE ROW PER DEVICE ----------
 
rows = []
 
for device in devices:
    name = device["name"]
 
    backup_file = latest_backup(name)
    if backup_file:
        backup_date = backup_file.stem.split("_")[-1]
    else:
        backup_date = "none"
 
    device_health = health.get(name, {})
    device_compliance = compliance.get(name, {})
 
    issues = device_health.get("problems", []) + device_compliance.get("failures", [])
 
    rows.append({
        "device": name,
        "site": device.get("site", ""),
        "role": device.get("role", ""),
        "last_backup": backup_date,
        "health": device_health.get("status", "not run"),
        "compliance": device_compliance.get("status", "not run"),
        "issues": "; ".join(issues),
    })
 
 
# ---------- PRINT A TABLE ----------
 
now = datetime.now()
print(f"\nNetwork report - {now:%Y-%m-%d %H:%M}\n")
print(f"{'Device':<10} {'Site':<12} {'Last backup':<12} {'Health':<9} {'Compliance':<11} Issues")
print("-" * 80)
 
for row in rows:
    print(f"{row['device']:<10} {row['site']:<12} {row['last_backup']:<12} "
          f"{row['health']:<9} {row['compliance']:<11} {row['issues']}")
 
healthy = sum(1 for row in rows if row["health"] == "OK" and row["compliance"] == "PASS")
print(f"\n{healthy} of {len(rows)} devices are healthy and compliant")
 
 
# ---------- SAVE AS CSV ----------
 
csv_file = report_folder / f"network_report_{now:%Y-%m-%d_%H%M}.csv"
 
with open(csv_file, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
 
print(f"\nCSV saved to {csv_file}")
 