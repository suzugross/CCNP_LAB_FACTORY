# 問題 GEN-FNFTS-6640 : Flexible NetFlow 監視標準 適合トラブルシュート（難易度5）

## 状況

中継ルータ **RT02** に、昨日 監視チームが Flexible NetFlow を導入した。
しかし NMS/コレクタ運用チームから下記のトラブルチケットが届いている。
社内の**監視標準仕様書（抜粋・下記）に完全準拠**するよう調査・是正せよ。

```
RT01(顧客側, Lo0=3.3.3.3) ─── RT02(FNF・被疑) ─── RT03(上流側, Lo0=1.1.1.1)
                          Et0/0            Et0/1
```

## トラブルチケット

> 1. 機器の**フローキャッシュにはフローが見えている**のに、コレクタには**一切レコードが届かない**。
> 2. コレクタが「**未登録ソース IP からの NetFlow パケットを破棄**」と警告している。NMS はエクスポータを **Loopback0 の IP で登録**している。

## 監視標準仕様書（抜粋）

RT02 で顧客側からの **入り (ingress) トラフィック**を計測しエクスポートする。

1. **flow record `REC-EDGE`** — match キー: IPv4 送信元/宛先アドレス・IPv4 プロトコル・
   L4 送信元/宛先ポート。collect: counter bytes / counter packets。
2. **flow exporter `EXP-EDGE`** — コレクタ **`203.0.113.236`** へ **UDP `4739`**。
   エクスポート元は **`Loopback0`**。エクスポート形式は **`netflow-v9`**。
3. **flow monitor `MON-EDGE`** — 上記 record と exporter を束ねる。
4. **適用** — RT02 の **RT01 向け IF (`Ethernet0/0`) の ingress (input)**。

## 遵守事項

- FNF の**撤去や別名での作り直しによる「復旧」は不可**（仕様書の名前・値に一致させる）。
- 設定変更は **RT02 のみ**。RT01 / RT03 は変更禁止（状態確認・ping 送信は可）。
- OSPF・アドレッシングは変更しない。
- コレクタ `203.0.113.236` は実在しない（エクスポート先の指定のみ。動作確認はキャッシュで行う）。

## 切り分けの観点

- 原因の種類・場所・数は伏せている。仕様書と実機の状態(`show flow ...` 系)を
  突き合わせて差分を特定すること。
- 採点は設定の字面に加え、**フローキャッシュに仕様どおりのフローが採取されること**まで見る。

## アクセス・採点

SSH `SUZUKI / CCNP`（mgmt は割当順）。
```
ansible-playbook playbooks/grade.yml -e problem=GEN-FNFTS-6640 --vault-password-file <(printf 'CCNP\n')
```
