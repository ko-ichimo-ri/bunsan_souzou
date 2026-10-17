# exchange-iroh：Iroh による素材の受け渡し

| 項目 | 内容 |
| --- | --- |
| クレート | `crates/exchange-iroh` |
| 依存してよい先 | domain、ports、iroh、iroh-blobs、tokio |
| 実装するインターフェース | `ports::AssetExchange` |
| 対応する要件 | R-030〜R-032 |

## 1. 責務

- 素材を公開し、素材 ID（Iroh のチケット）を作る。
- 素材 ID から接続して素材を受け取り、ハッシュ値で照合する。
- Iroh の非同期処理（tokio）を内部に閉じ込め、外には同期の形で見せる（[全体構成 6 節](../architecture.md#6-スレッドの扱い)）。

Iroh・iroh-blobs の具体的な API は版によって変わるため、この文書は外から見た振る舞いとアルゴリズムを定めます。関数名などの細部は、検証用プログラム（M0）で確かめてから追記します。

## 2. 型と関数

```rust
/// AssetExchange の実装。アプリケーションが動いている間、Iroh のノードを動かし続ける。
pub struct IrohAssetExchange {
    runtime: tokio::runtime::Runtime,   // Iroh を動かす非同期の実行環境（このクレートの中だけで使う）
    node: Node,                         // 接続口（endpoint）・素材の保管場所（blob store）・受け付け（router）
}
```

| 関数 | 内容 | アルゴリズム |
| --- | --- | --- |
| `IrohAssetExchange::start() -> Result<IrohAssetExchange, ExchangeError>` | 実行環境を作り、ノードを起動する。保管場所はメモリ上に作る | ― |
| `publish(&self, hash: &AssetHash, bytes: &[u8]) -> Result<AssetTicket, ExchangeError>` | 公開して素材 ID を返す | [A25](#a25-公開) |
| `parse_ticket(&self, text: &str) -> Result<AssetTicket, ExchangeError>` | 素材 ID の文字列を読み取る | [A26](#a26-受け取り) |
| `fetch(&self, ticket: &AssetTicket) -> Result<Vec<u8>, ExchangeError>` | 受け取って照合する | [A26](#a26-受け取り) |
| `Drop` | ノードを止め、実行環境を閉じる | ― |

## 3. ハッシュ値をそろえる

iroh-blobs は、データを BLAKE3 のハッシュ値で識別します。分散創造の `AssetHash` も BLAKE3 なので、**素材 ID に含まれるハッシュ値と、素材置き場・作品フォルダのファイル名が同じ値**になります（[判断の記録 0006](../../decisions/0006-p2p-iroh.md)）。M0 で、同じバイト列から同じ値が得られることを確かめます。

## 4. アルゴリズム

### A25. 公開

```
publish(hash, bytes):
    blob_hash = runtime.block_on(保管場所に bytes を加える)
    if blob_hash を 16 進数にした値 ≠ hash: return Err(Network("ハッシュ値が一致しない"))   // 実装の取り違えを防ぐ
    ticket = チケット（このノードの接続情報 + blob_hash）
    return AssetTicket{ text: ticket の文字列表現, hash }
```

- 保管場所はメモリ上なので、アプリケーションを閉じると公開も終わります（仕様書 6.1「アプリケーションを起動している間、公開した素材を相手が受け取れる」）。
- 接続情報には、直接つながらないときに使う中継サーバー（既定では Iroh の開発元が運営するもの）が含まれます（判断の記録 0006 の「影響」）。

### A26. 受け取り

```
parse_ticket(text):
    ticket = text をチケットとして読み取る（失敗したら Err(InvalidTicket)）
    return AssetTicket{ text, hash: AssetHash::parse(ticket のハッシュ値) }

fetch(ticket):
    runtime.block_on(タイムアウト 30 秒で):
        チケットの接続情報で相手のノードにつなぐ（つながらなければ Err(Unreachable)）
        ticket.hash を指定してダウンロードする
        // iroh-blobs は受信しながら BLAKE3 で検証し、一致しないデータを受け付けない
    bytes = 保管場所から読み出す
    if bytes.len() > 32 MB: return Err(Network("大きすぎる"))
    if AssetHash::of(bytes) ≠ ticket.hash: return Err(HashMismatch)    // 念のための照合
    return bytes
```

照合は 3 段階で行われます。iroh-blobs が受信中に、このクレートが受け取った後に、app が取り込む前に（[app 4 節](app.md#4-時間のかかる操作)）照合します。どこか 1 か所の実装に誤りがあっても、違う素材は取り込まれません（R-032）。

## 5. 検証用プログラム（M0）

`crates/exchange-iroh/examples/spike.rs` は、このクレートの `IrohAssetExchange` をそのまま使います。

```
cargo run -p exchange-iroh --example spike -- publish <PNG ファイル>
    → 素材 ID を表示し、Ctrl+C まで公開し続ける
cargo run -p exchange-iroh --example spike -- fetch <素材 ID> <保存先>
    → 受け取ってファイルに保存し、ハッシュ値を表示する
```

確かめること：

1. 同じ PC の 2 つのプロセス間で受け渡しできる
2. 別々の PC（同じネットワーク・別のネットワーク）で受け渡しできる
3. `AssetHash::of`（blake3 クレート）と iroh-blobs のハッシュ値が一致する
4. 公開側を止めると、`Unreachable` になる
5. 使った iroh・iroh-blobs の版と、実際の関数名をこの文書に追記する

## 6. テスト

| 確かめること | 方法 |
| --- | --- |
| A25・A26 の流れ | 同じプロセスの中で 2 つの `IrohAssetExchange` を起動し、片方で公開、もう片方で受け取る |
| 不正な素材 ID | `parse_ticket` に壊れた文字列を与えて `InvalidTicket` |
| app 側の流れ | app のテストでは testkit の `LoopbackExchange` を使い、通信しない |
