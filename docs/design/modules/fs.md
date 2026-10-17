# fs：ファイルの読み書きと素材置き場

| 項目 | 内容 |
| --- | --- |
| クレート | `crates/fs` |
| 依存してよい先 | domain、ports、image、dirs |
| 実装するインターフェース | `ports::FileAccess`・`ports::FileSource`・`ports::FileSink`・`ports::AssetLibrary` |
| 対応する要件 | R-020・R-022・R-030・R-031・R-050・R-051 |

## 1. 責務

- 作業フォルダのファイルを、原子的に読み書きする。
- 利用者ごとの素材置き場を管理する（PNG の検査、ハッシュ値での保存、一覧）。
- JSON の形式や git のことは知らない。

## 2. 型と関数

### 2.1 作業フォルダ

```rust
/// FileAccess の実装。
pub struct FsFileAccess;

/// 1 つの作品フォルダ。FileSource と FileSink の実装。
pub struct FsWorkDir { root: PathBuf }
```

| 関数 | 内容 | アルゴリズム |
| --- | --- | --- |
| `FsFileAccess::open(&self, dir: &Path) -> Result<Arc<dyn FileSink>, FileError>` | フォルダが存在すれば `FsWorkDir` を返す | ― |
| `FsFileAccess::create(&self, dir: &Path) -> Result<Arc<dyn FileSink>, FileError>` | フォルダがない・空なら作って返す。空でなければ `NotEmpty` | ― |
| `FsWorkDir::read(&self, path: &RelPath) -> Result<Option<Vec<u8>>, FileError>` | `root/path` を読む。なければ `None` | ― |
| `FsWorkDir::list(&self, dir: &RelPath) -> Result<Vec<RelPath>, FileError>` | `root/dir` 直下のファイルを名前順に返す | ― |
| `FsWorkDir::write(&self, path: &RelPath, bytes: &[u8]) -> Result<(), FileError>` | 原子的に書く。途中のディレクトリは作る | [A18](#a18-原子的な書き込み) |
| `FsWorkDir::remove(&self, path: &RelPath) -> Result<(), FileError>` | 消す。なければ何もしない | ― |

`RelPath` は `..` や絶対パスを含まないことが保証されているので、`root` の外のファイルに触れることはありません。

### 2.2 素材置き場

```rust
/// AssetLibrary の実装。
pub struct FsAssetLibrary { root: PathBuf }   // Windows では %APPDATA%\bunsan_souzou\assets
```

| 関数 | 内容 | アルゴリズム |
| --- | --- | --- |
| `FsAssetLibrary::open_default() -> Result<FsAssetLibrary, LibraryError>` | 利用者ごとのデータフォルダ（`dirs::data_dir()`）の下に置き場を作って開く | ― |
| `FsAssetLibrary::open(root: PathBuf) -> Result<FsAssetLibrary, LibraryError>` | 指定したフォルダを置き場にする（テスト用） | ― |
| `import(&self, bytes: &[u8]) -> Result<AssetInfo, LibraryError>` | 検査してから保存する | [A19](#a19-素材の取り込み) |
| `list(&self) -> Result<Vec<AssetInfo>, LibraryError>` | `*.png` の一覧。画素数は画像の先頭部分だけを読んで求める | ― |
| `info(&self, hash: &AssetHash) -> Result<AssetInfo, LibraryError>` | 1 つの素材の情報 | ― |
| `read(&self, hash: &AssetHash) -> Result<Vec<u8>, LibraryError>` | バイト列を読む | ― |

## 3. アルゴリズム

### A18. 原子的な書き込み

書き込みの途中でアプリケーションが止まっても、ファイルが壊れないようにします（構想 NF-05）。

```
write(path, bytes):
    target = root / path
    target の親ディレクトリを作る
    temp = target と同じディレクトリの ".<ファイル名>.tmp-<乱数>"
    temp に bytes を書く
    temp を flush し、ディスクへの書き込みを待つ（sync_all）
    temp を target に名前変更する（rename）
    失敗したら temp を消して、エラーを返す
```

- 名前変更（rename）は、同じドライブの中では一度に置き換わります。読み手からは、古い内容か新しい内容のどちらかしか見えません。
- Rust の `std::fs::rename` は、Windows でも既存のファイルを置き換えます。
- 一時ファイルを同じディレクトリに作るのは、別のドライブをまたぐと名前変更が一度に置き換わらないためです。

### A19. 素材の取り込み

P2P で受け取った素材は、信頼できない相手からのデータです。メモリ安全な Rust の実装（image クレート）で、PNG として正しいかを確かめてから保存します（[調査レポート](../../research/p2p-safety.md) 4.3）。

```
import(bytes):
    if bytes.len() > 32 MB: return Err(TooLarge)
    format = 先頭のバイトから画像の形式を判定する
    if format が PNG でない: return Err(NotPng)
    image = PNG として最後まで読み込む（壊れていれば Err(NotPng)）
    hash = AssetHash::of(bytes)
    path = root / "<hash>.png"
    if path が存在しない: A18 の方法で bytes を書く       // 同じ素材は 1 つだけ保存する
    return AssetInfo{ hash, natural: (image.width, image.height) }
```

- 保存するのは**受け取ったバイト列そのもの**です。読み込み直した画像を書き出すと、バイト列が変わってハッシュ値が変わってしまうためです。
- 画像を最後まで読み込むのは、先頭だけ正しく中身が壊れたデータを置き場に入れないためです。

## 4. テスト

| 確かめること |
| --- |
| 書き込みの途中で失敗させても、元のファイルが残り、一時ファイルが消えている |
| 空でないフォルダに `create` すると `NotEmpty` |
| PNG 以外・壊れた PNG・32 MB を超えるデータは取り込まれない |
| 同じ素材を 2 回取り込んでも、ファイルは 1 つで、同じハッシュ値が返る |
| `list` が、取り込んだ素材の画素数を正しく返す |
