# Problem GEN-DMVPNW-14320

## Scenario

A DMVPN, in which RT01 at HQ is the hub and the routers of three branch sites are the spokes, is in the middle of being newly deployed. The previous engineer in charge of the deployment applied the configuration partway, and the work was then handed over. When `show dmvpn` was executed on RT01, not a single spoke was displayed. RT05 is the service provider's router and is outside of your administrative control.

Your task is to ensure that all sites are connected by DMVPN as stated in the configuration specification below, and that traffic between branch sites is carried directly over an encrypted tunnel, without transiting the hub.

## Topology

```
            RT05 (ISP) ─ Lo0 8.8.8.8
      ┌────────┼────────┬────────┐
    RT01      RT02     RT03     RT04
    (HQ)    (Branch1) (Branch2) (Branch3)
```

| Site | Router | Outside address (NBMA) | Tunnel address | LAN (Loopback1) |
|---|---|---|---|---|
| HQ | RT01 | `203.0.113.2` | `172.26.137.1` | `10.71.0.0/24` |
| Branch 1 | RT02 | `198.51.100.2` | `172.26.137.2` | `10.71.2.0/24` |
| Branch 2 | RT03 | `198.51.100.6` | `172.26.137.3` | `10.71.3.0/24` |
| Branch 3 | RT04 | `198.51.100.10` | `172.26.137.4` | `10.71.4.0/24` |

## Configuration Specification

| Item | Specified value |
|---|---|
| Tunnel | A single `Tunnel0` (mGRE) at every site, `172.26.137.0/24`, sourced from the ISP-facing interface |
| GRE key | 2771 |
| NHRP | network-id 614, authentication `BRANCH60`, Phase 3 (hub = redirect / spoke = shortcut) |
| IKE | IKEv1, AES 256 / SHA-256 / DH group 14, pre-shared key `HUBKEY3703` (common to all sites; the peer address is not restricted) |
| IPsec | ESP AES 256 / SHA-256 HMAC, transport mode, no PFS, tunnel protection by an ipsec profile |
| Names | transform-set `TS-DMVPN`, ipsec profile `DMVPN-PROF` (the same names at all sites) |
| HQ outside protection | Access list `EDGE-IN` (permits only IKE, IPsec, and ICMP) is applied inbound on the outside interface |
| MTU / MSS | ip mtu 1400 / ip tcp adjust-mss 1360 |
| Routing | EIGRP AS 834 (the tunnel network + the LAN of each site) |

## Restrictions

1. The configuration of RT05 cannot be changed. The outside interface addresses and the default routes of the routers must not be changed. The HQ outside protection must not be removed.
2. The configuration must use the values and methods in the specification. Connectivity achieved by removing encryption, or by replacing it with a different method, is not allowed.
3. Do not add dedicated tunnels between spokes.

## Access and Scoring

Log in to each device with SSH (`SUZUKI / CCNP`; the mgmt IP addresses are provided when the problem is presented).
```
ansible-playbook playbooks/grade.yml -e problem=GEN-DMVPNW-14320 --vault-password-file <(printf 'CCNP\n')
```
