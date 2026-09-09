# 贡献指南（Contributing Guide）

感谢你愿意参与「番茄工作台」！无论是修 bug、加功能、写文档还是提建议，都欢迎。

## 📌 项目原则

- **零第三方运行时依赖**：应用本体只用 Python 标准库。新增功能请优先用标准库实现；
  确需第三方库时，请在 Issue/PR 中说明理由并同步更新文档。
- **界面与逻辑分离**：业务逻辑放 `app/`（不依赖 tkinter，可被第三方 import），
  界面放 `ui/`。
- **每个改动都有测试**：核心逻辑请在 `tests/run_smoke.py` 中补断言。

## 🔧 本地开发

```bash
git clone https://github.com/GarryLiang/pomodoro-workbench.git
cd pomodoro-workbench

# 运行
python main.py          # 或 Windows 下双击 start.bat

# 测试（全部通过才算完成）
python tests/run_smoke.py   # 核心逻辑测试
python tests/gui_smoke.py   # GUI 冒烟（窗口会短暂闪现）
```

## 🌿 提 PR 流程

1. 先看 [Issues](https://github.com/GarryLiang/pomodoro-workbench/issues)，
   认领任务或自己提 Issue 说明要做什么，避免重复劳动。
   新手可以从标记了 `good first issue` 的任务开始。
2. `git checkout -b feature/xxx` 或 `fix/xxx` 开分支。
3. 提交信息建议用前缀：`feat:` 新功能 / `fix:` 修复 / `docs:` 文档 /
   `test:` 测试 / `refactor:` 重构 / `chore:` 杂项。
4. 推送分支并创建 Pull Request，在描述中说明：
   - 改了什么、为什么改；
   - 如何验证（测试结果截图或文字说明）；
   - 是否影响现有数据/行为。
5. 仓库配置了 CI，PR 会自动跑测试，**请确保测试全绿**。

## ✅ PR Checklist

- [ ] `python tests/run_smoke.py` 全部通过
- [ ] 代码遵循现有结构与命名风格（类名 `UpperCamelCase`，函数/变量 `lower_snake_case`）
- [ ] 有必要的注释与中文字符串保持简洁
- [ ] README / CHANGELOG 在需要时同步更新

## 🐛 报告 Bug / 提需求

请使用仓库自带的 Issue 模板：
- 报 Bug：[bug_report.md](.github/ISSUE_TEMPLATE/bug_report.md)
- 提需求：[feature_request.md](.github/ISSUE_TEMPLATE/feature_request.md)

## 🔒 安全问题

不要直接在公开 Issue 里发安全漏洞细节，请走
[SECURITY.md](SECURITY.md) 描述的流程（GitHub 安全通告）。

再次感谢你的贡献！🎉
