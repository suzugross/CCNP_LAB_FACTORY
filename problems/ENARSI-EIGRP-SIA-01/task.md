# 問題 ENARSI-EIGRP-SIA-01 : 隣接は上がるのに経路が来ない（EIGRP SIA/クエリ不達）（難易度5）

## 状況
named-mode EIGRP（AS 100）の小規模網。**RT04 の Loopback `T = 10.100.100.100/32`** へ
**RT01 から到達できない**という申告です。RT01 では EIGRP の隣接自体は「見える」のに、
RT03 の先（RT04）の経路が入ってきません。

```
RT02 ── RT01 ── RT03 ── RT04
(健全)          (?)        (T=10.100.100.100 / 10.4.4.4)
```

| ルータ | Loopback | mgmt(SSH) |
|--------|----------|-----------|
| RT01 | 10.1.1.1 | 10.1.10.11 |
| RT02 | 10.2.2.2 | 10.1.10.12 |
| RT03 | 10.3.3.3 | 10.1.10.13 |
| RT04 | 10.100.100.100（T）/ 10.4.4.4 | 10.1.10.14 |

## 到達目標
- **RT01 が T（10.100.100.100）へ到達**し、網全体が相互到達すること。
- 変更してよいのは設定のみ（スタティック等の“逃げ”は使わない＝EIGRP で解決する）。

## 切り分けのヒント（EIGRP の勘所）
- `show ip eigrp neighbors` を**健全な隣接と見比べる**：片方の隣接だけ **Q Cnt が下がらない／
  RTO が最大(5000)**、`show ip eigrp neighbors` の uptime が周期的に若返る（=リセットしている）。
- `show logging` に隣接の up/down が繰り返し出ていないか（`retry limit exceeded` 等）。
- 隣接は Hello（マルチキャスト 224.0.0.10）で成立するが、**Update/Query/Reply/ACK は
  ユニキャスト**。ここだけが通らないと「隣接は上がるが経路交換が完了しない」状態になる。
- その区間で EIGRP のユニキャストが落ちていないか——**インタフェースの入出力フィルタ**を疑う。
- `show ip eigrp topology active` / SIA（Stuck-in-Active）はクエリのリプライが返らない時に起きる。
  今回の症状はその一族（リプライ/ACK 不達）。

## アクセス・採点
SSH `SUZUKI / CCNP`。
```
ansible-playbook playbooks/grade.yml -e problem=ENARSI-EIGRP-SIA-01 --vault-password-file <(printf 'CCNP\n')
```
