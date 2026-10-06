# Lab GEN-DHCPTS-81796 : DHCPv4 Distribution Standard Compliance Troubleshooting (Difficulty 3)

## Scenario

Yesterday, address distribution was **consolidated onto RT01 (DHCP server)** and
**security was hardened on the client-facing interfaces**. Immediately afterwards, the
trouble ticket below was received. Investigate and correct the configuration so that it
**fully complies with the company's Address Distribution Standard (excerpt below)**.

```
CL3 ── RT01(DHCP server) ──10.125.132.0/30── RT02(relay) ─┬─ CL1  segment A: 10.125.130.0/24
LOCAL: 10.125.129.0/24        .1        .2                └─ CL2  segment B: 10.125.131.0/24
```

## Trouble Ticket

> **Only the hosts on segment B (10.125.131.0/24) cannot obtain an address at all** (addresses are distributed normally on the other segments).

## Address Distribution Standard (excerpt)

1. **Pools** - LOCAL=`NET-CAMPUS-L` / segment A=`NET-CAMPUS-A` / segment B=`NET-CAMPUS-B`.
   Distribute the network, default-router (the GW `.1` of each segment), and DNS **`198.51.100.138`** for each segment.
2. **Excluded addresses** - **`.1` through `.9`** of each segment are excluded.
3. **Relay** - Relay from both client-facing interfaces of RT02 to **`10.125.132.1`**.
4. **Security** - Apply the ACL **`CAMPUS-DHCP-ONLY`** inbound on both client-facing interfaces of RT02,
   **permitting only DHCP (UDP 67/68) and ICMP**; the last line is an **explicit `deny ip any any`**.
   In this state, **neither initial acquisition (DISCOVER) nor renewal may be broken**.

## Restrictions

- A "restoration" achieved by **removing the standard or re-creating it under a different name is not allowed** (match the names and values in the standard).
- The configuration of the clients (CL1 through CL3) is **correct; do not modify it** (checking state and release/renew are allowed).
- Do not change the interface addresses or static routes of RT01/RT02.
- The type, location, and number of causes are not disclosed. Compare the standard with the devices and identify the differences.

## Access and Scoring

SSH `SUZUKI / CCNP` (mgmt addresses are assigned in order).
```
ansible-playbook playbooks/grade.yml -e problem=GEN-DHCPTS-81796 --vault-password-file <(printf 'CCNP\n')
```
> Scoring verifies that release/renew actually works (re-acquisition with the ACL applied).
