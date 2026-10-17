# ports：インターフェース

| 項目 | 内容 |
| --- | --- |
| クレート | `crates/ports` |
| 依存してよい先 | domain |
| 対応する要件 | R-014・R-020〜R-022・R-030〜R-032・R-040〜R-045・R-050・R-051・R-101 |

## 1. 責務

- 中心部（app）が外の世界に頼むことを、**トレイト**として定義する。
- トレイトのメソッドで受け渡すデータの型と、エラーの型を定義する。
- 実装は持たない。実装はアダプターのクレートにある（2 節）。

すべてのトレイトは `Send + Sync` とし、メソッドは**処理が終わるまで待つ形（同期）**で定義します（[全体構成 6 節](../architecture.md#6-スレッドの扱い)）。

## 2. インターフェースと実装の対応

| トレイト | 役割 | 本物の実装 | テスト用の実装（testkit） |
| --- | --- | --- | --- |
| `FileAccess` | 作品フォルダを開く・作る | `fs::FsFileAccess` | `MemoryFileAccess` |
| `FileSource` | 作品のファイルを読む | `fs::FsWorkDir`、`vcs_git::RevisionFiles` | `MemoryFiles` |
| `FileSink` | 作品のファイルを書く・消す | `fs::FsWorkDir` | `MemoryFiles` |
| `WorkRepository` | 作品のデータとファイルの変換（保存形式） | `store_json::JsonWorkRepository` | ―（本物を使う。ファイル操作は `MemoryFiles` で置き換わる） |
| `VersionControlFactory` | 履歴管理を始める・開く・初回ダウンロード | `vcs_git::GitFactory` | `FakeVcsFactory` |
| `VersionControl` | 作品フォルダの履歴管理 | `vcs_git::GitRepository` | `FakeVcs` |
| `AssetLibrary` | 手元の素材置き場 | `fs::FsAssetLibrary` | `MemoryAssetLibrary` |
| `AssetExchange` | 素材の P2P 受け渡し | `exchange_iroh::IrohAssetExchange` | `LoopbackExchange` |
| `IdSource` | 新しいコマ ID を作る | `RandomIdSource`（bunsan-souzou） | `SequentialIdSource` |

## 3. ファイルの読み書き

作品のファイルを、置き場所（作業フォルダか過去の履歴か）から切り離して扱うためのトレイトです。保存形式（store-json）は、ファイルがどこにあるかを知りません。

```rust
/// 作品フォルダからの相対パス（区切りは "/"）。".." や絶対パスは作れない。
pub struct RelPath(String);

pub trait FileSource: Send + Sync {
    /// ファイルを読む。存在しなければ None。
    fn read(&self, path: &RelPath) -> Result<Option<Vec<u8>>, FileError>;
    /// ディレクトリ直下のファイルの一覧。
    fn list(&self, dir: &RelPath) -> Result<Vec<RelPath>, FileError>;
}

pub trait FileSink: FileSource {
    /// ファイルを書く。途中で止まっても、古い内容か新しい内容のどちらかが残る（原子的）。
    fn write(&self, path: &RelPath, bytes: &[u8]) -> Result<(), FileError>;
    /// ファイルを消す。存在しなければ何もしない。
    fn remove(&self, path: &RelPath) -> Result<(), FileError>;
}

pub trait FileAccess: Send + Sync {
    /// 既存の作品フォルダを開く。
    fn open(&self, dir: &Path) -> Result<Arc<dyn FileSink>, FileError>;
    /// 空のフォルダを作品フォルダとして使う（空でなければエラー）。
    fn create(&self, dir: &Path) -> Result<Arc<dyn FileSink>, FileError>;
}

pub enum FileError {
    NotFound,
    NotEmpty,           // 新規作成で、フォルダが空でない
    PermissionDenied,
    Io(String),
}
```

## 4. 保存形式

```rust
pub trait WorkRepository: Send + Sync {
    /// ファイルから作品を読み込む。
    fn load(&self, src: &dyn FileSource) -> Result<Work, StoreError>;
    /// 作品の全ファイルを書く（新規作成のとき）。
    fn save_all(&self, dst: &dyn FileSink, work: &Work) -> Result<(), StoreError>;
    /// changes に挙がったファイルだけを書く・消す（R-014）。
    fn save(&self, dst: &dyn FileSink, work: &Work, changes: &Changes) -> Result<(), StoreError>;
    /// 素材のファイルを置く場所（作品フォルダからの相対パス）。
    fn asset_path(&self, hash: &AssetHash) -> RelPath;
}

pub enum StoreError {
    NotAWork,                      // 作品の情報ファイルがない
    UnsupportedVersion(u32),       // 新しすぎる形式
    Broken { path: RelPath, reason: String },   // 壊れた・不正なファイル
    File(FileError),
}
```

## 5. 履歴管理

```rust
pub trait VersionControlFactory: Send + Sync {
    /// 履歴管理の道具が使えるかを確かめる（R-101）。
    fn check_available(&self) -> Result<String, VcsError>;   // 版の文字列
    /// フォルダで履歴管理を始める。
    fn init(&self, dir: &Path) -> Result<Arc<dyn VersionControl>, VcsError>;
    /// 履歴管理されているフォルダを開く。
    fn open(&self, dir: &Path) -> Result<Arc<dyn VersionControl>, VcsError>;
    /// アップロード先から作品を丸ごと取得する（初回ダウンロード）。
    fn download_initial(&self, from: &RemoteUrl, dest: &Path) -> Result<Arc<dyn VersionControl>, VcsError>;
}

pub trait VersionControl: Send + Sync {
    // 作者
    fn identity(&self) -> Result<Option<Identity>, VcsError>;
    fn set_identity(&self, identity: &Identity) -> Result<(), VcsError>;

    // 履歴更新と履歴（R-040〜R-042）
    fn has_changes(&self) -> Result<bool, VcsError>;
    fn record(&self, message: &str) -> Result<RecordOutcome, VcsError>;
    fn revisions(&self, limit: usize) -> Result<Vec<Revision>, VcsError>;
    fn files_at(&self, rev: &RevisionId) -> Result<Arc<dyn FileSource>, VcsError>;
    fn restore(&self, rev: &RevisionId) -> Result<(), VcsError>;   // 作業フォルダを rev の状態にする（履歴は作らない）

    // 履歴系統（R-043・R-044）
    fn lines(&self) -> Result<Vec<LineName>, VcsError>;
    fn current_line(&self) -> Result<LineName, VcsError>;
    fn branch_off(&self, name: &LineName) -> Result<(), VcsError>;   // 作って切り替える
    fn switch_line(&self, name: &LineName) -> Result<(), VcsError>;
    fn integrate(&self, from: &LineName) -> Result<IntegrateOutcome, VcsError>;
    fn conflicts(&self) -> Result<Vec<RelPath>, VcsError>;
    fn resolve(&self, path: &RelPath, side: Side) -> Result<(), VcsError>;
    fn finish_integration(&self) -> Result<RevisionId, VcsError>;
    fn abort_integration(&self) -> Result<(), VcsError>;

    // アップロードとダウンロード（R-045）
    fn upload_target(&self) -> Result<Option<RemoteUrl>, VcsError>;
    fn set_upload_target(&self, to: &RemoteUrl) -> Result<(), VcsError>;
    fn upload(&self) -> Result<(), VcsError>;
    fn download_more(&self) -> Result<IntegrateOutcome, VcsError>;
}

pub struct Identity { pub name: String, pub email: String }
pub struct RevisionId(String);
pub struct Revision { pub id: RevisionId, pub message: String, pub time: String /* ISO 8601 */ }
/// 履歴系統の名前。使える文字だけでできていることを、作るときに確かめる。
pub struct LineName(String);
pub struct RemoteUrl(String);   // 共有フォルダのパスか URL
pub enum Side { Ours, Theirs }  // こちら／あちら

pub enum RecordOutcome { Recorded(RevisionId), NoChanges }
pub enum IntegrateOutcome { Integrated, AlreadyUpToDate, Conflicts(Vec<RelPath>) }

pub enum VcsError {
    NotInstalled,               // R-101
    NotARepository,
    IdentityMissing,            // 作者名・メールアドレスが未設定
    InvalidLineName(String),
    LineExists(LineName),
    HasChanges,                 // 履歴更新していない変更があって切り替えられない
    NoUploadTarget,
    UploadRejected,             // 先に継続ダウンロードが必要
    Network(String),
    Failed { action: String, detail: String },   // その他（detail に道具の出力）
}
```

## 6. 素材置き場

```rust
pub trait AssetLibrary: Send + Sync {
    /// 素材を取り込む。PNG であることを確かめ、ハッシュ値で保存する。同じ素材を何度取り込んでもよい。
    fn import(&self, bytes: &[u8]) -> Result<AssetInfo, LibraryError>;
    fn list(&self) -> Result<Vec<AssetInfo>, LibraryError>;
    fn read(&self, hash: &AssetHash) -> Result<Vec<u8>, LibraryError>;
}

pub struct AssetInfo { pub hash: AssetHash, pub natural: Size }

pub enum LibraryError {
    NotPng,
    TooLarge { bytes: u64 },    // 上限は 32 MB
    NotFound(AssetHash),
    Io(String),
}
```

## 7. 素材の受け渡し（P2P）

```rust
pub trait AssetExchange: Send + Sync {
    /// 素材を公開し、相手に伝える素材 ID を返す（R-030）。アプリケーションが動いている間、相手が受け取れる。
    fn publish(&self, hash: &AssetHash, bytes: &[u8]) -> Result<AssetTicket, ExchangeError>;
    /// 素材 ID の文字列を読み取る。形式は実装ごとに決まる。
    fn parse_ticket(&self, text: &str) -> Result<AssetTicket, ExchangeError>;
    /// 素材を受け取る。ticket.hash と一致することを確かめてから返す（R-031・R-032）。
    fn fetch(&self, ticket: &AssetTicket) -> Result<Vec<u8>, ExchangeError>;
}

pub struct AssetTicket { pub text: String, pub hash: AssetHash }

pub enum ExchangeError {
    InvalidTicket,
    Unreachable,        // 公開側が起動していない・つながらない
    HashMismatch,       // 受け取ったデータがハッシュ値と一致しない
    Network(String),
}
```

## 8. ID

```rust
pub trait IdSource: Send + Sync {
    fn new_panel_id(&self) -> PanelId;
}
```

ID の作り方をトレイトにするのは、テストで決まった ID を使えるようにするためです（testkit の `SequentialIdSource`）。
