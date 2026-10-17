# vcs-git：git コマンドによる履歴管理

| 項目 | 内容 |
| --- | --- |
| クレート | `crates/vcs-git` |
| 依存してよい先 | domain、ports（外部クレートは使わず、標準ライブラリの `std::process::Command` で git を実行する） |
| 実装するインターフェース | `ports::VersionControlFactory`・`ports::VersionControl`・`ports::FileSource` |
| 対応する要件 | R-040〜R-045・R-050・R-101 |

## 1. 責務

- ports の履歴管理の操作を、git コマンドに置き換えて実行する。
- git の出力を読み取り、ports の型（`Revision`・`IntegrateOutcome` など）に変える。
- git のエラーを、利用者にどう伝えるかで分類する（`VcsError`）。
- 作品の保存形式（JSON）は知らない。

## 2. 構成

```
crates/vcs-git/src/
├── lib.rs          … GitFactory、GitRepository
├── runner.rs       … GitRunner（コマンドの実行とエラーの分類）
├── parse.rs        … git の出力を読む純粋な関数
└── revision.rs     … RevisionFiles（過去の履歴のファイルを読む FileSource）
```

```rust
pub struct GitFactory { git: PathBuf }                  // VersionControlFactory の実装
pub struct GitRepository { runner: GitRunner }          // VersionControl の実装
pub struct RevisionFiles { runner: GitRunner, rev: RevisionId }   // FileSource の実装

struct GitRunner { git: PathBuf, dir: PathBuf }
struct GitOutput { stdout: Vec<u8>, stderr: String, code: i32 }

impl GitRunner {
    /// 成功（終了コード 0）なら出力を返し、失敗なら分類したエラーを返す。
    fn run(&self, action: &str, args: &[&str]) -> Result<GitOutput, VcsError>;
    /// 終了コードを含めて返す（終了コード 1 を「競合あり」などとして扱う操作用）。
    fn run_raw(&self, args: &[&str]) -> Result<GitOutput, VcsError>;
}
```

## 3. 操作と git コマンドの対応

