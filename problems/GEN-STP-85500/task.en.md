# Troubleshooting GEN-STP-85500 : 3-Tier Campus L2 Spanning Tree Does Not Match the Design Document

## Scenario
This is a 3-tier campus L2 network consisting of two core switches, two distribution switches, and two access switches. A periodic inspection found that the spanning-tree state and configuration do not match the design document. Operations has also raised the following reports.

> - The inspection reported port/s in the inconsistent state.
> - Around one of the switches, the switchover upon a link failure is reported to be slower than elsewhere.

Note that a switch brought in by a user (SW07) is still connected to SW06 Gi1/3, and the state in which it is blocked is as designed.

Restore the network to the state described in the design document. **There may be more than one cause.**

## Design Document (excerpt)

| Item | Design |
|---|---|
| STP mode | Rapid PVST+ on all switches |
| Path cost | Use the 32-bit method (long) consistently on all switches |
| VLAN78, VLAN135 | root = SW02 (bridge priority 24576); secondary root = SW01 (bridge priority 28672) |
| VLAN199 | root = SW01 (bridge priority 24576); secondary root = SW02 (bridge priority 28672) |
| Distribution layer (SW03, SW04) | **For each VLAN, only one of the two uses bridge priority 36864**, and the other is left at the default. 36864 is assigned on SW03 for VLAN78 and VLAN135, and on SW04 for VLAN199. This determines which side blocks on the distribution-to-distribution link and which side the access-layer uplinks pass through, independent of the switch MAC addresses |
| Access layer (SW05, SW06) | bridge priority is left at the default |
| Protection mechanisms (policy) | **Ports facing the upper layer and links between switches in the same layer** must not transition to the forwarding state even if BPDUs stop arriving (for example, a unidirectional failure). **Ports facing the lower layer** must not yield the root position even if a superior BPDU is received from the lower side. The ports are not listed (determine them from the device inventory) |
| Access edge ports (Gi1/0 to Gi1/3) | Start forwarding without waiting when an end device is connected. Block the port immediately when a BPDU is received, and do not recover automatically |
| How the protection mechanisms are configured | The two edge functions (forwarding without waiting, blocking on a BPDU) and the BPDU-loss protection for the upper-layer-facing and same-layer links are enabled **as switch-wide defaults**. Configure per port only those ports that cannot meet the requirement with the defaults |
| Methods not to be used | Per-port and per-VLAN path cost changes and port-priority are not used |
| Trunks | 802.1Q; allowed VLANs are 78,135,199 only (common to all trunks) |

## Device Inventory

| Device | Role | Cabling |
|---|---|---|
| SW01 | Core CR1 | Gi0/0→SW02 / Gi0/1→SW03 / Gi0/2→SW04 |
| SW02 | Core CR2 | Gi0/0→SW01 / Gi0/1→SW03 / Gi0/2→SW04 |
| SW03 | Distribution DS1 | Gi0/0→SW01 / Gi0/1→SW02 / Gi0/2→SW04 / Gi0/3→SW05 / Gi1/0→SW06 |
| SW04 | Distribution DS2 | Gi0/0→SW01 / Gi0/1→SW02 / Gi0/2→SW03 / Gi0/3→SW05 / Gi1/0→SW06 |
| SW05 | Access AS1 | Gi0/0→SW03 / Gi0/1→SW04 / Gi1/0 to Gi1/3 = edge |
| SW06 | Access AS2 | Gi0/0→SW03 / Gi0/1→SW04 / Gi1/0 to Gi1/3 = edge |
| SW07 | Brought-in device (unmanaged; login prohibited) | Connected to SW06 Gi1/3 (unused port, parking VLAN 99) |

SVIs (for reachability checks; access layer only): VLAN78 = 10.144.78.<SW number>/24 / VLAN135 = 10.144.135.<SW number>/24 / VLAN199 = 10.144.199.<SW number>/24

## Notes
- Do not touch the management VLAN (999) or GigabitEthernet3/3 on any device. Do not log in to SW07.
- You may shutdown / no shutdown ports (this is not counted as a configuration change).
- Do not leave any configuration that is not in the design document.

## Login / Scoring
Use the CML console, or telnet to the management IP (user SUZUKI / pass CCNP; refer to the assignment table issued at provisioning for the management IPs).
```
scripts/lab.sh grade GEN-STP-85500
```
