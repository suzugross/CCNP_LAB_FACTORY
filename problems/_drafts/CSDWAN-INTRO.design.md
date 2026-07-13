# CSDWAN-INTRO — Cisco Catalyst SD-WAN の CML2 導入準備計画（BL-050）

2026-07-12 起草。FGT-SDWAN-01（FortiGate 版 SD-WAN 体感ラボ）完成を受け、
本家 Cisco Catalyst SD-WAN（旧 Viptela: Manager/Controller/Validator + C8000v cEdge）を
CML 2.8.1 に導入し、ENCOR 出題範囲（SD-WAN アーキテクチャ/OMP/TLOC/ポリシー）の
体感ラボ・作問基盤を整える。

## 現状調査結果（2026-07-12 実施・CML API + Web 調査）

### CML サーバ側（10.1.10.10 / v2.8.1 実測）

- **SD-WAN 系ノード定義は未導入**（`/node_definitions` に cat-sdwan-* なし。
  現状: iol/iosv/cat8000v/csr1000v/asav/fortigate 等22定義のみ）
- リソース実測: 16コア / RAM 47.1GB(空き42GB) / ディスク 88GB(空き41.9GB)。
  稼働中ノード14（調査時点）
- **cat8000v-17-15-01a は導入済** → IOS XE 17.2.1r+ は単一イメージで
  autonomous/controller 両モード対応のため、**cEdge は追加イメージ不要**

### 導入ルート（調査で確定した事実）

1. **イメージ入手**: CML Personal ライセンス保持者は software.cisco.com の
   CML-Personal ダウンロードセクションから **supplemental refplat ISO**
   （例 refplat-20241016-supplemental.iso）を取得可能。
   **Manager/Controller/Validator/vEdge = 20.15.1 + SD-WAN Edge(C8000v) 17.15.1a 同梱**。
   SD-WAN 単体ダウンロードページはエンタイトルメント要のため、この refplat 経由が唯一の現実解。
   - https://developer.cisco.com/docs/modeling-labs/reference-platforms-and-images/
2. **ノード定義**: refplat ISO 同梱、または自動化ツールの `csdwan setup` が
   cat-sdwan-manager/controller/validator/edge を自動アップロード。
   手動なら https://github.com/CiscoDevNet/cml-community/tree/master/node-definitions/cisco/sd-wan
3. **自動化ツール**: `pip install catalyst-sdwan-lab`
   （cisco-open/sdwan-lab-deployment-tool、**v3.1.2 2026-07-09 / CML 2.7+対応 / Manager 20.15+ / Python 3.11+**）。
   `csdwan setup` → `csdwan images upload` → `csdwan deploy 20.15.1` で
   コントロールプレーン確立・**証明書（同梱エンタープライズCAで自動署名・インターネット不要）**・
   エッジオンボーディング（`add N edges`）まで全自動。backup/restore/delete あり。
   - ★v2.1.4 未満は CML 2.8 で Manager 起動不能バグあり → 最新版を使うこと
4. **証明書/ライセンス**: エンタープライズCAモードなら Smart Account /
   PnP シリアルファイル**不要**。C8000v controller モードは HSECK9 なしで
   250Mbps 上限だがラボには無関係。

### ★最大の制約 = RAM（要チューニング・唯一の不確実点）

| ノード | ツール既定 | 削減案 |
|---|---|---|
| SD-WAN Manager | 10vCPU / **32GB** / data_volume 50GB | **16GB へ手動削減**（CML FAQ 公称値は16GB） |
| Controller | 2vCPU / 4GB | そのまま |
| Validator | 2vCPU / 4GB | そのまま |
| cEdge ×2 | 4vCPU / 5GB ×2 | そのまま |

- 既定合計 ≒50GB は **RAM 47GB + CML の「80%超で起動拒否」制限（実質予算約37GB）に不適合**。
  Manager 16GB 化で 16+4+4+5+5+alpine×2 ≒ 35GB とギリギリ収まる計算。
  **20.15 Manager が 16GB で application-server を安定起動できるかは未保証**
  （コミュニティに起動失敗報告あり）→ PoC の最重要検証項目。
- ディスク空き42GB: 初期構築は可（data_volume はシンプロビジョニング）だが余裕僅少。
  長期稼働で Manager DB/ログが成長 → **常設せず backup→delete→restore 運用**が前提。
- ノード数: 最小構成 ~10ノード → CML Personal 20ノード上限内。
  ただし**他ラボとの同時稼働はほぼ不可**（RAM 都合）。

## 導入手順（PoC チェックリスト）

### ★進捗 2026-07-12: ステップ1〜3完了・CML に SD-WAN 4定義認識済

- ISO 入手→DVD マウント実施。**★実機知見: CML 2.8 は「マウントした refplat ISO からの
  直接利用」も「ブート時自動読込」も機能しなかった**（sr0 認識・/var/local/virl2/refplat
  へ手動マウント・virl2.target 再起動まで試して全て不発）。