| ports の操作 | git コマンド | アルゴリズム |
| --- | --- | --- |
| `check_available` | `git --version` | [A20](#a20-コマンドの実行とエラーの分類) |
| `init` | `git -c init.defaultBranch=main init` → `.gitattributes` を書く | ― |
| `open` | `git rev-parse --is-inside-work-tree` | ― |
| `download_initial` | `git clone <from> <dest>` | ― |
| `identity` | `git config user.name` / `git config user.email`（未設定なら終了コード 1 → `None`） | ― |
| `set_identity` | `git config --local user.name <名前>` / `git config --local user.email <メール>` | ― |
| `has_changes` | `git status --porcelain=v1 -z`（出力が空でなければ変更あり） | ― |
| `record` | `git add -A` → `git diff --cached --quiet`（終了コード 0 なら `NoChanges`）→ `git commit -m <メッセージ>` → `git rev-parse HEAD` | ― |
| `revisions` | `git log -n <件数> --format=%H%x1f%s%x1f%cI%x1e` | [A21](#a21-履歴一覧の読み取り) |
| `files_at` | `RevisionFiles` を返す（`read` は `git show <rev>:<path>`、`list` は `git ls-tree --name-only <rev> <dir>/`） | ― |
| `restore` | `git restore --source=<rev> --staged --worktree -- .` | ― |
| `lines` | `git branch --format=%(refname:short)` | ― |
| `current_line` | `git branch --show-current` | ― |
| `branch_off` | `git check-ref-format --branch <名前>` → `git switch -c <名前>` | [A22](#a22-履歴系統の名前の検証) |
| `switch_line` | `git switch <名前>` | ― |
| `integrate` | `git merge --no-ff --no-edit <名前>` | [A23](#a23-統合と競合の解決) |
| `conflicts` | `git diff --name-only --diff-filter=U -z` | [A23](#a23-統合と競合の解決) |
| `resolve` | `git checkout --ours/--theirs -- <path>` → `git add -- <path>` | [A23](#a23-統合と競合の解決) |
| `finish_integration` | `git commit --no-edit` → `git rev-parse HEAD` | ― |
| `abort_integration` | `git merge --abort` | ― |
| `upload_target` | `git remote get-url origin`（未設定なら `None`） | ― |
| `set_upload_target` | `git remote add origin <url>`、設定済みなら `git remote set-url origin <url>` | ― |
| `upload` | `git push -u origin <今の履歴系統>` | [A20](#a20-コマンドの実行とエラーの分類) |
| `download_more` | `git fetch origin` → `git merge --no-ff --no-edit origin/<今の履歴系統>` | [A24](#a24-継続ダウンロード) |

`init` で書く `.gitattributes` は次のとおりです。PC 間で改行コードがそろい、PNG が文字データとして扱われるのを防ぎます。

```
*.json text eol=lf
*.png binary
```

## 4. アルゴリズム

### A20. コマンドの実行とエラーの分類

```
run(action, args):
    command = git に次の設定を付けて args を実行する
        -c core.quotepath=false          // 日本語のファイル名をそのまま出力させる
        作業ディレクトリ = dir
        環境変数 LC_ALL=C                 // メッセージを英語にそろえ、分類しやすくする
        環境変数 GIT_TERMINAL_PROMPT=0    // パスワードの入力待ちで止まらないようにする
    起動できない（実行ファイルがない）: return Err(NotInstalled)
    if 終了コード = 0: return Ok(出力)
    return Err(classify(action, stderr))

classify(action, stderr):
    "not a git repository"           を含む → NotARepository
    "Please tell me who you are"     を含む → IdentityMissing
    "[rejected]" または "fetch first" を含む → UploadRejected
    "Could not resolve host"・"unable to access"・"Connection refused" を含む → Network(stderr)
    "Your local changes"・"would be overwritten" を含む → HasChanges
    "already exists"（branch_off のとき） → LineExists
    それ以外 → Failed{ action, detail: stderr }
```

- 認証が必要なアップロード先は、git の資格情報マネージャー（Git for Windows に同梱）に任せます。`GIT_TERMINAL_PROMPT=0` により、資格情報がないときは入力待ちで止まらずにエラーになります。
- `classify` は純粋な関数なので、標準エラー出力の文字列を与えて単体テストします。

### A21. 履歴一覧の読み取り

メッセージに改行や記号が入っても区切りを誤らないよう、区切りに制御文字を使います。

```
revisions(limit):
    out = git log -n limit --format=%H%x1f%s%x1f%cI%x1e
    履歴がまだ 1 つもない（"does not have any commits yet"）: return 空の一覧
    for record in out を \x1e で区切る（空の要素は飛ばす）:
        [id, message, time] = record を前後の空白を除いて \x1f で区切る
        Revision{ id, message, time } を加える
    return 新しい順の一覧
```

### A22. 履歴系統の名前の検証

名前は 2 段階で確かめます。

1. `ports::LineName::parse`（純粋な関数）：空でない、100 文字以内、空白・制御文字・`~ ^ : ? * [ \` を含まない、`-` や `.` で始まらない、`..` と `@{` を含まない、`/` や `.lock` で終わらない。日本語の名前は使える。
2. vcs-git：`git check-ref-format --branch <名前>` で git 自身にも確かめる。

### A23. 統合と競合の解決

```
integrate(from):
    out = run_raw(merge --no-ff --no-edit from)
    if 終了コード = 0:
        出力に "Already up to date" → AlreadyUpToDate
        それ以外 → Integrated
    paths = conflicts()
    if paths が空でない: return Conflicts(paths)
    return Err(classify("integrate", stderr))        // 競合以外の失敗

conflicts():
    out = git diff --name-only --diff-filter=U -z
    return out を NUL で区切った RelPath の一覧

resolve(path, side):
    if side 側にそのファイルがある:                  // git cat-file -e :2:<path>（こちら）/ :3:<path>（あちら）
        git checkout --ours|--theirs -- path
        git add -- path
    else:                                             // 片方でコマを消し、もう片方で中身を変えた場合
        git rm -- path
```

### A24. 継続ダウンロード

`git pull` は、統合の結果の扱いが設定によって変わるため使いません。取得（fetch）と統合（merge）に分けて、A23 と同じ手順で結果を読み取ります。

```
download_more():
    upload_target() が None なら Err(NoUploadTarget)
    git fetch origin
    line = current_line()
    if origin/<line> が存在しない: return AlreadyUpToDate   // まだ誰もアップロードしていない
    return integrate("origin/<line>")
```

## 5. テスト

| 確かめること | 方法 |
| --- | --- |
| `classify`・A21・A22 の読み取り | 文字列を与える単体テスト |
| 履歴更新・一覧・過去のファイル・戻す | 一時フォルダに本物のリポジトリを作る |
| コマ割りとコマ内容を別々の履歴系統で変えると、競合せずに統合できる | 同上（`layout.json` と `panels/<id>.json` を別の履歴系統で変える） |
| 同じファイルを両方で変えると `Conflicts` になり、`resolve` → `finish_integration` で完了できる | 同上 |
| 片方でファイルを消し、もう片方で変えた競合を解決できる | 同上 |
| アップロード・初回ダウンロード・継続ダウンロード | 一時フォルダに「アップロード先」の bare リポジトリを作り、2 つの作業フォルダから操作する |
