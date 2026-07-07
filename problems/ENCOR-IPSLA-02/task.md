# 問題 ENCOR-IPSLA-02 : IP SLA 発展 — primary 経路を「奥まで」監視する

## シナリオ
RT01 はデュアルホーム（RT02=primary / RT03=backup）でインターネット(`8.8.8.8`)に出ている。
IPSLA-01 では「すぐ隣（10.0.12.2）」を監視していたが、それでは **primary ISP の
*奥*（RT02↔Internet 間）で障害が起きても気づけず**、primary に張り付いたまま
ブラックホールになる。

そこで、**primary 経路でしか到達できない奥のヘルスビーコン `100.64.0.1`（Internet コア RT04 上）**
を監視し、**primary 全経路の健全性**を track する構成にせよ。primary 経路のどこが切れても
backup へ自動切替し、かつ **フラップしない**こと。

```
RT01 ─10.0.12/30─ RT02(primary) ─10.0.24/30─ RT04(Internet)  8.8.8.8/32 ＋ 100.64.0.1/32(beacon)
     ╲10.0.13/30─ RT03(backup)  ─10.0.34/30─┘
```

## 既設（変更不可：RT02/RT03/RT04）
- `8.8.8.8/32` は primary / backup どちらの ISP からも到達可（データ用）。
- `100.64.0.1/32`（ビーコン）は **primary 経路（RT01→RT02→RT04）でのみ到達可**。
  backup ISP(RT03) はビーコンへの経路を持たない。
- RT02 は Internet/ビーコンへ **RT04 直結のみ**（RT02↔RT04 が切れると primary は両方を失う）。
- ビーコンプローブの戻りを primary 限定にするため、RT04 は送信元 `10.0.12.1` への戻りを
  primary(RT02) 経由のみで持つ。
- RT01 社内アドレス: `Loopback0 = 1.1.1.1`（データの送信元）。

## 到達目標（RT01 のみ設定）
1. **IP SLA 1**（ICMP echo）で **ビーコン `100.64.0.1`** を監視する。
   送信元は **primary 側 IF のアドレス `10.0.12.1`**。
2. ★**ビーコン宛の `/32` スタティックを primary next-hop に固定**する
   （`100.64.0.1/32 → 10.0.12.2`）。これにより:
   - プローブが常に primary を通る（backup に逃げず**フラップしない**）
   - default ルートに依存しない（track と default の循環参照を断ち切る）
3. **Track 1** で SLA 1 の reachability を監視。
4. **default route**: 通常時 primary `10.0.12.2`（Track 1 連動）、
   障害時 backup `10.0.13.2`（**AD 200** フローティング）。
5. 結果として、primary 経路の **どこか（access でも奥の RT02↔RT04 でも）**が切れたら
   track が Down → backup へ切替、`8.8.8.8` への通信が継続すること。

## 指定値（採点が固定値で判定）
- IP SLA 番号 = **1** / Track 番号 = **1**
- SLA: **ICMP echo**、ターゲット = **`100.64.0.1`**、source = **`10.0.12.1`**
- ビーコン固定: **`ip route 100.64.0.1 255.255.255.255 10.0.12.2`**
- primary default = next-hop **10.0.12.2**、Track 1 連動
- backup default = next-hop **10.0.13.2**、**AD 200**

## アクセス
- RT01: `10.1.10.11`（他 .12-.14）SSH(SUZUKI/CCNP) または CMLコンソール

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=ENCOR-IPSLA-02 --vault-password-file <(printf 'CCNP\n')
```

## 奥障害フェイルオーバ実証（任意・本問の目玉）
**RT02↔RT04（奥）リンク**を落として、それでも track Down→backup→`8.8.8.8` 継続を自動確認:
```
ansible-playbook playbooks/verify_failover_deep.yml -e problem=ENCOR-IPSLA-02 --vault-password-file <(printf 'CCNP\n')
```
（IPSLA-01 の near 監視ではこの奥障害を検知できない。その差を体感できる。）
