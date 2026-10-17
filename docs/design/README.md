# 分散創造 設計書（v0.1.0 試作品）

| 項目 | 内容 |
| --- | --- |
| 対象の版 | v0.1.0（試作品） |
| 作成日 | 2026-09-24 |
| 更新日 | 2026-10-17 |

[仕様書](../spec/) の動きを実現する内部構造を定めます。各文書の見出しに、対応する要件 ID を書きます。技術選定の理由は [設計判断の記録](../decisions/) にあります。

## 1. 文書の一覧

| 文書 | 内容 |
| --- | --- |
| [architecture.md](architecture.md) | 全体構成：ポートとアダプター、クレート構成、依存の規則、用語とコード上の名前、スレッド・エラー・テストの方針 |
| [sequences.md](sequences.md) | 主な操作のシーケンス図（S1〜S14） |
| [modules/domain.md](modules/domain.md) | データと純粋な処理：作品の型、座標の変換、当たり判定、編集操作 |
| [modules/ports.md](modules/ports.md) | インターフェース：ファイル・保存形式・履歴管理・素材置き場・P2P・ID のトレイト |
| [modules/app.md](modules/app.md) | ユースケース：画面からの操作の窓口、作品の状態、保存・履歴更新・統合 |
| [modules/store-json.md](modules/store-json.md) | 保存形式（JSON）の実装 |
| [modules/fs.md](modules/fs.md) | ファイルの読み書きと素材置き場の実装 |
| [modules/vcs-git.md](modules/vcs-git.md) | git コマンドによる履歴管理の実装 |
| [modules/exchange-iroh.md](modules/exchange-iroh.md) | Iroh による素材の受け渡しの実装 |
| [modules/ui-egui.md](modules/ui-egui.md) | 画面：道具、描画、作業スレッド |
| [modules/testkit.md](modules/testkit.md) | テスト用の実装 |

## 2. 全体像

外の世界（ファイル・git・P2P）とのやりとりを**インターフェース（ports）**と**実装（アダプター）**に分け、中心部（domain・app）はインターフェースだけを知る形にします。部品はクレートとして分け、依存の規則をコンパイラに守らせます。詳しくは [architecture.md](architecture.md) を参照してください。

```
ui-egui ──→ app ──→ ports ──→ domain
                └──────────→ domain
store-json・fs・vcs-git・exchange-iroh ──（ports を実装）──→ ports
bunsan-souzou（組み立て役）──→ すべて
```

## 3. 作品フォルダ（R-014・R-022・R-050・R-051・R-102）

```
作品フォルダ/
├── .git/
├── .gitattributes           … vcs-git が作る
├── work.json                … 作品の情報
├── layout.json              … コマ割り
├── panels/
│   └── <コマ ID>.json       … コマ内容（1 コマ 1 ファイル）
└── assets/
    └── <ハッシュ値>.png     … 貼った素材
```

- コマ割り（`layout.json`）とコマ内容（`panels/`）を別ファイルにすることで、コマ割りの変更とコマ内容の変更が Git 上でも別ファイルの変更になります。別々の履歴系統で行った変更は、競合せずに統合できます（仕様書 7.5、要件定義書 2 章の手順 9）。
- 素材のファイル名はハッシュ値なので、同じ素材は同じファイル名になり、統合時に競合しません。
- ファイルの中身と書く順番は [store-json.md](modules/store-json.md) にあります。

## 4. 実装の順序

| 段階 | 内容 | 主なクレート | 要件 |
| --- | --- | --- | --- |
| M0 | P2P の検証用プログラム | exchange-iroh | R-030〜R-032 |
| M1 | ワークスペースの骨組み、作品の作成・保存、1 コマへの描画と消しゴム | domain・ports・app・store-json・fs・ui-egui・testkit・bunsan-souzou | R-001・R-002・R-050・R-051 |
| M2 | コマ割り（作成・移動・大きさ・表示範囲・読み順） | domain・ui-egui | R-010〜R-014 |
| M3 | 履歴（履歴更新・一覧・表示・戻す・分岐・統合・アップロード・ダウンロード） | vcs-git・app・ui-egui | R-040〜R-045 |
| M4 | 素材の貼り付け | domain・fs・app・ui-egui | R-020〜R-022 |
| M5 | P2P を本体に組み込み、完成の定義の流れを通す | exchange-iroh・app・ui-egui | R-030〜R-032 |

M0 は M1 と並行して進められます。各段階は、段階ごとにブランチとプルリクエストを分けます。
