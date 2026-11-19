# Network Automation Project

A two-site small business network built in **Cisco Modeling Labs**, then automated with **Python**. The network was designed and configured by hand first, and a set of scripts now backs it up, checks its health, pushes configuration from templates, audits it against security rules, and produces a combined report.

## Contents

- [Scenario](#scenario)
- [Topology](#topology)
- [Network design](#network-design)
- [Automation scripts](#automation-scripts)
- [Project structure](#project-structure)
- [Setup](#setup)
- [Usage](#usage)
- [Example output](#example-output)
- [What I learned](#what-i-learned)
- [Next steps](#next-steps)

## Scenario

A small company has a **head office** and a **branch office**. The business requirements:

- Staff, Guest and Server networks kept separate with VLANs
- Guests can reach the internet but not staff or servers
- Head office and branch share routes with OSPF
- Internet access through an ISP, using eBGP and NAT
- Devices managed securely over SSH only
- Configurations backed up, and problems reported automatically

## Topology

<!-- Add a screenshot of the CML lab here, e.g. images/topology.png -->
<!-- ![Lab topology](images/topology.png) -->

```
                    [ISP-RT]  AS 65100
                       |      Loopback 198.51.100.1 ("the internet")
                       | eBGP
                       |
   [HQ-RT] AS 65001 ---+--- OSPF --- [Branch-RT]
       |                                  |
   [HQ-SW]                           [Branch-SW]
   VLAN 10 Staff                     VLAN 10 Staff
   VLAN 20 Guest                     VLAN 20 Guest
   VLAN 30 Servers
```

All five devices also connect to a separate **out-of-band management network** (192.168.218.0/24) through an unmanaged switch and CML's external connector, which is how the Python scripts reach them over SSH.

## Network design

### Devices

| Device | Role | Platform | Management IP |
| --- | --- | --- | --- |
| HQ-RT | Head office router: OSPF, eBGP, NAT, ACLs | Cisco IOL | 192.168.218.11 |
| Branch-RT | Branch router: OSPF | Cisco IOL | 192.168.218.12 |
| ISP-RT | Simulated ISP: eBGP | Cisco IOL | 192.168.218.13 |
| HQ-SW | Head office switch | Cisco IOL-L2 | 192.168.218.21 |
| Branch-SW | Branch switch | Cisco IOL-L2 | 192.168.218.22 |

### IP addressing

| Network | Subnet | Gateway |
| --- | --- | --- |
| HQ Staff (VLAN 10) | 10.0.10.0/26 | 10.0.10.1 |
| HQ Guest (VLAN 20) | 10.0.20.0/27 | 10.0.20.1 |
| HQ Servers (VLAN 30) | 10.0.30.0/28 | 10.0.30.1 |
| Branch Staff (VLAN 10) | 10.0.10.64/27 | 10.0.10.65 |
| Branch Guest (VLAN 20) | 10.0.20.32/28 | 10.0.20.33 |
| HQ to Branch link | 10.0.0.0/30 | — |
| HQ to ISP link | 203.0.113.0/30 | — |
| Router loopbacks | 10.0.255.1, 10.0.255.2 (/32) | — |
| Management | 192.168.218.0/24 | — |

### Features configured

- **VLANs and trunks** on both switches, with **router-on-a-stick** gateways
- **OSPF** (area 0) between head office and branch, loopbacks as router IDs
- **eBGP** between HQ (AS 65001) and the ISP (AS 65100); the ISP sends a default route, which HQ shares with the branch through OSPF
- **PAT** on the HQ router for internet access from every VLAN
- **Extended ACL** that blocks Guest from Staff and Servers while still allowing the internet
- **SSH v2 only** on all devices, with Telnet disabled

## Automation scripts

| Script | What it does |
| --- | --- |
| `inventory.yaml` | Single source of truth: every device's name, IP, role, site and protocols |
| `backup.py` | Logs in to every device and saves its running config to `backups/<device>_<date>.txt` |
| `health_check.py` | Checks interfaces are up, OSPF neighbours are FULL and BGP sessions are Established, using TextFSM to parse output; saves a timestamped report and JSON results |
| `push_config.py` | Renders a Jinja2 template (login banner, log timestamps, log buffer) for each device, previews it, asks for confirmation, pushes it, and saves only if the device accepted every command |
| `push_vlans.py` | Adds VLANs from `vlans.yaml` to both switches and their trunks, using a looping Jinja2 template |
| `compliance.py` | Audits each device's latest backup against security rules (SSH v2, SSH-only VTY lines, banner, logging; no Telnet or plain-text enable password) |
| `report.py` | Combines backup, health and compliance results into one table and a CSV file |

Design choices:

- **No passwords in the repository.** Scripts ask for credentials at run time with `getpass`.
- **Checks run only where they apply.** Each device's `protocols` list in the inventory decides whether OSPF and BGP are checked.
- **One failure doesn't stop the run.** Every device is wrapped in `try/except`, so an unreachable device is reported and the rest continue.
- **Changes are previewed and confirmed** before anything is pushed, and saved only if no errors were returned.

## Project structure

```
NetworkAutomationProject/
├── inventory.yaml        # device inventory
├── vlans.yaml            # VLANs to add to the switches
├── templates/
│   ├── base.j2           # baseline settings for every device
│   └── vlans.j2          # VLAN and trunk template
├── backup.py
├── health_check.py
├── push_config.py
├── push_vlans.py
├── compliance.py
├── report.py
├── requirements.txt
└── .gitignore            # excludes venv, backups and reports
```

## Setup

Requirements: Python 3, a running lab, and SSH access to each device's management IP.

```
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Update `inventory.yaml` with your own device names and management IPs.

## Usage

Run the reporting scripts in this order, since each one uses what the one before it saved:

```
python backup.py          # 1. back up every config
python health_check.py    # 2. check interfaces, OSPF and BGP
python compliance.py      # 3. audit the backups against the rules
python report.py          # 4. combine everything into one report
```

To make changes:

```
python push_config.py     # push the baseline template to every device
python push_vlans.py      # add the VLANs in vlans.yaml to both switches
```

## Example output

```
Network report - 2026-11-19 18:45

Device     Site         Last backup  Health    Compliance  Issues
--------------------------------------------------------------------------------
HQ-RT      head-office  2026-11-19   OK        PASS
Branch-RT  branch       2026-11-19   OK        PASS
ISP-RT     isp          2026-11-19   OK        PASS
HQ-SW      head-office  2026-11-19   OK        PASS
Branch-SW  branch       2026-11-19   OK        PASS

5 of 5 devices are healthy and compliant
```

## What I learned

- Designing an IP plan and subnetting every VLAN and link before configuring anything
- Configuring and verifying VLANs, router-on-a-stick, OSPF, eBGP, NAT and ACLs on Cisco IOS
- Connecting a simulated lab to a laptop with an out-of-band management network
- Using Python data structures (lists of dictionaries, nested data) to drive automation from an inventory
- Netmiko for SSH automation, TextFSM for parsing CLI output, Jinja2 for templating, and JSON and CSV for sharing results
- Troubleshooting real problems, including:
  - a NAT rule pointing at the wrong interface, found by reading `show ip nat translations`
  - host virtualisation conflicts (Windows Credential Guard) blocking the lab
  - TextFSM key names that differed from what I expected, fixed by inspecting the parsed data

## Next steps

- Combine the scripts into a safe change pipeline: backup, pre-check, deploy, post-check, and automatic rollback
- Replace the HQ–Branch link with a site-to-site IPsec VPN over the "internet"
- Connect the network to Microsoft Azure with a site-to-site VPN
- Add monitoring with SNMP and syslog

## Tools

Cisco Modeling Labs Free (IOL and IOL-L2), VMware Workstation Pro, Python, Netmiko, TextFSM (ntc-templates), Jinja2, PyYAML, Git.

---

Built by Michael Darian Susanto as a hands-on network automation learning project.
