# store-json：作品の保存形式（JSON）

| 項目 | 内容 |
| --- | --- |
| クレート | `crates/store-json` |
| 依存してよい先 | domain、ports、serde、serde_json |
| 実装するインターフェース | `ports::WorkRepository` |
| 対応する要件 | R-014・R-022・R-050・R-051・R-102 |

## 1. 責務

- 作品（`domain::Work`）と、作品フォルダのファイル（JSON）を相互に変換する。
- どのファイルをどの順番で書くかを決める。
- ファイルが作業フォルダにあるか過去の履歴にあるかは知らない。`FileSource`・`FileSink` を通して読み書きする。

## 2. 構成

```
crates/store-json/src/
├── lib.rs          … JsonWorkRepository（WorkRepository の実装）
├── paths.rs        … ファイルの場所
├── files_v1.rs     … ファイル用の型（形式の版 1）と、domain の型との変換
└── format.rs       … 決まった形で JSON を書き出す
```

### 2.1 ファイル用の型

保存形式を domain の型から切り離すため、ファイル用の型（DTO）を別に定義します。domain の型を変えても保存形式は変わらず、保存形式の版を上げても domain は変わりません。

```rust
#[derive(Serialize, Deserialize)]
struct WorkFileV1 { format_version: u32, page: SizeV1 }

#[derive(Serialize, Deserialize)]
struct LayoutFileV1 { panels: Vec<PanelV1> }

#[derive(Serialize, Deserialize)]
struct PanelV1 { id: String, frame: RectV1, view: ViewV1 }

#[derive(Serialize, Deserialize)]
struct PanelFileV1 { assets: Vec<PlacedAssetV1>, strokes: Vec<StrokeV1> }

#[derive(Serialize, Deserialize)]
struct PlacedAssetV1 { hash: String, x: f32, y: f32, width: f32, height: f32, scale: f32 }

#[derive(Serialize, Deserialize)]
struct StrokeV1 { points: Vec<[f32; 2]> }

fn layout_to_domain(file: LayoutFileV1) -> Result<Layout, StoreError>;
fn layout_from_domain(layout: &Layout) -> LayoutFileV1;
fn content_to_domain(file: PanelFileV1) -> Result<PanelContent, StoreError>;
fn content_from_domain(content: &PanelContent) -> PanelFileV1;
```

`*_to_domain` は、読み込んだ値を確かめます（コマ ID が UUID であること・重複しないこと、ハッシュ値が 64 文字の 16 進数であること、数値が有限で拡大率が正であること）。不正なら `StoreError::Broken` を返します。

### 2.2 ファイルの場所

| ファイル | 中身 | 型 |
| --- | --- | --- |
| `work.json` | 作品の情報（形式の版・ページの大きさ） | `WorkFileV1` |
| `layout.json` | コマ割り | `LayoutFileV1` |
| `panels/<コマ ID>.json` | コマ内容（1 コマ 1 ファイル） | `PanelFileV1` |
| `assets/<ハッシュ値>.png` | 貼った素材（app が置く。場所だけ `asset_path` で教える） | ― |

**work.json**（`format_version` は保存形式の版。形式を変えたときに上げる）

```json
{
  "format_version": 1,
  "page": { "width": 1820.0, "height": 2570.0 }
}
```

**layout.json**（`panels` の並びが読み順。`frame` は枠の位置と大きさ、`view` は表示範囲）

```json
{
  "panels": [
    {
      "id": "3f2b8c1e-0d7a-4e5b-9c61-2a8f4d7e9b10",
      "frame": { "x": 100.0, "y": 100.0, "width": 800.0, "height": 600.0 },
      "view": { "offset_x": 0.0, "offset_y": 0.0, "scale": 1.0 }
    }
  ]
}
```

**panels/<コマ ID>.json**（素材が下、線が上の順に描く。貼った素材には画像の画素数 `width`・`height` も保存し、画像を開かずに当たり判定と拡大縮小ができるようにする）

```json
{
  "assets": [
    { "hash": "b3a1…", "x": 50.0, "y": 40.0, "width": 640.0, "height": 480.0, "scale": 0.5 }
  ],
  "strokes": [
    { "points": [[10.0, 20.0], [12.5, 21.0], [15.0, 23.5]] }
  ]
}
```

