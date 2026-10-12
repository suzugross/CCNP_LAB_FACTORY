# Problem GEN-URPF-33702 : Anti-Spoofing (uRPF) Troubleshooting (difficulty 3)

## Scenario

The edge router **RT01** is multihomed to two ISPs (routes are received through OSPF).
Yesterday, at the direction of the SOC, **source address verification (uRPF) was deployed on both uplinks**.
The trouble ticket below was subsequently opened. Isolate the cause and **restore** service.

## Topology

```
            RT01 (under your administration, Lo0 = 84.84.84.84)
       E0/0 |              | E0/1
    (Uplink-A)          (Uplink-B)
            |              |
      RT02 (ISP)  ------  RT03 (ISP)
              (inter-ISP peering)
```

## Trouble Ticket

> SOC detection: **Packets suspected of source spoofing that arrive on Uplink-B (E0/1) pass through without being verified** (the interface has no record of verification drops).

## Restrictions (security policy and change scope)

1. Source verification on both uplinks must be **maintained** ("restoring" service by removing it is not allowed).
2. The verification mode must be **the strictest one that is technically possible on each interface**.
3. Legitimate flows (sourced from the ISP NOC keepalive monitor `70.70.70.70` and from customer B `192.168.73.1`) must not be interrupted.
4. **Changing or adding routing configuration (OSPF, static routes) on RT01 is not allowed**.
5. Changing the configuration of RT02 / RT03 (ISP equipment) is not allowed (checking their state is allowed).

## Isolation Guidance

- The type and location of the cause are not disclosed. Isolate it from the state by using `show ip interface <IF>` (verification statistics),
  `show ip route <prefix>`, `show ip cef`, and so on.
- Scoring is based not on the wording of the configuration but on **the state and the actual drop behavior**.

## Access and Scoring

SSH `SUZUKI / CCNP` (mgmt addresses are assigned in order from 10.1.10.11).
```
ansible-playbook playbooks/grade.yml -e problem=GEN-URPF-33702 --vault-password-file <(printf 'CCNP\n')
```
