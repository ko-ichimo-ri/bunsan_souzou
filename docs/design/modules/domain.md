# domain：データと純粋な処理

| 項目 | 内容 |
| --- | --- |
| クレート | `crates/domain` |
| 依存してよい先 | 外部の純粋なライブラリ（blake3・uuid） |
| 対応する要件 | R-001・R-002・R-010〜R-014・R-020〜R-022 |

## 1. 責務

- 作品のデータ構造（作品・コマ割り・コマ・コマ内容・線・貼った素材）を定義する。
- 座標の変換、当たり判定、編集操作を、**入力から出力が決まる純粋な関数**として提供する。
- ファイル・git・通信・画面のことは知らない。新しい ID の作り方も知らない（ID は呼び出し側から受け取る）。

## 2. 型

### 2.1 基本の型

```rust
/// ページ座標・コマ内容座標の点。単位は 0.1 mm（ページの幅 = 1820）。
pub struct Point { pub x: f32, pub y: f32 }

/// 大きさ。
pub struct Size { pub width: f32, pub height: f32 }

/// 長方形（左上の点と大きさ）。
pub struct Rect { pub origin: Point, pub size: Size }

/// 長方形の四隅。
pub enum Corner { TopLeft, TopRight, BottomLeft, BottomRight }

/// コマ ID（UUID v4）。作り方は app が決める。
pub struct PanelId(uuid::Uuid);

/// 素材のハッシュ値（BLAKE3 を 16 進数 64 文字で表したもの）。
pub struct AssetHash(String);

impl AssetHash {
    /// バイト列からハッシュ値を計算する。
    pub fn of(bytes: &[u8]) -> AssetHash;
    /// 16 進数 64 文字かを確かめてから作る。
    pub fn parse(s: &str) -> Result<AssetHash, ParseHashError>;
}
```

### 2.2 作品

```rust
/// 作品全体。
pub struct Work {
    pub page: Size,                                   // 1820 × 2570
    pub layout: Layout,                               // コマ割り
    pub contents: BTreeMap<PanelId, PanelContent>,   // コマ内容（コマ ID → 中身）
}

/// コマ割り。panels の並びが読み順。
pub struct Layout { pub panels: Vec<Panel> }

/// コマ（枠）。
pub struct Panel {
    pub id: PanelId,
    pub frame: Rect,   // ページ座標
    pub view: View,    // 表示範囲
}

/// コマ内容の表示範囲（トリミング）。
pub struct View {
    pub offset: Point, // 枠の左上から、コマ内容の原点までのずれ（ページ座標）
    pub scale: f32,    // 拡大率
}

/// コマ内容。描く順は assets → strokes（素材が下、線が上）。
pub struct PanelContent {
    pub assets: Vec<PlacedAsset>,
    pub strokes: Vec<Stroke>,
}

/// 線（コマ内容座標の点の並び）。
pub struct Stroke { pub points: Vec<Point> }

/// 貼った素材。
pub struct PlacedAsset {
    pub hash: AssetHash,
    pub position: Point,   // 左上（コマ内容座標）
    pub natural: Size,     // 画像の画素数（1 画素 = 1 単位として扱う）
    pub scale: f32,
}
```

`Work` と `PanelContent` の対応は、`layout.panels` にあるコマ ID と `contents` のキーが一致することを不変条件とします。

### 2.3 変更の記録