## 3. 関数

| 関数 | 内容 | アルゴリズム |
| --- | --- | --- |
| `JsonWorkRepository::new() -> JsonWorkRepository` | 作る | ― |
| `load(&self, src: &dyn FileSource) -> Result<Work, StoreError>` | 作品を読み込む | [A17](#a17-読み込みと形式の版) |
| `save_all(&self, dst: &dyn FileSink, work: &Work) -> Result<(), StoreError>` | すべてのファイルを書く | [A15](#a15-決まった形で書き出す)・[A16](#a16-変わったファイルだけを書く) |
| `save(&self, dst: &dyn FileSink, work: &Work, changes: &Changes) -> Result<(), StoreError>` | 変わったファイルだけを書く | [A16](#a16-変わったファイルだけを書く) |
| `asset_path(&self, hash: &AssetHash) -> RelPath` | `assets/<hash>.png` | ― |

## 4. アルゴリズム

### A15. 決まった形で書き出す

同じデータからは、いつでも同じバイト列を書き出します。保存し直しただけで Git が「変わった」と判定したり、統合で余計な競合が起きたりするのを防ぐためです。

- **項目の順番**：ファイル用の型の宣言順で書く（serde の構造体は宣言順に書き出される）。
- **並びの順番**：コマは読み順、線と素材は描く順。辞書（マップ）は使わない。
- **数値**：domain で 0.01 単位に丸めた値を、serde_json の最短表記で書く（[domain A3](domain.md#a3-線の点の間引きと丸め)）。
- **書式**：インデントは空白 2 つ、改行は LF、ファイルの最後に改行を 1 つ。

```rust
fn to_json_bytes<T: Serialize>(value: &T) -> Vec<u8> {
    let mut bytes = serde_json::to_vec_pretty(value).expect("ファイル用の型は必ず書き出せる");
    bytes.push(b'\n');
    bytes
}
```

### A16. 変わったファイルだけを書く

書く順番を、途中で止まっても読み込める状態が保たれるように決めます。

```
save(dst, work, changes):
    1. for id in changes の Content(id):        dst.write("panels/<id>.json", コマ内容)
    2. if changes に Layout がある:             dst.write("layout.json", コマ割り)
    3. for id in changes の ContentRemoved(id): dst.remove("panels/<id>.json")
```

- コマ内容を先に書くので、新しいコマが `layout.json` に載った時点で、そのコマ内容のファイルはすでにあります。
- コマ内容のファイルを消すのは、`layout.json` からそのコマを外した後です。
- 1 つ 1 つの書き込みは原子的です（[fs A18](fs.md#a18-原子的な書き込み)）。

コマ割りだけを変えた場合、`changes` に `Content` が入らないので、コマ内容のファイルは書かれません（R-014）。

`save_all` は、`work.json` を書いた後、すべてのコマについて `Content` と `Layout` を挙げた `changes` で `save` を呼びます。

### A17. 読み込みと形式の版

```
load(src):
    work_file = src.read("work.json") が None なら Err(NotAWork)
    version = work_file.format_version
    if version > SUPPORTED_VERSION (= 1): return Err(UnsupportedVersion(version))
    match version:
        1 → layout = layout_to_domain(src.read("layout.json"))
            for panel in layout.panels:
                bytes = src.read("panels/<panel.id>.json") が None なら Err(Broken)
                contents[panel.id] = content_to_domain(bytes)
    return Work{ page, layout, contents }
```

- 形式を変えるときは、`files_v2.rs` を加えて `match` に枝を足します。古い版のファイルも読めるようにし、書き出すのは常に最新の版です。
- `layout.json` に載っていない `panels/*.json` は読みません（統合の結果などで残ったファイルは無視する）。

## 5. テスト

| 確かめること |
| --- |
| `save_all` → `load` で、元の作品に戻る |
| 同じ作品を 2 回書き出すと、バイト列が一致する |
| コマ割りだけを変えて `save` すると、`panels/` には何も書かれない |
| 新しいコマを加えて `save` すると、`panels/<id>.json` が `layout.json` より先に書かれる（`MemoryFiles` で書いた順番を記録して確かめる） |
| `format_version` が 2 以上なら `UnsupportedVersion` |
| 不正なコマ ID・ハッシュ値・負の拡大率は `Broken` |