- **確立した手順 = ISO から選択コピー**: ISO を `/var/local/virl2/refplat` に手動 mount →
  `node-definitions/cat-sdwan-*.yaml` と必要イメージ4ディレクトリ
  （manager 4.4G/controller 344M/validator 344M/edge 1.8G ≒ 計6.9GB）を
  **`/var/lib/libvirt/images/` の node-definitions/ と virl-base-images/ へ cp** →
  `chown -R libvirt-qemu:virl2`＋`chmod g+rwX` → `systemctl restart virl2.target` で認識。
  vedge/fmcv/ftdv はスキップ。**以後 ISO マウント不要（DVD 取り外し可）**。
- API 確認済: cat-sdwan-manager(8vCPU/32GB/data_vol 256GB)・controller(2vCPU/4GB)・
  validator(2vCPU/4GB)・edge(2vCPU/5GB) ＋イメージ4点紐づき正常。
- **ホスト RAM 54.8GB に増強確認**（47.1→54.8）→ 80%制限の実質予算 ≒ **43.8GB**。
  Manager 32GB のままでもコントロールプレーン単体(40GB)は起動可能に。
  エッジ2台まで足すなら Manager 24GB 化（合計~43GB ギリギリ）か 16GB 化（~35GB 余裕）。
- `catalyst-sdwan-lab` **v3.1.2 を .venv に導入済**（`csdwan` コマンド利用可）。
- **デプロイ実行（案1=Manager 32GB のままコントロールプレーンのみ先行）**:
  `csdwan deploy 20.15.1` / ラボ名 `sdwan-poc` / direct mode（bridge="System Bridge"）/
  **Manager= 10.1.10.21/26 GW .30（MGMT予約帯 .21-.29 を使用）/ admin / CCNPlab@2026** /
  PKI= enterprise（オフライン）。CML 認証は vault の cml_* を env 渡し
  （スクリプト= scratchpad/run_deploy.py 方式・秘密は透過しない）。

1. [ ] software.cisco.com → CML-Personal → supplemental refplat ISO をダウンロード
2. [ ] ISO 取り込み（★2026-07-12 追加調査済・CML はハイパーバイザ上の VM と API 確認済）:
   - **DVD マウント方式は公式サポート**: ハイパーバイザで ISO を CML VM の CD/DVD に
     アタッチ → cockpit(:9090) CML2 > Maintenance >「Copy Refplat ISO」。
     **全ラボ停止が前提**・OS再起動不要（サービスは自動再起動）。
     代替 = scp で `/var/local/virl2/dropfolder/refplat_images.iso` に置いて同ボタン。
   - ★ただし cockpit コピーは**全量一括のみ（選択不可・約15GB消費）** → 空き42GBでは非推奨
     （Learning Network に容量枯渇でログイン不能事例あり）。
   - **推奨A（最省ディスク）**: ISO をマウントしたまま**コピーしない**
     （マウント中は ISO 上のイメージを直接利用できる設計。supplemental での
     自動認識挙動のみ要実機確認）
   - **推奨B（確実）**: ISO を手元で展開し、Manager/Controller/Validator の qcow2 だけ
     `csdwan images upload --dir <展開dir>` か Web UI (Tools > Image Management) で
     選択投入（FMCv/FTDv/vEdge/cat9800/splunk はスキップ）。
     Manager の image definition は**データディスクサイズ指定が必要**な点に注意。
   - 出典: https://developer.cisco.com/docs/modeling-labs/copy-refplat-iso-to-disk/
3. [ ] Ansible ホストに `pip install catalyst-sdwan-lab`（.venv は Python 3.12 なので可）
4. [ ] `csdwan setup` でノード定義投入 → **Manager ノード定義の RAM を 16GB に編集**
5. [ ] `csdwan deploy 20.15.1` でコントロールプレーン起動（既存稼働ラボは事前停止）
6. [ ] Manager GUI ログイン・certificates/control connections 確認（16GB 安定性の見極め）
7. [ ] `csdwan add 2 edges 17.15.1a` で cEdge オンボーディング
8. [ ] `csdwan backup` → `delete` → `restore` の往復を実証（常設しない運用の要）
9. [ ] 知見をメモリ + 本ファイルに追記

## ★セッションログ 2026-07-12: 初回デプロイ（中断・ラボ停止で退避中）

### 到達点

`csdwan deploy 20.15.1` でラボ **sdwan-poc**（9ノード）が CML に構築され全ノード BOOTED まで到達。
ツールは Manager API 待ちの**内蔵60分タイムアウト**で終了（`ERROR SD-WAN Manager did not
become available within 60 minutes`）。Manager はコンソール応答
`System Initializing. Please wait to login...` のまま（=初期化進行中・ハングではない）。
リソース異常なし（ディスク減1GBのみ・RAM余裕）。**ラボは削除せず STOPPED で退避**
（Manager のディスク状態保持）。

