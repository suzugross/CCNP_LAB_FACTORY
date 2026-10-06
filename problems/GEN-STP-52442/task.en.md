# Troubleshooting GEN-STP-52442 : Campus L2 Spanning Tree Does Not Match the Design Document

## Scenario
This is a campus L2 network consisting of two distribution-layer switches (SW01, SW02) and two access-layer switches (SW03, SW04).
A periodic inspection found that the spanning-tree state does not match the design document. Operations has also raised the following reports.

> - Traffic for a specific VLAN takes a detour path when viewed from the access layer.
> - One of the uplinks on an access switch has never been used since boot.

Restore the network to the state described in the design document. **There may be more than one cause.**

## Design Document (excerpt)

| Item | Design |
|---|---|
| STP mode | Rapid PVST+ on all switches |
| VLAN225, VLAN181 | root = SW02 (priority 24576); secondary root = SW01 (priority 28672) |
| VLAN42 | root = SW01 (priority 24576); secondary root = SW02 (priority 28672) |
| Access layer | Must be neither root nor secondary root (bridge priority left at default) |
| Use of the two DS-to-DS links | VLAN225 and VLAN181 forward over link 1 (Gi0/0 on both ends); VLAN42 forwards over link 2 (Gi0/1 on both ends) |
| DS-to-DS ports | Loop guard on both ends |
| DS access-facing ports (Gi0/2, Gi0/3) | Root guard |
| Access edge ports (Gi1/0 to Gi1/3) | PortFast + BPDU guard. A port that receives a BPDU must remain err-disabled (recovery only after a request is filed) |
| Trunks | 802.1Q; allowed VLANs are 42,181,225 only (common to all trunks) |
| Path cost | Default (short); no per-VLAN cost changes |

## Device Inventory

| Device | Role | Cabling |
|---|---|---|
| SW01 | Distribution DS1 | Gi0/0, Gi0/1 → SW02 / Gi0/2 → SW03 / Gi0/3 → SW04 |
| SW02 | Distribution DS2 | Gi0/0, Gi0/1 → SW01 / Gi0/2 → SW03 / Gi0/3 → SW04 |
| SW03 | Access AS1 | Gi0/0 → SW01 / Gi0/1 → SW02 |
| SW04 | Access AS2 | Gi0/0 → SW01 / Gi0/1 → SW02 |
| SW05 | Brought-in device (unmanaged; login prohibited) | Connected to SW04 Gi1/3 (unused port, parking VLAN 99) |

SVIs (for reachability checks): VLAN42 = 10.195.42.<SW number>/24 / VLAN181 = 10.195.181.<SW number>/24 / VLAN225 = 10.195.225.<SW number>/24

## Notes
- Do not touch the management VLAN (999) or GigabitEthernet3/3 on any device. Do not log in to SW05.
- Do not make the configuration "work" with settings that are not in the design document (scoring also checks conformance to the design document).

## Login / Scoring
Use the CML console, or telnet to the management IP (user SUZUKI / pass CCNP; refer to the assignment table issued at provisioning for the management IPs).
```
scripts/lab.sh grade GEN-STP-52442
```
