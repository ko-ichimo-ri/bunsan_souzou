# 初回プッシュがリモートの LICENSE により拒否された

- 日付：2026-09-24
- 記録者：Claude Opus 5.5
- 状態：解決済み

## 何が起きたか

ローカルで `git init` → 初回コミットした後、GitHub のリポジトリに `git push -u origin main` したところ、`rejected (fetch first)` で拒否された。

## 原因

GitHub でリポジトリを作成するときに LICENSE（MIT）を追加していたため、リモートの `main` に「Initial commit」が既にあった。ローカルとリモートの履歴につながりがなかった。

## 対応

1. `git fetch origin` でリモートの中身を確認し、LICENSE 1 ファイルだけで、ローカルのファイルと重ならないことを確かめた。
2. `git merge origin/main --allow-unrelated-histories` で履歴を統合した。
3. 改めて `git push -u origin main` して成功した。

強制プッシュ（`--force`）はリモートの LICENSE を消してしまうため使わなかった。

## 次に活かすこと

- プッシュが拒否されたら、まず `git fetch` でリモートの中身を確認する。強制プッシュで上書きしない。
- GitHub でリポジトリを作るとき、ローカルに既存のリポジトリがあるなら、README・LICENSE・.gitignore を追加しないで作ると手間が少ない。
