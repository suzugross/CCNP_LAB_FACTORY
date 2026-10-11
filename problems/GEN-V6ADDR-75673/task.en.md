# Problem GEN-V6ADDR-75673 : IPv6 Prefix Delegation Compliance Troubleshooting (Difficulty 5)

## Scenario

You are the network administrator of a company. The central router **RT01** is a DHCPv6 server and
also a **prefix delegation (PD) server**, and it delegates an IPv6 prefix to the CPE router **RT03**
at a branch site. RT03 derives a /64 for its downstream LAN from the prefix it receives, and the
downstream host **HST** automatically generates its address from that /64 using SLAAC. Separately,
**LAN-A** (host CLA) behind **RT02** is also served.

After recent work, the following trouble report has been submitted. Investigate and correct the
configuration **so that it fully complies with the requirements below**.

## Requirements

1. Hosts on LAN-A **automatically generate their IPv6 addresses** (based on router advertisements) and **obtain configuration information such as DNS from the central DHCPv6 server**.
2. **The CPE (RT03) receives a prefix delegation from the upstream RT01** and derives a /64 for
   its downstream LAN. The downstream host **HST** **automatically generates its IPv6 address** from that /64.
   The /64 used for the downstream LAN must be **subnet ID `2`** of the delegated prefix
   (that is, `2001:DB8:f000:2::/64`).
3. HST must be able to **reach Loopback0 of RT01 (`2001:DB8:a1:1::1`)** through the CPE.

## Topology

```
   RT01 (DHCPv6/PD server, Lo0=2001:DB8:a1:1::1)
     ├─ 2001:DB8:a1:12::/64  ── RT02 (GW/relay) ── 2001:DB8:a1:A::/64  LAN-A ── CLA
     └─ 2001:DB8:a1:13::/64  ── RT03 (CPE) ── (delegated /64) ── HST
```

- RT01 operates as an ordinary DHCPv6 server toward LAN-A and as a prefix delegation server
  toward RT03 (the two are on separate interfaces).
- The **DNS server** to be distributed is **`2001:DB8:a1:1::53`**, and the domain name is `example.net`.

## Restrictions

- You may change **RT01, RT02, CLA, RT03, and HST** (all are managed by your company). However,
  **do not change the interface IPv6 addresses or Loopback0** of any device (addresses derived from
  the delegated prefix are exempt from this).
- The type, location, and number of causes are not disclosed. Compare the requirements with the
  state of the devices to identify the differences.

## Access / Scoring

SSH `SUZUKI / CCNP` (mgmt addresses in order of assignment) or the CML console.
```
ansible-playbook playbooks/grade.yml -e problem=GEN-V6ADDR-75673 \
  -e max_attempts=8 -e settle_delay=15 --vault-password-file <(printf 'CCNP\n')
```
> Scoring checks acquisition of the delegated prefix (server binding / general-prefix on the CPE),
> address generation on the downstream host, and actual reachability to `2001:DB8:a1:1::1`.
