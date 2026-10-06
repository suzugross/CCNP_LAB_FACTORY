# Lab GEN-V6ADDR-24425 : IPv6 Automatic Addressing Compliance Troubleshooting (Difficulty 4)

## Scenario

You are the network administrator of a company. The company has deployed automatic IPv6
address assignment on two user LANs (LAN-A / LAN-B). The central router **RT01** is the
DHCPv6 server, and **RT02** is the default gateway and DHCPv6 relay for each LAN. The hosts
(CLA / CLB) obtain their addresses and configuration information through the gateway.

Deployment and change work related to this IPv6 automatic addressing was recently carried
out. Afterwards, the fault report below was submitted. Investigate and correct the
configuration so that it **fully complies with the "LAN Requirements" below**.

## LAN Requirements

1. On LAN-A, **router advertisements (RAs) are suppressed in accordance with the security policy**. Hosts **obtain their IPv6 address from the central DHCPv6 server** (server-managed), and **the default gateway is configured statically**. **RAs must not be enabled.**
2. Hosts on LAN-B **obtain their IPv6 address from the central DHCPv6 server** (server-managed). An autoconfigured address is allowed to coexist.

- On both LANs, hosts must be able to **reach Loopback0 of RT01
  (`2001:DB8:f7:1::1` - a service hosted on the same device as the DNS server)** through the default gateway they obtained.
- The **DNS server to be distributed is `2001:DB8:f7:1::53`** (on LANs that use DHCPv6, the
  **domain name `example.net`** must be distributed as well).

> Note: In IPv6, the default gateway (default route) is not distributed by DHCPv6.
> It is normally learned from router advertisements (RAs), but on a LAN where RAs are
> suppressed it must be configured statically.

## Fault Report

> Hosts on LAN-B obtain an IPv6 address and DNS, but they cannot reach any destination outside their own LAN (servers and so on) at all.

## Topology

```
   RT01 (DHCPv6 server, Lo0=2001:DB8:f7:1::1)
     │ 2001:DB8:f7:12::/64  (core)
   RT02 (GW / DHCPv6 relay)
     ├─ 2001:DB8:f7:A::/64  LAN-A ── CLA
     └─ 2001:DB8:f7:B::/64  LAN-B ── CLB
```

- In the /64 of the core and of each LAN, the RT01/RT02 side is `::1`, and the LAN-side gateway (RT02) is `::1`.
- RT01 handles the DHCPv6 requests of both LANs over a single link (the server automatically
  selects the pool for each LAN based on where the request arrived from).

## Restrictions

- You may modify **RT01, RT02, CLA, and CLB**
  (all are managed by your company). However, **do not change the interface IPv6 addresses
  or Loopback0** of any device. The underlying addressing and routing are sound.
- The type, location, and number of causes are not disclosed. Compare the LAN requirements
  with the state of the devices and identify the differences.

## Access and Scoring

SSH `SUZUKI / CCNP` (mgmt addresses are assigned in order) or the CML console.
```
ansible-playbook playbooks/grade.yml -e problem=GEN-V6ADDR-24425 \
  -e max_attempts=8 -e settle_delay=15 --vault-password-file <(printf 'CCNP\n')
```
> Scoring verifies each LAN requirement (address acquisition method, DNS distribution, whether
> autoconfiguration is permitted) and actual reachability to `2001:DB8:f7:1::1`. Because of
> DHCP exchanges and the RA interval, convergence can take several minutes.
