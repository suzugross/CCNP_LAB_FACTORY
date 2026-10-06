# Lab GEN-DMVPN-25806 : DMVPN (Phase 3 + IKEv2) Troubleshooting (Difficulty 4)

## Scenario

A **DMVPN** network (IPsec-encrypted, Phase 3) is in operation with HQ (RT01) as the hub and
Branch 1 (RT02) and Branch 2 (RT03) as the spokes. RT04 is the service provider WAN
(**do not modify**).
**Until yesterday, all sites communicated normally, and branch-to-branch traffic used
on-demand, directly encrypted tunnels.** Today, the trouble ticket below was issued.
Isolate the cause and **restore the network to the state defined in the configuration specification**.

```
   RT01 (Hub/NHS, Lo0=1.1.1.1)
     |
   RT04 (WAN transit - do not modify)
   /  \
RT02    RT03 (Spokes, Lo0=2.2.2.2/3.3.3.3)
```

## Trouble Ticket

> Since this morning, **Branch 2 (RT03) is completely down** (it cannot reach HQ or the other branch at all). The other branch is operating normally. Last night, a configuration restore was performed at each site following a device replacement.

## Configuration Specification (the intended normal state - these values are authoritative)

| Item | Specified value |
|------|--------|
| Tunnel | A single `Tunnel0` at every site (mGRE); overlay **`10.255.198.0/24`** (hub `.1` / Branch 1 `.2` / Branch 2 `.3`) |
| GRE key | **507** / NHRP network-id **38** / NHRP authentication **`OVLNET48`** |
| Phase | **Phase 3** (routes continue to point to the hub; branch-to-branch traffic is forwarded over a directly encrypted tunnel) |
| MTU / MSS | ip mtu **1400** / tcp adjust-mss **1360** |
| IKE | **IKEv2**; AES-GCM-256 / PRF SHA-384 / DH 19; PSK common to all sites **`Ss2026#Gen3910`**; DPD 30/5 on-demand |
| IPsec | ESP **AES-GCM-256**; **transport mode**; PFS group19 |
| Routing | EIGRP **AS 396** (tunnel segment + Loopback0 of each router) |

## Restrictions

1. Do not modify RT04 (the WAN) or the underlay (physical interface IP addresses, /30).
2. **Restore** the values and methods given in the specification (a "restoration" achieved by removing encryption or by replacing it with a different method is not allowed).
3. Do not add dedicated spoke-to-spoke tunnels (a single `Tunnel0` only).
4. The type and location of the cause are not disclosed. Isolate it **from the operational state**
   by using commands such as `show dmvpn` / `show crypto ikev2 sa` /
   `show crypto ipsec sa` / `show ip nhrp nhs detail` / `show ip eigrp neighbors`.

## Access and Scoring

Log in to each device from the CML console (`SUZUKI / CCNP`).
```
ansible-playbook playbooks/grade.yml -e problem=GEN-DMVPN-25806 --vault-password-file <(printf 'CCNP\n')
```
> Scoring collects output through the console (`access: console`). The direct branch-to-branch tunnel is triggered by active pings at scoring time.
