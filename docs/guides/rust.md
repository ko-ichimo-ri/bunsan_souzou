# Rust 技術ガイド

分散創造の開発に必要な Rust の知識を、初心者向けにまとめたガイドです。開発を進めながら、つまずいた点や新しく使った技術を随時追記します。

技術選定の理由は [設計判断の記録](../decisions/) を参照してください。

## 目次

1. [環境構築](#1-環境構築)
2. [Cargo の基本](#2-cargo-の基本)
3. [Rust の考え方（最低限）](#3-rust-の考え方最低限)
4. [本プロジェクトで使うクレート](#4-本プロジェクトで使うクレート)
5. [よくあるコンパイルエラー](#5-よくあるコンパイルエラー)
6. [参考資料](#6-参考資料)

---

## 1. 環境構築

### 1.1 Rust のインストール（Windows）

1. C++ のビルドツールを入れます。Rust は Windows でプログラムを組み立てる際に Microsoft のリンカーを使います。

   ```powershell
   winget install Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
   ```

2. Rust のインストーラー（rustup）を入れます。

   ```powershell
   winget install Rustlang.Rustup
   ```

3. ターミナルを開き直して、インストールを確認します。

   ```powershell
   rustc --version
   cargo --version
   ```

### 1.2 エディター

VS Code に拡張機能 **rust-analyzer** を入れます。入力補完・エラー表示・型の表示が使えるようになり、学習がかなり楽になります。

### 1.3 Rust の更新

```powershell
rustup update
```

## 2. Cargo の基本

Cargo は Rust のビルドツール兼パッケージ管理ツールです。

| コマンド | 内容 |
| --- | --- |
| `cargo new 名前` | 新しいプロジェクトを作る |
| `cargo run` | ビルドして実行する |
| `cargo build --release` | 最適化してビルドする（配布用・性能確認用） |
| `cargo test` | テストを実行する |
| `cargo fmt` | コードの書式を整える |
| `cargo clippy` | よくある間違いや改善点を指摘する |
| `cargo add クレート名` | 依存するクレート（ライブラリ）を追加する |

`Cargo.toml` にプロジェクトの情報と依存クレートを書き、`Cargo.lock` に実際に使ったバージョンが記録されます。アプリケーションでは両方を Git に入れます。

## 3. Rust の考え方（最低限）

### 3.1 変数は基本的に変更不可

```rust
let x = 1;       // 変更不可
let mut y = 1;   // mut を付けると変更可能
y += 1;
```

### 3.2 所有権と借用

Rust の最大の特徴です。値には「持ち主（所有者）」が 1 人だけいます。

```rust
let a = String::from("線");
let b = a;              // 所有権が a から b に移る（ムーブ）
// println!("{a}");     // a はもう使えないのでコンパイルエラー

let c = String::from("コマ");
let d = &c;             // 借用：中身を読むだけなら & で借りる
println!("{c} {d}");    // c も d も使える
```

- `&T`：読み取り用の借用。同時に何人でも借りられる。
- `&mut T`：書き換え用の借用。同時に 1 人だけ借りられる。

この決まりにより、メモリ関連の不具合がコンパイル時に見つかります。

### 3.3 構造体と列挙型

```rust
struct Point { x: f32, y: f32 }

struct Stroke {
    points: Vec<Point>,
}

enum Tool {
    Pen,
    Eraser,
}
```

`match` で列挙型の値ごとに処理を分けます。すべての場合を書かないとコンパイルエラーになるので、処理の書き忘れを防げます。

```rust
match tool {
    Tool::Pen => { /* 線を追加 */ }
    Tool::Eraser => { /* 線を削除 */ }
}
```

### 3.4 値がないかもしれない：`Option`

```rust
let first: Option<&Point> = stroke.points.first();
if let Some(p) = first {
    println!("{} {}", p.x, p.y);
}
```

### 3.5 失敗するかもしれない：`Result` と `?`

```rust
fn load(path: &std::path::Path) -> std::io::Result<String> {
    let text = std::fs::read_to_string(path)?; // 失敗したらその場でエラーを返す
    Ok(text)
}
```

`?` を付けると、失敗時にエラーを呼び出し元へそのまま返します。アプリケーションでは、いろいろな種類のエラーをまとめて扱える **anyhow** クレートを使うと楽です。

## 4. 本プロジェクトで使うクレート

### 4.1 serde / serde_json：JSON の読み書き

```rust
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
struct Point { x: f32, y: f32 }

let json = serde_json::to_string_pretty(&Point { x: 1.0, y: 2.0 })?;
let p: Point = serde_json::from_str(&json)?;
```

`#[derive(...)]` を付けるだけで、構造体と JSON を相互に変換できます。

追加方法：`cargo add serde --features derive` と `cargo add serde_json`

### 4.2 egui / eframe：画面

egui は、毎フレーム画面全体を描き直す「即時モード」方式の画面ライブラリです。状態は自分の構造体に持ち、`update` の中で「今の状態をどう表示するか」を書きます。

```rust
use eframe::egui;

#[derive(Default)]
struct App {
    count: u32,
}

impl eframe::App for App {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            if ui.button("押す").clicked() {
                self.count += 1;
            }
            ui.label(format!("{} 回", self.count));
        });
    }
}

fn main() -> eframe::Result {
    eframe::run_native(
        "分散創造",
        eframe::NativeOptions::default(),
        Box::new(|_cc| Ok(Box::new(App::default()))),
    )
}
```

- 書き方は egui のバージョンで変わることがあります。コンパイルが通らないときは、使っているバージョンの公式サンプル（examples）を確認してください。
- 標準のフォントには日本語が含まれていません。日本語を表示するには、日本語フォントを読み込んで `ctx.set_fonts(...)` で設定します。
- 線を描くには `ui.painter()` で得られる `Painter` を使います。マウスの位置や押下状態は `Response` や `ctx.input(...)` から取得します。

追加方法：`cargo add eframe`

### 4.3 std::process::Command：git コマンドの呼び出し

```rust
use std::path::Path;
use std::process::Command;

fn git(repo: &Path, args: &[&str]) -> anyhow::Result<String> {
    let output = Command::new("git").args(args).current_dir(repo).output()?;
    if !output.status.success() {
        anyhow::bail!("{}", String::from_utf8_lossy(&output.stderr));
    }
    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
}

// 使用例：履歴更新
git(repo, &["add", "."])?;
git(repo, &["commit", "-m", "線を追加"])?;
```

標準ライブラリだけで使えます。

### 4.4 Iroh：P2P 通信

Iroh は、データをハッシュ値で指定して端末間で受け渡すライブラリです。ファイルの受け渡しには iroh-blobs を使います。非同期処理（`async` / `await`）と、その実行環境である **tokio** が必要です。

使い方は、P2P の検証用プログラムを作る段階で追記します。

## 5. よくあるコンパイルエラー

| エラー | 意味 | 主な対処 |
| --- | --- | --- |
| `E0382` borrow of moved value | ムーブ済みの値を使った | `&` で借用する / `.clone()` で複製する |
| `E0502` cannot borrow as mutable because it is also borrowed as immutable | 読み取り用に借りている間に書き換えようとした | 読み取りを先に終えてから書き換える / 必要な値を先に取り出す |
| `E0499` cannot borrow as mutable more than once | 書き換え用の借用を同時に 2 つ作った | 借用の範囲を小さくする |
| `E0308` mismatched types | 型が合わない | エラーに表示される expected（期待）と found（実際）を見比べる |
| `E0277` the `?` operator can only be used ... | `Result` を返さない関数の中で `?` を使った | 関数の戻り値を `Result` にする |

エラーメッセージには、多くの場合 `help:` として直し方の提案が書かれています。まずそこを読むのが近道です。

## 6. 参考資料

- [The Rust Programming Language 日本語版](https://doc.rust-jp.rs/book-ja/)：公式の入門書
- [Rust by Example 日本語版](https://doc.rust-jp.rs/rust-by-example-ja/)：短いコード例で学べる
- [egui のデモ](https://www.egui.rs/)：ブラウザで egui の部品を試せる
- [Iroh のドキュメント](https://www.iroh.computer/docs)
