# 問題 ENCOR-OSPFV3-01 : OSPFv3 (IPv6) 到達性 + IPv6 ACL 制御（難易度5）

## シナリオ
**IPv6 のみ**で運用するネットワーク。RT01—RT02—RT03 のチェーン構成で、各ルータに IPv6
アドレス（リンク／Loopback）と `ipv6 unicast-routing` は設定済み。これから **OSPFv3** で
全 Loopback 相互到達を確立し、さらに **IPv6 ACL** でセキュリティ制御を加える。

## トポロジ
```
   2001:DB8:1::1/128        2001:DB8:2::2/128        2001:DB8:3::3/128
        (Lo0)                    (Lo0)                    (Lo0)
        RT01 ─── 2001:DB8:12::/64 ─── RT02 ─── 2001:DB8:23::/64 ─── RT03
            Et0/0            Et0/0    Et0/1            Et0/0
```

| ルータ | Loopback0 | リンク |
|--------|-----------|--------|
| RT01 | `2001:DB8:1::1/128` | Et0/0=`2001:DB8:12::1` |
| RT02 | `2001:DB8:2::2/128` | Et0/0=`2001:DB8:12::2` ／ Et0/1=`2001:DB8:23::2` |
| RT03 | `2001:DB8:3::3/128` | Et0/0=`2001:DB8:23::3` |

## 到達目標
1. リンク IF が無効なら有効化（`no shutdown`）し、**OSPFv3（エリア 0）** を全ルータの
   全リンク・全 Loopback で構成し、**すべてのルータが他の全 Loopback に到達**できるようにする。
2. **IPv6 ACL** を構成し、**RT01 の Loopback(`2001:DB8:1::1`) から RT03 の Loopback(`2001:DB8:3::3`)
   への通信だけを遮断**する。ただし：
   - **OSPFv3 隣接は維持**（落とさないこと）。
   - RT02 から RT03 Loopback への到達、RT01 から RT02 Loopback への到達など、**他の通信は妨げない**。
   - ACL を**どのルータ／どの方向に置くか**は自由（経路上のどこで濾過しても効果が出れば可）。

## 制約
- 3 台とも設定変更可。適用する IPv6 ACL は、遮断対象以外（OSPFv3・ND・他到達）を通すこと。

## ヒント（最小限）
- IPv6 only の環境では、OSPFv3 が **ルータ ID（32bit）を自動選定できない**点に注意。
- IPv6 ACL は末尾に暗黙の deny がある。`deny` だけ書くと OSPFv3 まで巻き添えになり得る。

## アクセス・採点
SSH `SUZUKI / CCNP`（RT01=.11 / RT02=.12 / RT03=.13）。
```
ansible-playbook playbooks/grade.yml -e problem=ENCOR-OSPFV3-01 --vault-password-file <(printf 'CCNP\n')
```
※ 採点は `show ipv6 route ospf` の経路学習に加え、**実 ping（到達／遮断）** を能動確認します
（RT02→RT03lo 到達・RT01→RT02lo 到達・**RT01→RT03lo は遮断**）。
