# 問題 ENCOR-OSPFV3-AREA-01 : OSPFv3 マルチエリア + 集約 + Totally Stubby（難易度6）

## シナリオ
**IPv6 のみ**のネットワーク。バックボーン **area 0**（RT01—RT02）と支店 **area 1**（RT02—RT03—RT04）
で構成。**RT02 が ABR**。支店(area1)の経路はバックボーンに**集約 1 本**で見せ、支店側は
**詳細を持たず default だけ**で外へ出る、という設計にする。

## トポロジ
```
   area 0                         area 1 (Totally Stubby)
  RT01 ─── RT02(ABR) ─────────── RT03 ─────────── RT04
   Lo0      Lo0   │  Et0/1   Et0/0│ Et0/1     Et0/0│ Lo0
2001:DB8:1::1  2001:DB8:2::2      Lo0              2001:DB8:A1:4::4
                              2001:DB8:A1:3::3
  Et0/0─2001:DB8:12::/64─Et0/0   2001:DB8:A1:23::/64   2001:DB8:A1:34::/64
```

| ルータ | エリア | Loopback0 |
|--------|--------|-----------|
| RT01 | area 0 | `2001:DB8:1::1/128` |
| RT02 | ABR (area 0 / area 1) | `2001:DB8:2::2/128` |
| RT03 | area 1 | `2001:DB8:A1:3::3/128` |
| RT04 | area 1 | `2001:DB8:A1:4::4/128` |

- area1 のプレフィクス（Loopback・リンク）はすべて **`2001:DB8:A1::/48`** 配下に整列済み。

## 到達目標
1. リンク IF が無効なら有効化（`no shutdown`）し、**OSPFv3** をマルチエリアで構成して
   **全ルータが全 Loopback に到達**できるようにする（area0 と area1 を ABR=RT02 で接続）。
2. **ABR(RT02) で area1 を `2001:DB8:A1::/48` の 1 本に集約**し、バックボーン(RT01)には
   個別の area1 経路(/128 等)を見せない。
3. **area1 を Totally Stubby** にし、RT03/RT04 は **デフォルト(`::/0`) だけ**で backbone 方向へ出る
   （個別の inter-area 経路を持たない）。到達性は維持すること。

## 制約
- 4 台とも設定変更可。area1 のスタブ設定は**全 area1 ルータで一致**させること（不一致だと隣接不可）。
- IPv6 only では OSPFv3 が **router-id を自動選定できない**点に注意。

## アクセス・採点
SSH `SUZUKI / CCNP`（RT01=.11 / RT02=.12 / RT03=.13 / RT04=.14）。
```
ansible-playbook playbooks/grade.yml -e problem=ENCOR-OSPFV3-AREA-01 --vault-password-file <(printf 'CCNP\n')
```
※ `show ipv6 route ospf` の **集約(/48)・個別抑止・デフォルト(::/0)** に加え、**実 ping** で
集約経由／デフォルト経由の end-to-end 到達を能動確認します。
