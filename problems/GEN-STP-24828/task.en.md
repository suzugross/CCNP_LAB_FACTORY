# Trouble Ticket GEN-STP-24828 : The Boundary Between the MST Region and the Legacy Switch Does Not Match the Design Document

## Scenario
This is a campus Layer 2 network with two distribution switches (SW01, SW02) and two access switches (SW03, SW04). SW01 through SW03 run MST, and SW04 is a legacy switch that does not support MST (Rapid PVST+) and forms the region boundary.
A periodic inspection found that the spanning-tree state does not match the design document. Operations has also reported the following.

> - An inspection result shows that, on the links between the DSs, a port in some instances is neither forwarding nor standing by.
> - The path of a specific VLAN does not match the path of its instance in the design document.

Restore the state to match the design document. **The cause is not necessarily in a single place.**

## Design Document (excerpt)

| Item | Design |
|---|---|
| MST region | SW01, SW02, SW03. Name `SITE01`, revision 7. Instance 1 = VLAN90 and VLAN175, instance 2 = VLAN137 (all other VLANs are in the IST) |
| SW04 | Legacy switch that does not support MST. It stays on Rapid PVST+ (outside the region). The path cost method is long |
| CIST and instance 1 | root = SW01 (priority 24576), backup root = SW02 (priority 28672) |
| Instance 2 | root = SW02 (priority 24576), backup root = SW01 (priority 28672) |
| Priority of the access layer (SW03, SW04) | Left at the default (they do not become root for any VLAN or instance) |
| Use of the two inter-DS links | In normal operation, instance 1 forwards on link 1 (Et0/0 to Et0/0) and instance 2 forwards on link 2 (Et0/1 to Et0/1). Per-port and per-instance path cost changes are not used |
| Inter-DS ports | Must not transition to the forwarding state even if BPDUs stop arriving (both ends) |
| Access-facing ports of the DSs (Et0/2, Et0/3) | Must not give up the root role even if a superior BPDU is received from the access side |
| Access edge ports (Et1/0 through Et1/3) | Start forwarding without waiting when an end host connects. Shut down immediately when a BPDU is received |
| trunk | 802.1Q; the allowed VLANs are 90,137,175 only (common to all trunks) |

## Topology (Inventory)

| Device | Role | Cabling |
|---|---|---|
| SW01 | Distribution DS1 (MST) | Et0/0, Et0/1→SW02 / Et0/2→SW03 / Et0/3→SW04 |
| SW02 | Distribution DS2 (MST) | Et0/0, Et0/1→SW01 / Et0/2→SW03 / Et0/3→SW04 |
| SW03 | Access AS1 (MST) | Et0/0→SW01 / Et0/1→SW02 / Et1/0 through Et1/3 = edge |
| SW04 | Access AS2 (legacy, Rapid PVST+) | Et0/0→SW01 / Et0/1→SW02 / Et1/0 through Et1/3 = edge |

SVIs (for reachability checks): VLAN90 = 10.85.90.<SW number>/24 / VLAN137 = 10.85.137.<SW number>/24 / VLAN175 = 10.85.175.<SW number>/24

## Notes
- Do not touch the management VLAN (999) or Ethernet3/3 of each device.
- Do not change the spanning-tree mode of SW04.

## Login / Scoring
CML console, or telnet to the management IP (user SUZUKI / pass CCNP. See the assignment table provided when the problem is presented for the management IPs).
```
scripts/lab.sh grade GEN-STP-24828
```
