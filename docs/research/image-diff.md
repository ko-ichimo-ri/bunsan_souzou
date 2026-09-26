# 画像・図版の差分表現の先行事例

| 項目 | 内容 |
| --- | --- |
| 調査日 | 2026-09-26 |
| 調査者 | Claude Opus 5.5 |
| 対象 | [concept.md](../concept.md)「過去との比較が足りない ― 分散バージョン管理システム」 |

## 1. 目的

分散創造は、作品の履歴どうしの差分を目で見て比較できることを目指している（[vision.md](../vision.md) F-VCS-05）。既存の Git やプラットフォームでも画像の差分は見られるが、それよりも良い方法があるかを、先行事例から検討する。

## 2. 方法

- 公式の文書と、査読付き論文を一次資料として用いた。
- すべての出典は、調査日に原文を取得し、引用した文が原文に存在することを照合した。引用は「」内に原文のまま示す。
- 「3. 調査結果」には出典が述べる事実のみを書き、本プロジェクトとしての解釈は「4. 分散創造への示唆」に分けて書く。

## 3. 調査結果

### 3.1 画素の比較（GitHub）

GitHub は、画像の差分を「three different modes: 2-up, swipe, and onion skin」で比較できる [1]。

- **2-up**：2 つの画像を並べて表示する。画像の大きさが変わった場合は「the actual dimension change is displayed」[1]
- **Swipe**：スライダーで境目を動かし、2 つの画像の一部ずつを並べて比べる [1]
- **Onion skin**：不透明度を変えて重ね、「when elements move around by small, hard to notice amounts」に役立つ [1]

いずれも、2 つの版の**画素**を人が見比べるための表示である。

### 3.2 文字に変換した比較（Git）

Git は、バイナリファイルの差分を、文字に変換したうえで表示できる。Git の文書は「Sometimes it is desirable to see the diff of a text-converted version of some binary files」と述べ、変換するプログラムを `textconv` として設定できるとしている。ただし、この差分は「useful for human viewing (but cannot be applied directly)」である [2]。

### 3.3 構造単位の差分と統合（3D モデルの研究）

3D モデルの分野では、画素ではなく**構成要素の対応づけ**によって差分と統合を行う研究がある。

- **3D Diff**：Doboš と Steed は、3D モデルの差分と統合を行うツールを示した。問題をソフトウェアの統合になぞらえ、「firstly, we automatically detect differences in 3D models by noting correspondences and discrepancies between them; secondly we provide an interactive tool to select between such changes in order to effect a merge」と述べている [3]。
- **MeshGit**：Denning と Pellacini は、ポリゴンメッシュの差分と統合のアルゴリズムを示した。「Inspired by version control for text editing, we introduce the mesh edit distance as a measure of the dissimilarity between meshes」と述べ、頂点と面の対応づけによって差分を求める。統合では、共通の祖先からの編集を操作の集合として求め、競合しない編集を自動で適用し、競合する編集は利用者に選ばせる [4]。

## 4. 分散創造への示唆

ここからは、調査結果を踏まえた本プロジェクトとしての解釈である。

### 4.1 2 種類の差分を使い分ける

| データ | 差分の方法 | 先例 |
| --- | --- | --- |
| コマ内容の線（ベクター） | **構造単位**：線ごとに「追加」「削除」「変更」を判定し、色分けして示す | 3D Diff [3]、MeshGit [4] |
| コマ割り | **構造単位**：コマごとに「移動」「拡大・縮小」「追加」「削除」「読み順の変更」を判定し、言葉と図で示す | 同上 |
| 貼った素材・将来のラスター画像 | **画素単位**：並べる・スワイプ・重ねるの 3 つの表示 | GitHub [1] |

分散創造は、線を点の座標の並び（JSON）として保存し、コマ割りとコマ内容を別ファイルにしている（[設計判断 0004](../decisions/0004-data-format-json.md)）。この形式では、線とコマが ID を持つ構成要素なので、3D モデルの研究 [3][4] と同じく、構成要素の対応づけによる差分が自然に使える。画素の比較 [1] よりも、「どの線を描き足したか」「どのコマを動かしたか」を明確に示せる点が、既存のプラットフォームに対する利点になる。

### 4.2 統合への応用

MeshGit [4] の統合の考え方（共通の祖先からの編集を求め、競合しない編集は自動適用、競合する編集は利用者が選ぶ）は、構想の F-VCS-06・F-VCS-07 と対応する。線やコマの単位で競合を判定すれば、ファイル単位（v0.1.0 の設計）よりも細かく自動統合できる。

### 4.3 Git との接続

v0.1.0 は `git` コマンドを使う（[設計判断 0005](../decisions/0005-vcs-git-cli.md)）。Git の `textconv` [2] を使えば、JSON を「コマ 2 を移動」のような人が読める要約に変換して、`git diff` に表示できる。ただし、この差分は表示専用であり [2]、統合には使えない。構造単位の統合は、分散創造の側で実装する必要がある。

### 4.4 構想への反映の提案

- F-VCS-05（差分を目で見て比較）を、「線とコマは構造単位、画素データは 3 つの表示」と具体化する。
- F-VCS-06（統合）の判定単位を、「レイヤー単位」から「線・コマ単位」に細かくすることを検討する。
- コマ割りのデータに、回転・長方形以外の形・枠線の種類を加える（concept.md の「コマの管理は、コマの番号、形、紙面内の座標、線の種類などを管理」「トリミング情報（回転、座標、拡大縮小率など）」への対応）。v0.1.0 は長方形・回転なしのままとし、構想に加える。

## 参考文献

アクセス日はすべて 2026-09-26。

1. GitHub Docs. Working with non-code files. https://docs.github.com/en/repositories/working-with-files/using-files/working-with-non-code-files （引用箇所：Viewing differences）
2. Git. gitattributes Documentation. https://git-scm.com/docs/gitattributes （引用箇所：Performing text diffs of binary files）
3. Doboš, J., & Steed, A. (2012). 3D Diff: An Interactive Approach to Mesh Differencing and Conflict Resolution. In *SIGGRAPH Asia 2012 Technical Briefs*. https://3drepo.com/wp-content/uploads/2012/11/dobos-steed_siggraph-asia-2012.pdf
4. Denning, J. D., & Pellacini, F. (2013). MeshGit: Diffing and Merging Meshes for Polygonal Modeling. *ACM Transactions on Graphics*, 32(4), Article 35. https://doi.org/10.1145/2461912.2461942 （本文：https://cse.taylor.edu/~jdenning/projects/meshgit/meshgit-s13.pdf）
