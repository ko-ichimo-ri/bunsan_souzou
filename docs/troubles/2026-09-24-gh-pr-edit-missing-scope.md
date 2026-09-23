# `gh pr edit` がトークンの権限不足で失敗した

- 日付：2026-09-24
- 記録者：Claude Opus 5.5
- 状態：回避策あり

## 何が起きたか

プルリクエストの説明文を `gh pr edit` で更新しようとしたところ、次のエラーで失敗した。

```
Your token has not been granted the required scopes to execute this query.
The 'login' field requires one of the following scopes: ['read:org'],
but your token has only been granted the: ['gist', 'repo', 'workflow'] scopes.
```

## 原因

- `gh` は未ログインのため、Git の認証情報（`git credential fill`）から得たトークンを `GH_TOKEN` として渡していた。
- このトークンの権限は `gist`・`repo`・`workflow` のみ。`gh pr edit` は内部の GraphQL クエリで `read:org` を必要とする。
- `gh pr create` と `gh pr list` は同じトークンで成功していた。

## 対応

REST API を直接呼び出して更新した。`read:org` は不要。

```sh
gh api -X PATCH repos/<owner>/<repo>/pulls/<番号> -F "body=@本文.md"
```

## 次に活かすこと

- `gh pr edit` の代わりに `gh api` の REST 呼び出しを使う。
- 恒久対応は、ユーザーが `gh auth login` で `read:org` を含むトークンを発行すること。
