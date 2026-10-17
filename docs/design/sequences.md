# シーケンス図

主な操作で、どの部品がどの順番で呼ばれるかを示します。部品の詳細は [modules/](modules/) にあります。

図の参加者は次のとおりです。

| 参加者 | クレート | 種類 |
| --- | --- | --- |
| UI | ui-egui | 画面 |
| Tool | ui-egui（`Tool` の実装） | 道具 |
| Jobs | ui-egui（`JobRunner`） | 作業スレッド |
| WS / Session / Assets | app（`Workspace`・`Session`・`AssetService`） | ユースケース |
| Work | domain | データと純粋な処理 |
| Repo | store-json（`WorkRepository` の実装） | アダプター |
| Files | fs（`FileSink` の実装） | アダプター |
| Vcs | vcs-git（`VersionControl` の実装） | アダプター |
| Lib | fs（`AssetLibrary` の実装） | アダプター |
| Ex | exchange-iroh（`AssetExchange` の実装） | アダプター |

app から右側の参加者への呼び出しは、すべて ports のトレイトを通ります。

## 目次

| 図 | 操作 | 要件 |
| --- | --- | --- |
| [S1](#s1-起動と新しい作品) | 起動と新しい作品 | R-050・R-101 |
| [S2](#s2-線を引く) | 線を引く | R-001 |
| [S3](#s3-線を消す) | 線を消す | R-002 |
| [S4](#s4-コマを動かして保存する) | コマを動かして保存する | R-011・R-014・R-051 |
| [S5](#s5-履歴更新) | 履歴更新 | R-040 |
| [S6](#s6-過去の状態を見る) | 過去の状態を見る | R-041・R-042 |
| [S7](#s7-この状態に戻す) | この状態に戻す | R-042 |
| [S8](#s8-分岐と切り替え) | 分岐と切り替え | R-043 |
| [S9](#s9-統合競合あり) | 統合（競合あり） | R-044 |
| [S10](#s10-素材を公開する) | 素材を公開する | R-030 |
| [S11](#s11-素材を受け取る) | 素材を受け取る | R-031・R-032 |
| [S12](#s12-素材を貼って保存する) | 素材を貼って保存する | R-020・R-022 |
| [S13](#s13-アップロードと継続ダウンロード) | アップロードと継続ダウンロード | R-045 |
| [S14](#s14-初回ダウンロード) | 初回ダウンロード | R-045 |

## S1. 起動と新しい作品

```mermaid
sequenceDiagram
    actor User as 利用者
    participant UI
    participant WS as Workspace
    participant Files
    participant Repo
    participant Vcs
    UI->>WS: check_environment()
    WS->>Vcs: check_available()（git --version）
    Vcs-->>WS: 版の文字列
    WS-->>UI: Ok（失敗なら Git の案内画面）
    User->>UI: 作品 → 新規作成、フォルダを選ぶ
    UI->>WS: create_work(dir)
    WS->>Files: create(dir)
    WS->>WS: Work::empty()
    WS->>Repo: save_all(files, work)
    Repo->>Files: write(work.json / layout.json)
    WS->>Vcs: init(dir)（git init、.gitattributes）
    WS-->>UI: Session
    UI->>UI: 空のページを描く
```

## S2. 線を引く

```mermaid
sequenceDiagram
    actor User as 利用者
    participant UI
    participant Tool as PenTool
    participant Session
    participant Work
    User->>UI: コマの中でマウスを押す
    UI->>UI: 画面座標 → ページ座標（Viewport）
    UI->>Tool: on_pointer(Down{at})
    Tool->>Tool: panel_at(at) でコマを探す
    Tool-->>UI: StartStroke{panel, at}
    UI->>Session: edit(StartStroke)
    Session->>Work: start_stroke(panel, at)
    Work-->>Session: (index, Changes{Content})
    Session->>Session: active_stroke を覚え、dirty に加える
    loop マウスを動かすたび
        User->>UI: マウスを動かす
        UI->>Tool: on_pointer(Move{at})
        Tool-->>UI: ExtendStroke{at}
        UI->>Session: edit(ExtendStroke)
        Session->>Work: extend_stroke(panel, index, at)（近すぎる点は加えない）
    end
    User->>UI: マウスを離す
    UI->>Tool: on_pointer(Up)
    Tool-->>UI: EndStroke
    UI->>Session: edit(EndStroke)
    UI->>UI: 次のフレームで描き直す（タイトルに「*」）
```

## S3. 線を消す

```mermaid
sequenceDiagram
    actor User as 利用者
    participant UI
    participant Tool as EraserTool
    participant Session
    participant Work
    User->>UI: マウスを押す
    UI->>Tool: on_pointer(Down{at})
    Tool->>Tool: last = at
    loop マウスを動かすたび
        User->>UI: マウスを動かす
        UI->>Tool: on_pointer(Move{at})
        Tool-->>UI: Erase{panel, from: last, to: at}
        UI->>Session: edit(Erase)
        Session->>Work: erase(panel, from, to)
        Work->>Work: 消しゴムの通り道（カプセル）に触れた線を消す
        Work-->>Session: Changes{Content}（消えた線があれば）
        Tool->>Tool: last = at
    end
```

## S4. コマを動かして保存する

```mermaid
sequenceDiagram
    actor User as 利用者
    participant UI
    participant Tool as PanelTool
    participant Session
    participant Work
    participant Repo
    participant Files
    User->>UI: コマをドラッグ
    UI->>Tool: on_pointer(Down / Move)
    Tool-->>UI: MovePanel{panel, delta}
    UI->>Session: edit(MovePanel)
    Session->>Work: move_panel(panel, delta)
    Work-->>Session: Changes{Layout}（コマ内容は含まない）
    User->>UI: Ctrl+S
    UI->>Session: save()
    Session->>Repo: save(files, work, dirty = {Layout})
    Repo->>Files: write(layout.json)
    Note over Repo,Files: panels/*.json は書かない（R-014）
    Session->>Session: dirty を空にする
```

## S5. 履歴更新

```mermaid
sequenceDiagram
    actor User as 利用者
    participant UI
    participant Session
    participant Repo
    participant Vcs
    User->>UI: メッセージを書いて「履歴更新」
    UI->>Session: record(message)
    Session->>Repo: save(...)（変更があれば）
    Session->>Vcs: identity()
    alt 作者が未設定
        Vcs-->>Session: None
        Session-->>UI: Err(IdentityRequired)
        UI->>User: 作者名とメールアドレスを尋ねる
        User->>UI: 入力
        UI->>Session: set_identity(identity)
        Session->>Vcs: set_identity（git config --local）
        UI->>Session: record(message)（やり直し）
    end
    Session->>Vcs: record(message)
    Vcs->>Vcs: git add -A → git diff --cached --quiet → git commit
    Vcs-->>Session: Recorded(id) または NoChanges
    Session-->>UI: 結果
    UI->>Session: revisions(50)
    UI->>UI: 履歴一覧を描き直す
```

## S6. 過去の状態を見る

vcs-git と store-json は互いを知りません。app が、vcs-git の `FileSource`（過去のファイルを読む手段）を store-json に渡して組み合わせます。

```mermaid
sequenceDiagram
    actor User as 利用者
    participant UI
    participant Session
    participant Vcs
    participant Rev as RevisionFiles
    participant Repo
    User->>UI: 履歴一覧の行をクリック
    UI->>Session: view(revision)
    Session->>Vcs: files_at(revision.id)
    Vcs-->>Session: RevisionFiles（FileSource）
    Session->>Repo: load(revision_files)
    Repo->>Rev: read(work.json / layout.json / panels/*.json)
    Rev->>Rev: git show <rev>:<path>
    Repo-->>Session: その時点の Work
    Session->>Session: mode = Viewing{revision, work}
    UI->>UI: 「過去の状態を表示中」と表示し、編集を止める
```

## S7. この状態に戻す

```mermaid
sequenceDiagram
    actor User as 利用者
    participant UI
    participant Session
    participant Vcs
    participant Repo
    participant Files
    User->>UI: 「この状態に戻す」
    UI->>Session: restore()
    Session->>Repo: save(...)（今の変更を保存）
    Session->>Vcs: restore(revision.id)（git restore --source）
    Session->>Repo: load(files)
    Repo->>Files: read(...)
    Session->>Session: mode = Editing
    Session->>Vcs: record("「…」の状態に戻す")
    Note over Session,Vcs: それまでの履歴はすべて残る
```

## S8. 分岐と切り替え

```mermaid
sequenceDiagram
    actor User as 利用者
    participant UI
    participant Session
    participant Vcs
    participant Repo
    User->>UI: 「分岐」、名前を入力
    UI->>Session: branch_off(name)
    Session->>Session: LineName::parse(name)
    Session->>Repo: save(...)
    Session->>Vcs: branch_off(name)（git switch -c）
    User->>UI: 履歴系統の一覧から選ぶ
    UI->>Session: switch_line(name)
    Session->>Repo: save(...)
    Session->>Vcs: has_changes()
    alt 履歴更新していない変更がある
        Session-->>UI: Err(UnrecordedChanges)
        UI->>User: 先に履歴更新するよう促す
    else 変更なし
        Session->>Vcs: switch_line(name)（git switch）
        Session->>Repo: load(files)
        UI->>UI: キャンバスを描き直す
    end
```

## S9. 統合（競合あり）

```mermaid
sequenceDiagram
    actor User as 利用者
    participant UI
    participant Session
    participant Vcs
    participant Repo
    User->>UI: 「統合」、取り込む履歴系統を選ぶ
    UI->>Session: integrate(from)
    Session->>Vcs: has_changes()（変更があればエラー）
    Session->>Vcs: integrate(from)（git merge --no-ff）
    Vcs->>Vcs: git diff --diff-filter=U で競合を調べる
    Vcs-->>Session: Conflicts([layout.json])
    Session->>Session: mode = Integrating
    Session-->>UI: Conflicts
    UI->>User: 競合したファイルの一覧（こちら／あちら）
    User->>UI: layout.json は「あちら」
    UI->>Session: resolve(layout.json, Theirs)
    Session->>Vcs: resolve（git checkout --theirs → git add）
    User->>UI: 「統合を完了」
    UI->>Session: finish_integration()
    Session->>Vcs: finish_integration()（git commit --no-edit）
    Session->>Repo: load(files)
    Session->>Session: mode = Editing
    Note over Session,Vcs: コマ割りとコマ内容を別々に変えただけなら、競合せずに Integrated が返る
```

## S10. 素材を公開する

```mermaid
sequenceDiagram
    actor User as 利用者
    participant UI
    participant Jobs
    participant Assets as AssetService
    participant Lib
    participant Ex
    User->>UI: 素材 → 公開、PNG を選ぶ
    UI->>UI: ファイルを読む
    UI->>Assets: prepare_publish(bytes)
    Assets-->>UI: PublishJob
    UI->>Jobs: submit(PublishJob)
    Note over UI: 状態表示「公開中…」
    Jobs->>Lib: import(bytes)（PNG の検査、ハッシュ値で保存）
    Lib-->>Jobs: AssetInfo{hash}
    Jobs->>Ex: publish(hash, bytes)
    Ex->>Ex: 保管場所に加え、チケットを作る
    Ex-->>Jobs: AssetTicket
    Jobs-->>UI: Published(ticket)
    UI->>User: 素材 ID を表示（コピーボタン）
```

## S11. 素材を受け取る

```mermaid
sequenceDiagram
    actor User as 利用者
    participant UI
    participant Jobs
    participant Assets as AssetService
    participant Ex
    participant Lib
    User->>UI: 素材 → 受け取る、素材 ID を貼り付ける
    UI->>Assets: prepare_fetch(text)
    Assets->>Ex: parse_ticket(text)
    Assets-->>UI: FetchJob
    UI->>Jobs: submit(FetchJob)
    Jobs->>Ex: fetch(ticket)
    Ex->>Ex: 相手のノードにつなぎ、受信しながら BLAKE3 で検証
    Ex-->>Jobs: bytes
    Jobs->>Jobs: AssetHash::of(bytes) = ticket.hash を確かめる
    Jobs->>Lib: import(bytes)
    Lib-->>Jobs: AssetInfo
    Jobs-->>UI: Fetched(info)
    UI->>User: 「素材を受け取りました」（素材一覧に入る）
```

## S12. 素材を貼って保存する

```mermaid
sequenceDiagram
    actor User as 利用者
    participant UI
    participant Session
    participant Lib
    participant Work
    participant Repo
    participant Files
    User->>UI: コマを選び、素材一覧で「貼る」
    UI->>Session: edit(PlaceAsset{panel, hash})
    Session->>Lib: info(hash)
    Lib-->>Session: AssetInfo{natural}
    Session->>Work: place_asset(panel, hash, natural)
    Work-->>Session: Changes{Content(panel), AssetAdded(hash)}
    User->>UI: Ctrl+S
    UI->>Session: save()
    Session->>Repo: asset_path(hash)
    Session->>Files: read(assets/<hash>.png)
    alt まだ作品フォルダにない
        Session->>Lib: read(hash)
        Session->>Files: write(assets/<hash>.png)
    end
    Session->>Repo: save(files, work, dirty)
    Repo->>Files: write(panels/<id>.json)
    Note over Session,Files: 素材を先に置いてから、コマ内容を書く
```

## S13. アップロードと継続ダウンロード

```mermaid
sequenceDiagram
    actor User as 利用者
    participant UI
    participant Jobs
    participant Session
    participant Vcs
    participant Repo
    User->>UI: 「アップロード」
    UI->>Session: prepare_upload()（保存まで済ませる）
    Session-->>UI: UploadJob
    UI->>Jobs: submit(UploadJob)
    Note over UI: 編集を止め、「アップロード中…」
    Jobs->>Vcs: upload()（git push -u origin）
    alt 先に新しい履歴がある
        Vcs-->>Jobs: Err(UploadRejected)
        Jobs-->>UI: Uploaded(Err)
        UI->>User: 先に継続ダウンロードするよう案内
    else 成功
        Jobs-->>UI: Uploaded(Ok)
    end
    User->>UI: 「継続ダウンロード」
    UI->>Session: prepare_download_more()（変更があればエラー）
    UI->>Jobs: submit(DownloadMoreJob)
    Jobs->>Vcs: download_more()（git fetch → git merge）
    Vcs-->>Jobs: IntegrateOutcome
    Jobs-->>UI: DownloadedMore(outcome)
    UI->>Session: finish_download_more(outcome)
    Session->>Repo: load(files)
    Note over UI,Session: 競合なら S9 と同じく Integrating になる
```

## S14. 初回ダウンロード

```mermaid
sequenceDiagram
    actor User as 利用者
    participant UI
    participant Jobs
    participant WS as Workspace
    participant VF as VcsFactory
    participant Files
    participant Repo
    User->>UI: 作品 → 初回ダウンロード、場所と保存先を入力
    UI->>WS: prepare_download_initial(from, dest)
    WS-->>UI: InitialDownloadJob
    UI->>Jobs: submit(InitialDownloadJob)
    Jobs->>VF: download_initial(from, dest)（git clone）
    VF-->>Jobs: VersionControl
    Jobs->>Files: open(dest)
    Jobs->>Repo: load(files)
    Jobs-->>UI: InitialDownloaded(Session)
    UI->>UI: 作品を表示（素材は作品フォルダの assets/ から読む）
```
