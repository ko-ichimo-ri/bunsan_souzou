# testkit：テスト用の実装

| 項目 | 内容 |
| --- | --- |
| クレート | `crates/testkit`（`dev-dependencies` としてだけ使う） |
| 依存してよい先 | domain、ports |
| 実装するインターフェース | ports のすべてのトレイト（`WorkRepository` を除く） |

## 1. 責務

- ports のインターフェースを、メモリ上で動く偽物として実装する。
- app のテストを、ファイル・git・通信なしで、速く・決まった結果で動かせるようにする。
- テストで確かめたいこと（書いた順番、呼ばれた操作）を記録して取り出せるようにする。

## 2. 実装

| 型 | 実装するトレイト | 動き | 記録・設定 |
| --- | --- | --- | --- |
| `MemoryFileAccess` | `FileAccess` | フォルダごとに `MemoryFiles` を作る | ― |
| `MemoryFiles` | `FileSource`・`FileSink` | `BTreeMap<RelPath, Vec<u8>>` に読み書きする | 書いた・消したパスを順番に記録する（`log()`） |
| `FakeVcsFactory` | `VersionControlFactory` | `FakeVcs` を作る | `check_available` の結果を設定できる |
| `FakeVcs` | `VersionControl` | 履歴を `Vec` で持つ。`record` は `MemoryFiles` の中身を写して履歴にする | 作者の有無、`integrate` が返す競合、`upload` の失敗などを設定できる。呼ばれた操作を記録する |
| `MemoryAssetLibrary` | `AssetLibrary` | `BTreeMap<AssetHash, Vec<u8>>` に保存する。PNG の検査は先頭 8 バイトの署名だけで行う | 画素数を設定できる |
| `LoopbackExchange` | `AssetExchange` | 公開した素材を同じプロセスの中で受け取れる。素材 ID は `loopback:<hash>` | わざと違うデータを返す・つながらない、を設定できる |
| `SequentialIdSource` | `IdSource` | `00000000-…-000000000001` から順に ID を返す | ― |
| `TestKit` | ― | 上の偽物をまとめて作り、それらを使う `Workspace` を返す | 作品フォルダごとの `MemoryFiles` を取り出せる（`files(dir)`） |

`WorkRepository` には偽物を作らず、本物の `store_json::JsonWorkRepository` を `MemoryFiles` と組み合わせて使います。保存形式は速く、決まった結果で動くためです。

## 3. 使い方の例

```rust
#[test]
fn コマ割りだけを変えるとコマ内容のファイルは書かれない() {
    let kit = TestKit::new();                         // 偽物をまとめて作る
    let mut session = kit.workspace().create_work(Path::new("w")).unwrap();
    session.edit(EditCommand::AddPanel { frame: rect(100, 100, 400, 300) }).unwrap();
    session.save().unwrap();
    kit.files("w").clear_log();

    let id = session.work().layout.panels[0].id;
    session.edit(EditCommand::MovePanel { panel: id, delta: point(10, 0) }).unwrap();
    session.save().unwrap();

    assert_eq!(kit.files("w").log(), vec![Written("layout.json".into())]);
}
```
