# Lab GEN-EIGRPV6-90761 : EIGRPv6 (IPv6) Complex Troubleshooting — Mixed Classic/Named (Difficulty 5)

## Scenario
There is a reachability failure in an **IPv6-only**, single-AS (**100**) EIGRPv6 network. Restore the network to a state
in which every router can reach every Loopback. **The enablement style is mixed per router: classic (`ipv6 router eigrp`) and named
(`router eigrp CCNP6` + `address-family ipv6`).**

## Trouble Ticket (representative symptom — 1 item)
> **RT01 cannot reach the Loopback of RT04 (`2001:DB8:40::40`).** There may be more than one cause.

## Router / Loopback Ledger (the mgmt addresses are assigned in order)
| Router | Loopback0 | Style | mgmt(SSH) |
|--------|-----------|-------|-----------|
| RT02 | `2001:DB8:32::32/128` | classic | 10.1.10.11 |
| RT07 | `2001:DB8:71::71/128` | classic | 10.1.10.12 |
| RT03 | `2001:DB8:23::23/128` | classic | 10.1.10.13 |
| RT01 | `2001:DB8:4::4/128` | classic | 10.1.10.14 |
| RT05 | `2001:DB8:52::52/128` | named | 10.1.10.15 |
| RT06 | `2001:DB8:46::46/128` | classic | 10.1.10.16 |
| RT04 | `2001:DB8:40::40/128` | named | 10.1.10.17 |

## Objectives / Troubleshooting
- Every router learns every Loopback in `show ipv6 route eigrp`, with mutual reachability.
- The topology and the type, location, and number of the faults are not disclosed.
- **EIGRPv6 key points**:
  - With classic, only the interfaces configured with **`ipv6 eigrp 100`** participate.
  - The named IPv6 AF has **no network statement; every interface that has IPv6 participates automatically**.
    To exclude or stop an interface, use `shutdown` under `af-interface <IF>` (= this can be a pitfall).
  - Authentication: classic = `ipv6 authentication ...` directly under the interface; named = under af-interface.
    Named can also use **hmac-sha-256** (**a neighbor relationship does not form unless the method and the key match on both ends**).
  - A hello/hold mismatch does not bring a neighbor down. A K-value mismatch brings all neighbors down. A stub on a transit router makes everything downstream disappear.
- Isolation: `show ipv6 eigrp neighbors` / `show ipv6 eigrp interfaces` / `show ipv6 protocols` /
  `show ipv6 route eigrp` / `show running-config | section eigrp`.

## Access and Scoring
SSH `SUZUKI / CCNP`.
```
ansible-playbook playbooks/grade.yml -e problem=GEN-EIGRPV6-90761 --vault-password-file <(printf 'CCNP\n')
```
