# Trouble Ticket GEN-BGPRING-4353 : Eliminating Transit Traffic (Difficulty 4)

## Scenario

Your company's router (RT04) is connected to two service providers (RT01 and RT03) by eBGP. Link-utilization monitoring has detected that traffic that does not belong to your company is passing through your links. This is not the intended behavior.

## Topology (Physical)

```
  RT01 ──── RT02
   │          │
  RT04 ──── RT03
```
Link list (connections and addresses):
```
  RT01:E0/0(.1) ── RT02:E0/0(.2)   10.68.103.0/30
  RT02:E0/1(.1) ── RT03:E0/0(.2)   10.180.191.0/30
  RT03:E0/1(.1) ── RT04:E0/0(.2)   10.50.176.0/30
  RT04:E0/1(.1) ── RT01:E0/1(.2)   10.149.53.0/30
```

Loopback1 of each router is the site network (/24). The logical design (AS numbers and peering details) is not provided. Verify it on the devices.

## Requirements

1. Traffic between other organizations must not transit your company's AS (RT04).
2. The advertisement of your company's network (`172.16.24.0/24`) to both providers must be maintained.
3. This control must be implemented by using a route-map. The use of a filter list (as-path filter-list) is not approved.
4. Reachability to all networks must be maintained.

## Restrictions

1. Configuration changes are permitted only on the devices that are under your company's administrative control.
2. Removing BGP sessions and adding static routes are not permitted.

## Access and Scoring

Log in to each device over SSH (`SUZUKI / CCNP`; the mgmt IP addresses are provided when the lab is assigned).

```
ansible-playbook playbooks/grade.yml -e problem=GEN-BGPRING-4353 --vault-password-file <(printf 'CCNP\n')
```
