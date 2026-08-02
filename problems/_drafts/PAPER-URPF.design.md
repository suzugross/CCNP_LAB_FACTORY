# PAPER-URPF — uRPF 紙面MCQファミリ (BL-084・shape=urpf)

2026-08-02 ユーザ発案（手組みラボ「uRPF」＋ ENARSI 対策）。BL-080 の紙面化枠
(gen_paper_mcq.py) へ shape=urpf として追加する分野拡張第2弾。
実機ラボ問 **ENARSI-URPF-01(BL-027・完成済・出題可)** の資産を紙面へ横展開する。

## 既存資産（そのまま効く）

- [URPF-01.design.md](URPF-01.design.md) と `poc/urpf/README.md` に **PoC 実証済みの
  核心知見**がある。紙面でもそのまま使える:
  - ★**「偽装 ping が失敗する」を成否で採点/出題してはならない**: 経路の無い送信元は
    uRPF が無くても echo-reply が戻れず 0% → uRPF 未設定でも「効いている」ように見える。
    **証拠は per-IF の `verification drops` カウンタ**(`show ip interface`)で示す。
  - ★**非対称ルーティング下で strict(rx) を無思慮に入れると正規通信が死ぬ**
    (loose=any なら通る)。紙面でも「厳格化したら業務断」の主役ネタ。
  - ★OSPF forwarding address 罠 / `ip ospf cost` では非対称を作れない(プレフィックス
    単位で作る) = 紙面の図・経路表を作る時の前提。

## ユーザ手組みラボ「uRPF」の読解（2026-08-02 ダンプ・温存）

4台リング(iol-0..3・全て static routing)。uRPF は iol-3 の E0/1 に1本:
`ip verify unicast source reachable-via rx 10` ＋ `ip access-list standard 10` に
`permit 10.10.0.5` のみ。**ACL 併用形(許可リストで例外を通す)** の最小形。
→ ユーザ要望「ACL 指定のまぎらわしい config」はこの形を土台にする。

## 紙面ファミリ設計（v1）

**トポロジ**: エッジ RT(採点対象・2アップリンク) + ISP-A/ISP-B + 顧客網。
経路は static/OSPF 混在で「対称フロー・非対称フロー・未広告(スプーフ)源」の3種を作る。

**故障/論点カタログ(v1・6種)**:
| kind | 中身 | 出題の核 |
|------|------|---------|
| `strict_on_asym` | 非対称 IF に rx を適用 → 正規業務断 | 「厳格すぎ」を drops と経路で読む |
| `loose_everywhere` | 全 IF any → スプーフが素通り | 「緩すぎ」(drops が増えない) |
| `acl_num_mismatch` | ★**uRPF が参照する ACL 番号と定義した ACL 番号が違う**(10 と 110 等) | ユーザ発案の主役。複数ホスト許可のつもりが未適用 |
| `acl_wrong_host` | ACL は適用されているが permit するホストが1台違う/ワイルドカード誤り | 例外が効かない |
| `acl_extended_form` | 標準ACL のつもりが拡張ACL 番号帯・src/dst の意味取り違え | 「よく見ると番号帯が違う」 |
| `missing_on_uplink` | 片方の IF にだけ設定 → もう片方から素通り | 適用漏れ |

**証拠セット**: エッジの `show ip interface <IF>`(uRPF 行 + verification drops)・
`show ip route`(対称/非対称の突き合わせ)・`show access-lists`・`show running-config`
＋ 各源からの ping 結果表(★スプーフ側は「成否」でなく drops 増分で語る)。

**要件世界(可変軸)**: 「検証は可能な限り厳格に(rx 優先)」⇄「業務断は不可(any 許容)」
⇄「例外は ACL で明示許可のみ」を抽選し、**同じ状態でも正解が変わる**ようにする
(BL-081 の要件世界と同型)。選択肢は恒久規約どおり事実・操作のみ。

**まぎらわしさの作り込み(ユーザ要望)**: ACL 番号帯(1-99/100-199)・似た番号(10 と 100)・
定義済みだが未参照の ACL・複数 permit 行のうち1行だけ別 ACL に属する、等を
赤ニシンとして常設。

## 実装手順

1. `gen_paper_urpf.py`(素材): 抽選・config 描画・証拠セット・選択肢テンプレ。
   ACL の意味評価は既存 `topologies/acl_model.py`(汎用ACL意味評価器・BL-012〜014)を
   流用できるか要確認 → できれば「ACL が実際に何を許可するか」を機械計算し、
   BL-081 と同様に**「直る候補≥2・要件適合=1」を seed 毎に機械検証**する。
2. gen_paper_mcq.py へ shape=urpf 配線(mixed ルーレットにも追加)。
3. 実機 E2E(1問1周・drops カウンタが紙面に写ることを確認)。

## 注意

- 実機ラボ問 ENARSI-URPF-01 とは**別物**(あちらは実機で解く構築+TS)。紙面版は
  「読んで選ぶ」ドリルとして併存させる。
- ユーザ手組みラボ「uRPF」は温存(読取のみ)。
