# 問題 ENCOR-VACL-01 : VACL で VLAN 内の Telnet を遮断

## シナリオ
スイッチ **SW01** の業務 VLAN **10 (USERS)** で、セキュリティ強化のため
**VLAN 10 内を流れる Telnet (TCP 23) のトラフィックを遮断**したい。
ただし Telnet 以外の通信は通常どおり**転送**すること。

ルータの ACL（インタフェース ACL）ではなく、**VACL（VLAN access-map）**で
VLAN 内のトラフィックに対して直接フィルタを掛けてください。

## 構成（初期状態で投入済み）
- SW01 は **iosvl2（L2 スイッチ）**。
- VLAN **10**（name USERS）作成済み。
- VACL は未設定。

## 到達目標 — SW01 のみ
1. Telnet (TCP 23) にマッチする ACL を作る。
2. **VLAN access-map** を作り、
   - 上記 ACL にマッチしたトラフィックは **drop**、
   - それ以外は **forward** する。
3. その VLAN access-map を **`vlan filter` で VLAN 10 に適用**する。

## 制約
- 設定するのは **SW01 のみ**。
- ★ VACL は「ACL が permit したパケット」に対して map の action を適用する点に注意
  （ACL は分類用。drop したいトラフィックを ACL で **permit** する）。
- ★ map の最後に「その他を forward」するエントリを置かないと、暗黙の drop で
  VLAN 内の通信がすべて落ちる。

## アクセス
- SW01: `10.1.10.11`（**Telnet**, SUZUKI / CCNP。このスイッチは SSH 不可）

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=ENCOR-VACL-01 --vault-password-file <(printf 'CCNP\n')
```