編集操作は、どのファイルに書き戻す必要があるかを `Changes` として返します。app はこれを集めて、保存のときに変わったファイルだけを書きます（[store-json 3.2](store-json.md#32-変わったファイルだけを書く)）。

```rust
pub enum Touched {
    Layout,                    // layout.json
    Content(PanelId),          // panels/<id>.json
    ContentRemoved(PanelId),   // panels/<id>.json を削除
    AssetAdded(AssetHash),     // assets/<hash>.png を作品フォルダに置く
}

pub struct Changes(BTreeSet<Touched>);
```

### 2.4 エラー

```rust
pub enum EditError {
    PanelNotFound(PanelId),
    StrokeNotFound { panel: PanelId, index: usize },
    AssetNotFound { panel: PanelId, index: usize },
    OutsidePage,      // ページの外にコマを作ろうとした
}
```

## 3. 関数

### 3.1 作品の作成

| 関数 | 内容 |
| --- | --- |
| `Work::empty() -> Work` | B5 縦のページで、コマのない作品を作る |

### 3.2 座標の変換（[A1](#a1-座標の変換)）

| 関数 | 内容 |
| --- | --- |
| `Panel::to_page(&self, p: Point) -> Point` | コマ内容座標 → ページ座標 |
| `Panel::to_content(&self, q: Point) -> Point` | ページ座標 → コマ内容座標 |
| `Viewport::fit(page: Size, canvas: Rect) -> Viewport` | ページをキャンバスに収める変換を作る |
| `Viewport::to_screen(&self, q: Point) -> Point` | ページ座標 → 画面座標 |
| `Viewport::to_page(&self, s: Point) -> Point` | 画面座標 → ページ座標 |

### 3.3 当たり判定（[A2](#a2-コマの当たり判定)）

| 関数 | 内容 |
| --- | --- |
| `Layout::panel_at(&self, q: Point) -> Option<PanelId>` | 点を含むコマのうち、いちばん上のコマ |
| `Layout::corner_at(&self, q: Point, tolerance: f32) -> Option<(PanelId, Corner)>` | 点の近くにあるコマの角 |
| `Work::asset_at(&self, panel: PanelId, q: Point) -> Option<usize>` | 点を含む貼った素材のうち、いちばん上のもの |

### 3.4 コマ割りの編集（R-010〜R-013）

| 関数 | 内容 | アルゴリズム |
| --- | --- | --- |
| `Work::add_panel(&mut self, id: PanelId, frame: Rect) -> Result<Changes, EditError>` | コマを読み順の最後に加え、空のコマ内容を作る | [A5](#a5-コマの移動と大きさの変更) |
| `Work::remove_panel(&mut self, id: PanelId) -> Result<Changes, EditError>` | コマとコマ内容を消す | ― |
| `Work::move_panel(&mut self, id: PanelId, delta: Point) -> Result<Changes, EditError>` | 枠を動かす（中身は枠と一緒に動く） | [A5](#a5-コマの移動と大きさの変更) |
| `Work::resize_panel(&mut self, id: PanelId, corner: Corner, to: Point) -> Result<Changes, EditError>` | 角を動かして大きさを変える（中身はページ上の位置を保つ） | [A5](#a5-コマの移動と大きさの変更) |
| `Work::reorder_panel(&mut self, id: PanelId, toward: Reorder) -> Result<Changes, EditError>` | 読み順を 1 つ前／後へ | [A8](#a8-読み順の入れ替え) |
| `Work::pan_view(&mut self, id: PanelId, delta: Point) -> Result<Changes, EditError>` | 表示範囲をずらす | [A6](#a6-表示範囲のずらしと拡大縮小) |
| `Work::zoom_view(&mut self, id: PanelId, factor: f32, anchor: Point) -> Result<Changes, EditError>` | 表示範囲を、anchor（ページ座標）を中心に拡大・縮小 | [A6](#a6-表示範囲のずらしと拡大縮小) |

コマ割りの編集が返す `Changes` は、コマの削除を除いて `Touched::Layout` だけです。コマ内容のファイルは変わりません（R-014）。

### 3.5 線の編集（R-001・R-002）

| 関数 | 内容 | アルゴリズム |
| --- | --- | --- |
| `Work::start_stroke(&mut self, panel: PanelId, q: Point) -> Result<(usize, Changes), EditError>` | 線を始め、その番号を返す | [A3](#a3-線の点の間引きと丸め) |
| `Work::extend_stroke(&mut self, panel: PanelId, index: usize, q: Point) -> Result<Changes, EditError>` | 線に点を加える（近すぎる点は加えない） | [A3](#a3-線の点の間引きと丸め) |
| `Work::erase(&mut self, panel: PanelId, from: Point, to: Point) -> Result<Changes, EditError>` | 消しゴムが from から to へ動いたときに触れた線を消す | [A4](#a4-消しゴム) |

### 3.6 貼った素材の編集（R-020・R-021）

| 関数 | 内容 | アルゴリズム |
| --- | --- | --- |
| `Work::place_asset(&mut self, panel: PanelId, hash: AssetHash, natural: Size) -> Result<Changes, EditError>` | コマの見えている範囲の中央に貼る | [A7](#a7-素材の配置と拡大縮小) |
| `Work::move_asset(&mut self, panel: PanelId, index: usize, delta: Point) -> Result<Changes, EditError>` | 動かす（delta はページ座標） | [A7](#a7-素材の配置と拡大縮小) |
| `Work::scale_asset(&mut self, panel: PanelId, index: usize, corner: Corner, to: Point) -> Result<Changes, EditError>` | 縦横比を保って拡大・縮小 | [A7](#a7-素材の配置と拡大縮小) |
| `Work::remove_asset(&mut self, panel: PanelId, index: usize) -> Result<Changes, EditError>` | コマから外す | ― |

## 4. 定数

| 名前 | 値 | 意味 |
| --- | --- | --- |
| `PAGE` | 1820 × 2570 | ページの大きさ（B5 縦、0.1 mm 単位） |
| `MIN_PANEL_SIZE` | 50 | コマの幅・高さの最小値（5 mm） |
| `MIN_POINT_STEP` | 3.0 | 線の点の最小間隔（ページ座標、0.3 mm） |
| `ERASER_RADIUS` | 10.0 | 消しゴムの半径（ページ座標、1 mm） |
| `VIEW_SCALE_RANGE` | 0.1〜10.0 | 表示範囲の拡大率の範囲 |
| `ASSET_FIT_RATIO` | 0.8 | 素材を貼るときに、コマの何割に収めるか |
| `COORD_QUANTUM` | 0.01 | 座標を丸める単位 |

## 5. アルゴリズム

### A1. 座標の変換

座標は 3 種類あります。

| 座標 | 原点 | 用途 |
| --- | --- | --- |
| コマ内容座標 `p` | コマ内容の原点 | 線と貼った素材の位置（保存される） |
| ページ座標 `q` | ページの左上 | 枠の位置、当たり判定 |
| 画面座標 `s` | ウィンドウの左上 | マウスの位置、描画 |

**コマ内容 ↔ ページ**（コマの `frame` と `view` を使う）

```
q = frame.origin + view.offset + p × view.scale
p = (q − frame.origin − view.offset) ÷ view.scale
```

**ページ ↔ 画面**（`Viewport`。ページをキャンバスに収めて中央に置く）

```
k      = min(canvas.width ÷ page.width, canvas.height ÷ page.height) × 0.95
origin = canvas.origin + (canvas.size − page × k) ÷ 2
s      = origin + q × k
q      = (s − origin) ÷ k
```

### A2. コマの当たり判定

コマは読み順の後ろほど上に描かれます。上にあるコマを優先するため、**読み順の後ろから**調べます。

```
panel_at(q):
    for panel in layout.panels を後ろから:
        if panel.frame が q を含む: return panel.id
    return None
```

角の判定（`corner_at`）は、選択中のコマを先に調べ、四隅のうち q からの距離が `tolerance` 以下で最も近い角を返します。

### A3. 線の点の間引きと丸め

マウスの位置は 1 フレームごとに届くため、そのまま点にすると点が多すぎます。直前の点から一定以上離れたときだけ点を加えます。

```
extend_stroke(panel, index, q):
    p    = panel.to_content(q)
    step = MIN_POINT_STEP ÷ view.scale        // 画面上の見た目の間隔を一定にする
    last = stroke.points の最後
    if |p − last| < step: return 変更なし
    stroke.points に quantize(p) を加える
    return Changes{ Content(panel) }

quantize(p) = (round(p.x ÷ COORD_QUANTUM) × COORD_QUANTUM, 同様に y)
```

座標を 0.01 単位に丸めるのは、保存した JSON の数値が実行ごとに揺れず、同じ線からは同じ文字列ができるようにするためです（[store-json A10](store-json.md#a10-決まった形で書き出す)）。

### A4. 消しゴム

消しゴムは、前のフレームのマウス位置 `from` から今の位置 `to` までの線分を、半径 r で太らせた形（カプセル）として扱います。点だけで判定すると、速く動かしたときに線を飛び越えてしまうためです。

```
erase(panel, from, to):
    a = panel.to_content(from);  b = panel.to_content(to)
    r = ERASER_RADIUS ÷ view.scale
    box = 線分 ab を r だけ広げた外接長方形
    removed = false
    for stroke in content.strokes を後ろから:
        if stroke の外接長方形が box と重ならない: continue     // 速い足切り
        if stroke が 1 点だけ:
            d = 点と線分の距離(stroke.points[0], a, b)
        else:
            d = min over 隣り合う 2 点 (c, e) of 線分どうしの距離(c, e, a, b)
        if d ≤ r: stroke を消す; removed = true
    return removed なら Changes{ Content(panel) }、そうでなければ変更なし
```

**点と線分の距離**

```
t = clamp(((p − a)・(b − a)) ÷ |b − a|², 0, 1)     // |b − a| = 0 なら t = 0
d = |p − (a + t(b − a))|
```

**線分どうしの距離**：2 本が交わるなら 0。交わらないなら、4 つの端点それぞれと相手の線分との距離の最小値。交わりの判定は、外積の符号で行います。

計算量は、コマ内容の点の総数に比例します。外接長方形による足切りで、離れた線はすぐに飛ばします。

### A5. コマの移動と大きさの変更

**作成**：ドラッグの始点と終点から長方形を作り（左上と右下に並べ直す）、ページの内側に切り詰め、幅と高さを `MIN_PANEL_SIZE` 以上にします。ページの外で始めた場合は `OutsidePage` を返します。

**移動**：

```
frame.origin += delta
frame.origin を [0, page − frame.size] の範囲に切り詰める
```

`view.offset` は枠の左上からの相対位置なので、中身は枠と一緒に動きます。

**大きさの変更**：動かす角の反対側の角を固定します。

```
resize_panel(id, corner, to):
    fixed = corner の反対側の角
    to を ページの内側に切り詰める
    to を fixed から MIN_PANEL_SIZE 以上離れるように切り詰める（角が反対側へ回り込まないように）
    new_frame = fixed と to を対角とする長方形
    view.offset −= new_frame.origin − frame.origin    // 中身のページ上の位置を保つ
    frame = new_frame
    return Changes{ Layout }
```

左や上の角を動かすと枠の左上が動きます。そのぶん `view.offset` を逆に動かすことで、中身はページ上で止まったまま、見える範囲だけが変わります。

### A6. 表示範囲のずらしと拡大縮小

**ずらし**：`view.offset += delta`

**拡大縮小**：マウスの下にある点が動かないようにします。

```
zoom_view(id, factor, anchor):
    p_anchor  = panel.to_content(anchor)                 // 拡大縮小の前に、マウスの下にあるコマ内容の点
    new_scale = clamp(view.scale × factor, VIEW_SCALE_RANGE)
    view.offset = anchor − frame.origin − p_anchor × new_scale
    view.scale  = new_scale
    return Changes{ Layout }
```

変更後も `panel.to_page(p_anchor) = anchor` が成り立ちます。

### A7. 素材の配置と拡大縮小

**配置**：コマの見えている範囲の中央に、コマの 8 割に収まる大きさで置きます。

```
place_asset(panel, hash, natural):
    center = panel.to_content(frame の中心)
    s = min(1, ASSET_FIT_RATIO × frame.width  ÷ (natural.width  × view.scale),
               ASSET_FIT_RATIO × frame.height ÷ (natural.height × view.scale))
    position = center − natural × s ÷ 2
    content.assets に PlacedAsset{ hash, position, natural, scale: s } を加える
    return Changes{ Content(panel), AssetAdded(hash) }
```

**拡大縮小**：反対側の角を固定し、縦横比を保ちます。

```
scale_asset(panel, index, corner, to):
    t     = panel.to_content(to)
    fixed = 素材の corner の反対側の角（コマ内容座標）
    s = max(|t.x − fixed.x| ÷ natural.width, |t.y − fixed.y| ÷ natural.height)
    s = max(s, 0.05)
    position = fixed から、corner の向きに natural × s だけ戻した点
    scale = s
    return Changes{ Content(panel) }
```

**動かす**：`position += delta ÷ view.scale`（delta はページ座標なので、コマ内容座標に直す）

### A8. 読み順の入れ替え

```
reorder_panel(id, toward):
    i = id の位置
    j = toward が「前へ」なら i − 1、「後へ」なら i + 1
    j が範囲外なら 変更なし
    panels[i] と panels[j] を入れ替える
    return Changes{ Layout }
```

## 6. テスト

| 対象 | 確かめること |
| --- | --- |
| A1 | `to_content(to_page(p)) = p`、`to_page(to_content(q)) = q`（誤差 1e-3 以内） |
| A2 | 重なったコマでは、読み順の後ろのコマが選ばれる |
| A3 | 近すぎる点は加わらない。拡大率を変えても画面上の間隔が同じ |
| A4 | 線分をまたいで速く動かしても消える。半径の外の線は残る。1 点だけの線も消せる |
| A5 | ページの外に出ない。最小サイズより小さくならない。左上の角を動かしても中身のページ上の位置が変わらない |
| A6 | 拡大縮小の後も、anchor の下の点が同じ |
| A7 | 縦横比が保たれる。固定した角が動かない |
| R-014 | コマ割りの編集は `Content` を返さない |
