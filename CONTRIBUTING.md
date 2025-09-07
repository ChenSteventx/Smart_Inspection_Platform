 # 项目协作与发布流程（必读）

本仓库采用「feature → dev → test → master」三段式合并流程，所有改动统一从 `dev` 开始，经过你确认进入 `test`，通过 code review/测试后进入 `master` 发布。

> 约定：AI 助手与所有贡献者在每次执行前，会先在对话中列出将运行的 git 命令，再执行操作；严禁直接向 `test`/`master` push 代码。

## 分支模型
- `master`：生产稳定分支，仅接受从 `test` 合并；发布后可打正式版本标签（如 `v1.0.0`）。
- `test`：预发布/集成测试分支，仅接受从 `dev` 合并；可打 RC 标签（如 `v1.0.0-rc.1`）。
- `dev`：集成开发分支，日常联调；仅接受 `feature/*` 合并或直接在 `dev` 上的小改动。
- `feature/*`：功能/需求分支，例如 `feature/login-api`。
- `hotfix/*`：生产紧急修复，来源于 `master`，修复后合回 `master`，并同步到 `dev`/`test`。

## 基本规则
1. 首次初始化后，`master/dev/test` 三个分支内容一致（已完成）。
2. 任何改动先在 `dev` 完成提交并推送；助手会在执行前列出 git 命令。
3. 你认可 `dev` 的改动后，合并到 `test`；合并使用 `--no-ff`，并推送。
4. 通过 code review/测试后，将 `test` 合并到 `master` 发布；合并使用 `--no-ff`，并推送。
5. 回滚优先使用 `git revert`（避免强制改历史）。
6. 禁止直接向 `test`/`master` 提交或推送。

## 日常流程与命令

### 1）功能开发（feature → dev）
- 从最新 `dev` 切分支：
  ```bash
  git checkout dev
  git pull --rebase
  git checkout -b feature/<task>
  ```
- 开发与提交：
  ```bash
  git add -A
  git commit -m "feat(scope): summary"
  git push -u origin feature/<task>
  ```
- 通过 PR 合并到 `dev`（或维护者在 `dev` 上直接小改动）。

### 2）你确认后（dev → test）
- 合并与推送：
  ```bash
  git checkout test
  git pull
  git merge --no-ff dev -m "release: dev -> test"
  git push
  ```
- （可选）在 `test` 打 RC 标签：
  ```bash
  git tag -a vX.Y.Z-rc.N -m "RC N"
  git push origin vX.Y.Z-rc.N
  ```

### 3）评审/测试通过（test → master）
- 合并与推送：
  ```bash
  git checkout master
  git pull
  git merge --no-ff test -m "release: vX.Y.Z"
  git push
  ```
- （可选）打正式标签：
  ```bash
  git tag -a vX.Y.Z -m "Release vX.Y.Z"
  git push origin vX.Y.Z
  ```

### 4）紧急修复（hotfix）
```bash
git checkout master && git pull
git checkout -b hotfix/<issue>
# 修复 + 提交
git add -A && git commit -m "fix: ..."
git push -u origin hotfix/<issue>
# 合并到 master 后，同步到 dev/test
git checkout dev && git pull && git merge --no-ff master && git push
git checkout test && git pull && git merge --no-ff master && git push
```

## 提交与 PR 规范
- 提交信息：建议遵循 Conventional Commits（`feat|fix|chore|docs|refactor|test|build`）。
- PR 模板：`.github/pull_request_template.md` 会自动预填；请填写 Summary、Changes、Test Plan、Impact 与 Release Notes（发布向）。
- 合并策略：PR 合并使用 `--no-ff`，保留分支边界；本地同步最新用 `git pull --rebase`。

## 分支保护（GitHub 建议）
- 仓库 → Settings → Branches → Add rule：分别为 `master/test/dev` 配置：
  - Require a pull request before merging（至少 1 位 Reviewer）
  - Require status checks to pass before merging（如已配置 CI）
  - Require branches to be up to date before merging

## 安全与仓库健康
- 禁止提交密钥/证书/账号到仓库；`.env` 已在 `.gitignore`。
- 二进制或超大文件避免入库（>100MB）；必要时使用 Git LFS。

## 助手执行承诺
- 每次改动前：在对话中列出即将运行的 git 命令。
- 改动只提交到 `dev`，并推送 `dev`。
- 待你确认后，执行 `dev → test`；待评审/测试通过后，执行 `test → master`。
- 发布与合并均在对话中说明所用命令与结果。

最后更新：由助手自动生成；如需补充规则，请直接在本文件追加内容并走上述流程变更。

