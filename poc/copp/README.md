# CoPP PoC 実測 (BL-125 P0+E2E・2026-08-16)

盤面= `_POC-COPP`(3 IOL: RT02—RT01(DUT)—RT03・OSPF 全網)。探針= probe.yml / p56.yml、
生ログ= probes/P0〜P6。紙面 shape=copp の設計前提となる実測知見。

## 確定した挙動(6点)

1. **書式(P0/P1)**: `show policy-map control-plane` は
   `Control Plane / Service-policy input: <PM>` 配下に class ごとの
   `Class-map: <NAME> (match-all)` / `Match: access-group <n>` /
   `police: cir 8000 bps, bc 1500 bytes` / `conformed <n> packets, <bytes> bytes;
   actions: transmit` / `exceeded ...; drop` / `conformed 3000 bps, exceeded 0000 bps`。
   **明示していない class-default (match-any) / Match: any の行が必ず末尾に出る**。
   ★`bc 1500 bytes` は config に書いていない自動既定値が show にだけ現れる(read 素材)。
2. **CoPP は punt トラフィックのみ対象(P2)**: 8000bps policer 稼働中に
   RT02→RT03 の transit ICMP 300発= **100% 成功・カウンタ完全不変**(271/29 のまま)。
   「ルータを通る ICMP」と「ルータ宛の ICMP」の区別が最初のひっかけ軸。
3. **ACL の deny = 分類除外(P3)**: `deny icmp host <RT02>` + `permit icmp any` の
   class では、RT02 発 200発=100% 成功(policer 素通り=クラス不一致)、
   RT03 発 300発= 271 適合/29 超過 drop(90%)。**deny は「拒否」ではなく
   「この class に乗せない」**。
4. **未定義 ACL 参照はどの punt にも一致しない(P4)**: `match access-group 199`(未定義)
   の class は **0 packets のまま**で、ICMP は class-default に落ちて無制限=
   200/200 成功。**通信は困らず、保護だけが黙って失効する**サイレント故障
   (IF 適用の「全許可」と結果は似るが機構が逆・BL-106 §1 と整合)。
5. **pps 単位(P5)**: `police rate 10 pps` → 書式は `rate 10 pps, burst 2 packets`
   (burst 2 も自動既定)。★カウンタは `conformed 203 packets, 203 bytes` —
   **pps ポリサでは bytes 欄がパケット数になる**(書式罠・byte 忠実出題の要注意点)。
   瞬時レート行も `conformed 0 pps` と単位が変わる。
6. **exceed-action transmit(P6)**: 超過 87 packets を**数えつつ転送**= ping 100/100
   成功。「policer は付いていて counters も動くのに何も制限されていない」という
   cause/ひっかけの種(監視モード的な見え方)。

## 運用メモ(採点・生成側)

- 負荷生成は `ping <DUT> repeat N timeout 0` が高速(応答を待たない。成功率は無意味に
  なるので**測定は DUT 側カウンタで行う**)。`timeout 1` のままだと drop 毎に 1 秒待ち、
  10pps 制限下の 300 発で 4 分超= ansible の command timeout を食い破る(P5 初回失敗の原因)。
- 8000 bps は police cir の実質最小域・bc 1500 自動。IOL で全探針が期待どおり=
  紙面の盤面プラットフォーム問題なし。

## E2E 実機スポット照合 (P2 後・2026-08-16・16/16 PASS)

探針= `e2e.yml`、生ログ= probes/E1〜E6。P0 で未実測だった紙面モデルの意味論を照合:

1. **E1 class 評価順(kind class_order)**: 広い CM-LIMIT が先・遮断 CM-BLOCK が後 →
   攻撃元 ping **90%**(遮断されず制限どまり)・CM-BLOCK は **0 packets** のまま。
2. **E2 遮断 class 先頭(block_first 正解状態)**: 攻撃元 **0%**・他発信元 90%・
   CM-BLOCK が 50/50 計上。★**police なし class の show は
   `Class-map:`+`Match:` の2行のみ**(class-default と同形・カウンタ行なし)= byte 採取。
3. **E3 conform-action drop(kind conform_drop)**: 低レート 30発= **0%**。
   conformed 30 を計上しつつ actions: drop(「カウンタは動くのに全滅」の実証)。
4. **E4 class-default police(kind cdefault_police)**: 65秒無操作で conformed 15→72・
   exceeded 0→54= **OSPF hello と SSH 管理セッション自身が class-default に道連れ分類
   される実証**(exceeded 54 は show 出力の ACK 群= 管理トラフィックが 1500B バケツを
   食い破る。cdefault_police の「SSH 断続断」症状の機構そのもの)。flood 89% 制限・
   OSPF 隣接は FULL 維持。
5. **E5 紙面盤面の忠実復元**: `--seed 11`(deny_misread) の紙面 config を投入し、
   実機 `show policy-map control-plane` と紙面レンダラ出力が**カウンタ数値を除き
   行単位で一致**(16行・rstrip 基準)。ACL ブロックも一致。挙動= その他発信元 90%。
6. **E6 `permit ospf any any` の class 一致**: 65秒無操作で 14 packets 計上=
   hello が match access-group(proto ospf)に乗る(protect_explicit・select2/allthat の
   OSPF 記述の根拠)。

## 紙面設計への写像(次段 P1 の入力)

- 世界レバー候補: 保護対象の反転(制限する/守る)・deny の意味・未定義参照(サイレント)・
  exceed action・単位(bps/pps)・class 順序+class-default 道連れ。
- 「すべて選べ」候補: 「この構成で **police の対象になる**トラフィックをすべて」
  (transit/punt × ACL permit/deny × 未定義 の組合せを列挙させる)。
- 曖昧要件候補: 「運用に必要な管理アクセスは維持すること」(プロトコルは盤面の
  vty transport から一意補完)。