### ツール実機知見（catalyst-sdwan-lab v3.1.2）

1. **★対話プロンプト罠**: `--manager-user` は default=admin があっても **env/引数未指定だと
   対話プロンプトを出す**（バックグラウンド実行だと無言ハング）。必要 env 全部=
   `CML_IP / CML_USER / CML_PASSWORD / MANAGER_IP / MANAGER_MASK / MANAGER_GATEWAY /
   MANAGER_USER / MANAGER_PASSWORD / LAB_NAME`。**stdin を閉じて（`< /dev/null`）実行**すれば
   プロンプト発生時に即エラーで検知可能。
2. 自動生成トポロジ（9ノード）: Manager01/Controller01/Validator01 + VPN0(unmanaged_sw) +
   Gateway(iol-xe・DNS/NAT役) + **INET/MPLS(ioll2・エッジ用2トランスポート敷設済)** +
   ext-conn×2。エッジ追加時は INET/MPLS に接続される。
3. ツール終了してもラボは残る → **`csdwan deploy 20.15.1 --retry` でラボ再作成なしに
   Manager オンボード（証明書署名〜Controller/Validator 登録）から再開できる**。
4. Manager 初回起動の実測: OS ブート（login prompt）まで ~5分、その後
   `System Initializing` が **60分超**（20.15.1・32GB/8vCPU）。次回は「遅い」の閾値を
   90分に設定して判断する。
5. 診断テク: ①コンソールログ API `GET /labs/{id}/nodes/{nid}/consoles/0/log`（読むだけ）
   ②CML コンソールサーバ pexpect（`ssh SUZUKI@10.1.10.10` → `open /sdwan-poc/Manager01/0`）
   ③`ss -tnp | grep 10.1.10.21` で csdwan の SYN-SENT を見る=ポーリング活動の現行犯確認。

### 再開手順（次セッション用）

1. CML で `sdwan-poc` ラボを **start**（GUI or API。ラボID f77e32e0-3d1b-4c6a-b579-324f9b05602b、
   他ラボ停止推奨・RAM 40GB 消費）
2. Manager ブート完了を待つ: `https://10.1.10.21` の応答を監視
   （**初期化途中で停止したため、2回目ブートで初期化が完走するかは未知数**。
   ログインプロンプト到達後も `System Initializing` が続くのは正常、90分超で異常判定）
3. HTTPS 応答後: `.venv/bin/csdwan --verbose deploy 20.15.1 --retry < /dev/null`
   （env は上記9変数。MANAGER_IP=10.1.10.21 / MASK=255.255.255.192 / GW=10.1.10.30 /
   USER=admin / PASSWORD=CCNPlab@2026 / LAB_NAME=sdwan-poc）
4. **2回目ブートでも初期化が完走しない場合**: DB 不整合の可能性 → ラボ削除
   （`csdwan delete --lab sdwan-poc` or CML GUI）→ クリーン再デプロイ。
   その際は (a) 他の全ラボ停止で I/O/CPU を Manager に集中 (b) Manager vCPU を 8→12 に
   一時増強して初期化を加速、を検討
5. オンボード完了後の確認: Manager GUI ログイン → `show control connections`
   （Controller/Validator が up）→ 案1の後半（Manager 24GB 化＋ `csdwan add 2 edges 17.15.1a`）へ

## 作問構想（導入後・別 BL 化予定）

- **CSDWAN-FEEL-01（体感導入）**: FGT-SDWAN-01 と同型の「観察→考察」段階構築。
  OMP ルート交換・TLOC・BFD セッションを diagnose 相当（show sdwan ...）で観察、
  App-Route ポリシーで SLA 切替体感（alpine-wanem で遅延注入は既存資産流用）
- **CSDWAN-TS-01**: control connection 不全 TS（証明書/organization-name 不一致・
  Validator 到達性・シリアル未登録など「コントロールプレーンの故障学」）
- 採点系: Manager REST API（/dataservice/...）採点が有力。既存 grade.py の
  RESTCONF 系実装（NETAUTO-03）の知見を流用可能か要検討
- ENCOR 試験マッピング: 1.2.c SD-WAN（control/data plane 分離・OMP・TLOC）直撃

## リスクと備え

- **R1: Manager 16GB で不安定** → 代替: RAM 増設（ホスト50GB→64GB）まで待つ /
  Controller/Validator のみで OMP を学ぶ縮退構成は不成立（Manager 必須）のため、
  最悪 WWT ATC の無料 SD-WAN Sandbox（20.18.x）で作問前検証
- **R2: ディスク枯渇** → 使わない旧 _generated ラボ/イメージの棚卸しを導入前に実施
- **R3: 他ラボと同時稼働不可** → 出題時は SD-WAN 専用運用（backup/restore で退避）
