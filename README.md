# codex-title-once

**Name a Codex chat once, after its first substantive task — using the current agent and official hooks.**

[English](#english) · [中文说明](#中文说明) · [Related projects / 类似项目](#related-projects--类似项目)

## English

### What it does

`codex-title-once` gives each new local Codex chat a short, durable title after the first meaningful piece of work is complete. The **agent already working in that conversation** chooses the title. This package does not launch another model, ask for an API key, or require another sign-in just to name the chat.

The naming hierarchy is:

```text
Project → Internal module → Persistent goal
```

Codex already displays the project. The chat title therefore contains only:

```text
Module｜Persistent goal
```

For example, “fix draftbox write failures and add tests” becomes `草稿箱｜写入稳定性` (Draftbox｜Write reliability). Later debugging, tests and commits belong to the same goal and do not repeatedly change the title. The default instructions prefer concise Chinese titles; the fields can also contain English text.

Greetings, empty prompts, generic tests and vague requests are deferred. A completed analysis, plan, code change or report qualifies as substantive work; the entire research or product goal does not have to be finished. Existing chats created before installation are skipped.

### Supported scope

| Capability | Status |
| --- | --- |
| Windows native Codex Desktop, user-level command hooks | Implemented |
| Current-agent title generation, no separate model request | Default mode |
| Once-per-chat state, resume/compaction handling | Implemented |
| Install, inspect, enable, disable and uninstall | Implemented |
| User-provided model API / local CodeBuddy | Planned; not implemented |
| ChatGPT web / Codex web browser extension | Not implemented or tested |
| macOS / Linux | Not tested |

Verified local environment: Codex Desktop **26.1007.2314.0**, bundled CLI **0.162.0-alpha.17.2**, Windows. These are tested versions, not a minimum-version promise. Changes to Codex hooks or App Server may affect compatibility.

Persisted title metadata and the live sidebar are separate verification surfaces. The script checks the saved title through `thread/read`; a successful readback does not prove that every already-open UI refreshes immediately. Reopen the chat if necessary.

### Requirements

- Windows and a working Codex Desktop installation with supported lifecycle hooks and local App Server interfaces.
- Python **3.9 or newer**, available through `py -3`. No third-party Python packages are required.
- Access to review and trust user-level hooks through a supported Codex hook-management interface.

### Install

Download the repository ZIP, or clone it:

```powershell
git clone https://github.com/leo-cheung-itlger/codex-title-once.git
cd codex-title-once
py -3 --version
py -3 install.py install
```

The installer first checks the official `hooks/list` interface. It copies the runtime into `CODEX_HOME/thread-naming`, defaulting to `$env:USERPROFILE\.codex\thread-naming`, and merges three entries into the user-level `hooks.json`. It backs up existing configuration before changing it. Reinstalling retains existing naming states, the original installation cutoff, unrelated hooks and a previously disabled setting.

**Review and trust the three naming hooks before use.** In a supported Codex CLI, open `/hooks` and review `SessionStart`, `UserPromptSubmit` and `Stop` entries containing `auto_title.py`. If Desktop exposes an equivalent hook-trust UI, use that interface instead. The installer does not silently trust its hooks or change global security policies. This review is required by Codex; it is not a second account login.

Check activation:

```powershell
py -3 install.py check
```

All three entries should be enabled and `trusted`. Start a new chat. If an already-running desktop process caches configuration, restart it after your current work is finished. If your version exposes no supported hook-trust interface, installation alone is not sufficient; consult the official Hooks documentation for that version.

### How it works

```text
SessionStart / UserPromptSubmit
    → inject naming instructions into the current agent's context
Current agent finishes its first substantive work
    → submits a candidate through auto_title.py propose
Stop
    → validates the candidate against the current request generation
    → reserves one attempt, calls thread/name/set, verifies with thread/read
    → stores named state; future automatic naming stops
```

`Stop` does not ask another model to generate a title. Naming uses a small amount of context and tool execution inside the current agent's normal session, so “no separate model request” does **not** mean “zero session usage.” There is no direct external model API integration in this version. The official local App Server metadata API is still used to save the title.

State is stored per session ID with atomic writes and a Windows file lock. A new prompt or resume creates a new candidate generation. Compaction preserves the active generation instead of relying on a hard-coded turn ID.

### Manage and uninstall

From the downloaded repository directory:

```powershell
py -3 install.py disable
py -3 install.py enable
py -3 install.py uninstall
```

Uninstall disables this tool and removes its naming registrations. It retains unrelated hooks, state, logs and backups, and does not recursively delete files. The saved `old_title` can be used for a reviewed restoration through official metadata interfaces; this version does not include a general batch-rollback command.

### Manual titles and failure behavior

The default `first_default_once` policy permits replacing the initial default title once. After the automatic attempt, it will not rename the chat again. A manual title set after successful automatic naming is therefore preserved.

**A manual edit made before the first automatic rename cannot be fully protected.** The interfaces used here do not reliably expose title provenance or an atomic compare-and-set operation. Explicitly telling the agent to preserve or manually name the chat causes it to submit a `protect` operation, but a concurrent UI edit still has a race window.

For a conservative alternative, change `protection` to `strict` in the installed `settings.json`. Any existing title then prevents automatic renaming, including Codex-generated default titles. This does not distinguish manual from automatic defaults.

Hook errors return an empty result and exit zero; naming must not block the main task. A title-write attempt is reserved before mutation and not automatically retried after failure. If the current agent never submits a candidate, the chat remains pending and the local log records `awaiting_candidate`. Model compliance is a limitation, not a guaranteed callback.

### Privacy and publication safety

- No bundled API keys, passwords, OAuth tokens, private keys or real chat transcripts.
- No extra model backend, telemetry, direct HTTP client or credential-file reader in this package.
- Codex itself may use its existing account/configuration as part of normal operation. This tool does not bypass its permissions or billing.
- Metadata reads use `includeTurns: false`. The naming script does not export full conversation history or directly write Codex SQLite/transcript JSONL.
- Runtime state contains session IDs, titles, project/work-directory metadata and candidate state. Logs contain event/error summaries; installation backups may contain sensitive user configuration. Keep these files private.
- `.gitignore` excludes runtime data, credential-file patterns and backups. An ignore rule cannot protect a file already committed; review staged files before publishing.
- Publish the source files below, not an entire user `.codex` directory. Report bugs with sanitized diagnostics and synthetic examples.

These measures reduce exposure; they are not a guarantee against all platform, model, local-system or concurrent-edit risks.

### Test and troubleshoot

```powershell
py -3 -m unittest discover -v
```

The 19 tests use synthetic conversations and temporary directories. They cover first naming, repeated events, follow-up tests/commits, greetings, manual protection, resume, compaction, nonblocking errors and scoped installation/uninstallation. Prior local integration checks exercised actual hook-driven turns and a fresh App Server resume; this public repository intentionally does not include real chat transcripts or private test reports. Desktop restart and webpage behavior are not claimed as tested.

| Symptom | What to check |
| --- | --- |
| Nothing happens in a new chat | Run `install.py check`; verify three enabled, trusted hooks and Python availability. |
| Existing old chat is skipped | This is intentional: the installation cutoff excludes pre-existing chats. |
| `awaiting_candidate` | The current agent did not submit a candidate; no extra model is silently launched. |
| `metadata_not_ready` | Metadata was unavailable at that event; a later hook can re-check it. |
| `failed` state | Inspect local sanitized diagnostics; failure is not automatically retried. |
| Saved name is correct but sidebar is stale | Reopen the chat/client; a separate App Server does not guarantee immediate UI notification. |
| You only use ChatGPT/Codex web | This local Windows hook package is not a web extension. |

### Source layout and contributing

| File | Purpose |
| --- | --- |
| `auto_title.py` | Hook handler, candidate submission, state and official title metadata writes |
| `install.py` | Scoped installer, status check, enable/disable and uninstall |
| `test_auto_title.py` | Synthetic state-machine regression tests |
| `test_install.py` | Temporary-directory installation safety and idempotency tests |
| `AGENTS.md` | Contributor/agent boundaries and validation instructions |
| `README.md`, `LICENSE`, `.gitignore` | Documentation, MIT license and runtime-data exclusions |

Read `AGENTS.md` before contributing. Preserve the default current-agent mode, verify behavior with synthetic input, and clearly label unimplemented features. API and CodeBuddy modes may be added as optional choices later. Web support needs its own observed UI/API integration and end-to-end validation.

This is an independent community project, not an official OpenAI product. Related projects and official references are linked below.

## 中文说明

**Codex 一次命名：首轮实质任务完成后，由当前会话智能体生成稳定标题。**

默认不另接 API、不另调用模型、不要求额外 CLI 登录。沿用正在工作的 Codex 会话智能体判断标题，官方生命周期 Hooks 提供规则并保存候选，Stop 通过 App Server 的 `thread/name/set` 更新标题元数据。

## 目前可用范围

| 能力 | 状态 |
| --- | --- |
| Windows 本机 Codex Desktop 的用户级 Hooks | 已实现 |
| 当前智能体生成标题，无额外模型请求 | 默认模式，已实现 |
| 首次实质完成后命名、恢复后不重复 | 已实现 |
| 安装、检查、启停、卸载及状态机测试 | 已实现 |
| 用户自配模型 API | 后续可选接入，尚未实现 |
| 本机 CodeBuddy | 后续可选接入，尚未实现 |
| ChatGPT／Codex 网页浏览器扩展 | 尚未实现、未验收 |
| macOS／Linux | 尚未验证 |

已验证环境：Windows、Codex Desktop 26.1007.2314.0、内置 codex-cli 0.162.0-alpha.17.2。不是最低支持版本或所有版本兼容保证。正式接口或 Hooks 行为可能随 Codex 更新改变。

## 命名规则

层级：`Project → Module → Persistent Goal`。项目名称已经由 Codex Project/工作目录提供，所以标题只写：

```text
项目内部模块｜持续目标
```

模块可为功能、页面、癌种、数据集、科研子方向、工作流、代码组件、论文部分。持续目标描述整段聊天始终推进的交付，不描述某一次检查、修改、测试或提交。

| 首个请求 | 合适的标题 |
| --- | --- |
| 修复草稿箱写入失败并补充测试 | 草稿箱｜写入稳定性 |
| 补齐 LUSC 数据的临床信息 | LUSC｜临床资料补齐 |
| 整理 FGF 信号的机制证据 | FGF信号｜机制证据整理 |
| 完成论文结果段及后续修改 | 论文写作｜结果段收束 |

中文优先、简短、不加日期。问候、点号、模糊测试或尚未形成具体目标时暂缓。首次有明确目标的一轮分析、方案、代码或报告完成即可命名；不等待整个长期研究结束。之后即使继续测试、调试、提交也保持标题。彻底切换无关目标时建议新开会话。

## 工作机制

```text
SessionStart / UserPromptSubmit
    → 读取本工具状态，给当前会话智能体注入命名规则
当前智能体完成首次实质工作
    → 调用 auto_title.py propose 提交模块和持续目标
Stop
    → 校验候选所属请求，登记一次尝试
    → thread/name/set，随后 thread/read 验证
    → named；后续永久停止自动命名
```

标题的“思考”在当前智能体中发生。Stop 只处理结果，不再请求另一个智能体。命名指令注入当前会话上下文，可能带来少量现有模型上下文/工具调用开销；“无额外模型请求”不表示整个功能完全不消耗会话额度。

状态按 session_id 原子保存，Windows 文件锁避免重复并发。新用户请求和 resume 建立候选 generation；compact 保持当前 generation，避免固定 turn_id 的过期指令。安装前已有会话自动跳过。

## 安装（Windows）

前提：已安装并正常使用 Codex Desktop，支持本地生命周期 Hooks；Python 3.9 或更新版本可用，`py -3 --version` 能运行。无需安装第三方 Python 包。此工具使用已有 Codex 会话，不要求为了命名再次登录。

下载仓库 ZIP 解压，或在 PowerShell 中克隆仓库后执行：

```powershell
git clone https://github.com/leo-cheung-itlger/codex-title-once.git
cd codex-title-once
py -3 --version
py -3 install.py install
```

安装器先读取官方 `hooks/list` 检查接口，然后把脚本安装到当前 `CODEX_HOME` 的 `thread-naming` 目录，默认是 `$env:USERPROFILE\.codex\thread-naming`。它合并用户级 `hooks.json`，保留无关 Hooks、旧状态与安装时间；重要原文件先备份。重新安装不会把已命名会话恢复成待命名状态，也不会把已关闭的配置强行启用。

**按 Codex 官方要求，查看并信任三条命名 Hook。**可用支持 `/hooks` 的 Codex CLI 进入 Hook 管理界面，查看包含 `auto_title.py` 的 SessionStart、UserPromptSubmit、Stop；如果当前 Desktop 提供 Hook 信任管理界面，也可在那里查看。安装或改动定义不会自动获得信任；安装器不自动改信任记录、不降低安全策略。这一步是 Hook 审核，不是再次登录账号。没有 CLI Hook 管理入口的版本需使用它支持的官方信任界面，不能假定信任已生效。

查看状态：

```powershell
py -3 install.py check
```

应显示 sessionStart、userPromptSubmit、stop 三条命名 Hook 均启用且 trusted。配置变更后新开会话；若桌面缓存配置，在工作结束后重开 Codex。

## 关闭与卸载

```powershell
py -3 install.py disable
py -3 install.py enable
py -3 install.py uninstall
```

卸载只禁用本工具并移除本工具的注册，保留无关 Hook、状态、日志和备份，不递归删除目录。状态中保留命名前的 old_title，可用于人工核查和通过官方接口恢复；本版本没有通用批量回滚命令。

## 保护手动标题和失败行为

默认策略是 `first_default_once`：允许覆盖首次默认标题一次，成功命名后永久停止。因此命名后的手动修改不会被覆盖。

**首次命名前的纯 UI 手动标题无法完整保护**：当前本工具使用的官方接口不能可靠提供标题来源历史和原子比较交换。用户明确要求保持或手动命名时，智能体会调用 `protect` 并永久跳过；仍存在并发 UI 改名竞争窗口。

如需保守策略，可把安装目录 `settings.json` 的 `protection` 改成 `strict`：只要存在任何标题就保留。它同时可能跳过 Codex 自带的默认标题，不能区分两者。

所有 Hook 失败均退出 0、返回空结果、不请求阻断主任务。已开始写标题的尝试先登记为 failed，成功后改为 named；失败不自动重试，避免后续覆盖用户标题。模型漏交候选时留 pending，日志记录 awaiting_candidate。此机制依赖当前智能体遵循指令，不保证每个模型或每轮都提交候选。

本工具只写自己的状态、Hook 注册及官方标题元数据，不直接修改 Codex SQLite 或聊天正文。不要把运行时 settings.json、state、events.jsonl、账号凭据和用户备份上传到公共仓库。

## 隐私与发布安全

公开源码不包含真实 API Key、密码、OAuth token、私钥或聊天记录；当前实现没有直接外部模型 HTTP 请求、遥测或凭据文件读取代码。保存标题用的是本地 Codex 官方元数据接口，并非另接模型 API。Codex 本身仍按其已有账号、权限与配置正常运行。

元数据查询使用 `includeTurns: false`，不导出聊天全文。运行状态会保存会话 ID、标题、项目/工作目录和候选信息；日志保存事件和错误摘要。安装备份可能包含敏感配置，这些都是用户本地资料，应保留在本机。`.gitignore` 不能阻止已经提交过的文件泄露，发布前仍需核对暂存文件。

当前脚本确认的是持久化标题读回，不保证所有已打开的侧边栏马上刷新。如果官方元数据已经正确而 UI 仍旧显示旧标题，可重新打开会话/客户端；不同版本需要实测，不能把元数据成功当成所有 UI 同步已通过。

## 验证

```powershell
py -3 -m unittest discover -v
```

测试使用临时目录和合成会话，验证首次命名、重复事件、后续测试/提交、寒暄、人工保护、恢复、压缩、故障不阻断，以及安装器的范围与幂等性。此前本机实际 Hook 测试覆盖问候→实质任务→追问→手动标题，并在新 App Server 进程中恢复；未把这些结果宣称为实际重启 Desktop 或网页端验收。公开包不附带真实聊天测试记录。

## 后续接入：保持默认轻量

未来可添加用户自配 API 与本机 CodeBuddy，用于当前智能体不能提交候选或其他客户端场景；两者应由用户选择，不成为默认安装的强制依赖。

网页扩展需要单独验证读取、完成事件与重命名控件。官方云端编排不运行本机用户/插件命令 Hooks，网页安装插件也不会部署本机脚本。即使成功接入某个模型，也不等于已经获得 ChatGPT/Codex 网页标题写权限。本项目当前不提供网页扩展，不调用未公开的 backend-api。

## 官方资料

- [Hooks：生命周期、配置、信任及云端限制](https://learn.chatgpt.com/docs/hooks)
- [Codex App Server：thread/read 与 thread/name/set](https://learn.chatgpt.com/docs/app-server)
- [插件打包：Hooks 的分发与支持边界](https://developers.openai.com/plugins/build/plugins)

## Related projects / 类似项目

The following comparison is based on the linked maintainers' documentation, reviewed on 2026-10-13. These projects have not been installed or security-audited as part of this release.

下表依据维护者仓库文档，核对日期为 2026-10-13；本次没有安装这些工具或对其做安全审计。

| Project / 项目 | Similarity / 相近之处 | Difference / 差异 |
| --- | --- | --- |
| [egorovli/codex-session-auto-rename](https://github.com/egorovli/codex-session-auto-rename) | Codex UserPromptSubmit/Stop hooks; metadata renaming / Codex Hooks 与元数据改名 | Developer preview; default deterministic engine, considers later goal changes, and reports live-UI propagation limitations / 开发预览，默认确定性引擎，考虑后续目标变化，明确提示实时 UI 同步限制 |
| [sathwick-p/claude-rename](https://github.com/sathwick-p/claude-rename) | First meaningful exchange, Stop hook, once-per-session / 首次有意义交互后命名一次 | Claude Code; background `claude -p` worker, usually Haiku, and transcript title writes / 针对 Claude Code，另开后台模型调用并写会话文件 |
| [victor-software-house/pi-auto-rename](https://github.com/victor-software-house/pi-auto-rename) | Automatic naming after first assistant response / 首次回答后自动命名 | Pi extension; configurable naming model and explicit `/rename` commands / 针对 Pi，可选命名模型与显式重命名命令 |

Our scope is narrower: the current Codex agent submits the semantic title, the hook saves it once, and the project layer is omitted from the title. This is a design distinction, not a claim that the alternatives are inferior or that this implementation works in every client.

本项目的定位：当前 Codex 智能体生成语义标题、Hook 只保存一次、标题采用项目内部模块与持续目标。上表说明设计差异，不代表其他项目更差，也不代表本项目已适配所有客户端。

## License / 许可证

MIT — see [LICENSE](LICENSE). Independent community software; not affiliated with or endorsed by OpenAI.

MIT 开源许可证，详见 [LICENSE](LICENSE)。独立社区工具，与 OpenAI 无官方关联。
