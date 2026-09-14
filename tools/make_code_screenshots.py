"""开发者工具：把项目中的关键函数/类渲染成带行号的代码截图（用于申报材料）。

特点：
- 用标准库 ast 精确定位函数/类所在行区间，并统计**有效行数**（不含空行与注释行）；
- 用 Pillow 渲染：标题栏（文件 / 符号 / 行号区间 / 有效行数）、行号栏、简易语法高亮、
  页脚（项目名 + 原创代码 + 行数），输出 PNG；
- 同时输出清单 `screenshots/code/manifest.md` 与 `manifest.json`，便于申报书引用。

用法：
    python tools/make_code_screenshots.py

仅用于生成材料，不参与应用运行（需 Pillow，属于开发期依赖）。
"""

import ast
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "screenshots", "code")

FONT_CODE_CANDIDATES = (
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\cour.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/System/Library/Fonts/Menlo.ttc",
)
FONT_CN_CANDIDATES = (
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
)

CODE_SIZE = 18
GUTTER_PAD = 14
LINE_PAD = 6
TITLE_H = 56
FOOTER_H = 32

BG = "#ffffff"
CODE_BG = "#fbfcfe"
TITLE_BG = "#26364f"
TITLE_FG = "#ffffff"
TITLE_SUB = "#a9bcd6"
GUTTER_FG = "#9aa6b8"
FG = "#24292f"
COLOR_KEYWORD = "#0b5cad"
COLOR_STRING = "#a31515"
COLOR_COMMENT = "#2f8f4e"
COLOR_NUMBER = "#098658"
COLOR_DEF = "#795e26"
COLOR_DECORATOR = "#af00db"

# 需要截图的代码片段：(输出文件名, 说明, 文件, [符号...], 显式行区间或 None)
# 显式区间用于把较长的方法拆成两张（每张控制在十几~二十几行，便于阅读与排版）
SPECS = [
    ("01-番茄钟-开始专注.png", "番茄钟状态机：开始 / 继续计时",
     "app/pomodoro.py", ["PomodoroEngine.start"], None),
    ("02-番茄钟-暂停重置.png", "番茄钟状态机：暂停 / 开始暂停切换 / 重置",
     "app/pomodoro.py", ["PomodoroEngine.pause", "PomodoroEngine.reset"], None),
    ("03-番茄钟-手动推进.png", "手动推进 1 秒（无界面场景与第三方程序可用）",
     "app/pomodoro.py", ["PomodoroEngine.tick"], None),
    ("04-番茄钟-墙钟刷新.png", "按真实时间刷新剩余时间（幂等，界面卡顿不影响计时）",
     "app/pomodoro.py", ["PomodoroEngine.refresh"], None),
    ("05-番茄钟-时钟取整.png", "单调时钟剩余秒数计算与浮点取整容限",
     "app/pomodoro.py", ["PomodoroEngine._remaining_from_clock"], None),
    ("06-铃声-波形与包络.png", "标准库合成铃声：包络（防爆音）与正弦波形生成",
     "app/alarm.py", ["_envelope", "_render_note"], None),
    ("07-铃声-WAV写出.png", "按阶段旋律写出循环 WAV 文件",
     "app/alarm.py", ["synthesize_alarm"], None),
    ("08-提醒-播放铃声.png", "Windows 异步循环播放铃声（跨平台回退）",
     "ui/reminder.py", ["_play_wav"], None),
    ("09-提醒-提醒入口.png", "阶段结束提醒入口：按设置决定弹窗 / 响铃",
     "ui/reminder.py", ["show_phase_reminder"], None),
    ("10-悬浮窗-位置记忆.png", "悬浮窗位置恢复：多显示器坐标校验与默认位置",
     "ui/float_window.py", ["FloatWindow._restore_position"], None),
    ("11-悬浮窗-显隐与置顶.png", "悬浮窗显示、隐藏与 📌 置顶开关",
     "ui/float_window.py", ["FloatWindow.show", "FloatWindow.hide",
                            "FloatWindow.toggle_topmost"], None),
    ("12-习惯热力图-绘制.png", "Canvas 自绘热力图：颜色分级、今日高亮",
     "ui/habit_view.py", ["HabitView._draw_heatmap 绘制部分"], (269, 292)),
    ("13-统计趋势图-柱条.png", "Canvas 自绘趋势图：柱条、数值与日期标签",
     "ui/stats_view.py", ["StatsView._draw_chart 柱条部分"], (229, 250)),
    ("14-数据库-结构迁移.png", "SQLite 结构版本迁移通道",
     "app/storage.py", ["Storage._apply_migrations"], None),
    ("15-跨平台字体.png", "按平台探测可用中文字体并回退",
     "ui/theme.py", ["init_fonts"], None),
]

TOKEN_RE = re.compile(
    r"(#.*$"
    r"|\"\"\"[\s\S]*?\"\"\""
    r"|\"[^\"]*\""
    r"|'[^']*'"
    r"|@[\w.]+"
    r"|\b(?:def|class|return|if|elif|else|for|while|try|except|finally|with|as"
    r"|import|from|in|not|and|or|is|None|True|False|self|raise|lambda|global"
    r"|pass|break|continue|yield|del|assert|async|await|match|case)\b"
    r"|\b\d+(?:\.\d+)?\b)"
)


def load_font(candidates, size):
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def find_span(tree, dotted):
    """返回符号（支持 A.B 形式的方法）的 (起始行, 结束行, 类型)。"""
    parts = dotted.split(".")
    node = tree
    for part in parts:
        found = None
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                    and child.name == part:
                found = child
                break
        if found is None:
            raise SystemExit("未找到符号: %s" % dotted)
        node = found
    return node.lineno, node.end_lineno, type(node).__name__


def effective_lines(lines):
    """统计有效行数（不含空行与纯注释行）。"""
    count = 0
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#"):
            count += 1
    return count


def highlight(line):
    """把一行拆成 [(文本, 颜色)]，做简易语法高亮。"""
    parts = []
    pos = 0
    for match in TOKEN_RE.finditer(line):
        if match.start() > pos:
            parts.append((line[pos:match.start()], FG))
        token = match.group(0)
        if token.startswith("#"):
            color = COLOR_COMMENT
        elif token.startswith(("\"", "'")):
            color = COLOR_STRING
        elif token.startswith("@"):
            color = COLOR_DECORATOR
        elif token.isdigit() or (token[0].isdigit() and "." in token):
            color = COLOR_NUMBER
        elif token in ("def", "class"):
            color = COLOR_DEF
        else:
            color = COLOR_KEYWORD
        parts.append((token, color))
        pos = match.end()
    if pos < len(line):
        parts.append((line[pos:], FG))
    return parts or [("", FG)]


def render(spec, manifest):
    filename, desc, rel_path, symbols, explicit_range = spec
    abs_path = os.path.join(ROOT, rel_path)
    with open(abs_path, encoding="utf-8") as fh:
        source = fh.read()
    all_lines = source.split("\n")
    tree = ast.parse(source)

    if explicit_range:
        start, end = explicit_range
    else:
        spans = [find_span(tree, s) for s in symbols]
        start = min(s[0] for s in spans)
        end = max(s[1] for s in spans)

    lines = all_lines[start - 1:end]
    eff = effective_lines(lines)
    symbol_label = " / ".join(symbols)

    font = load_font(FONT_CODE_CANDIDATES, CODE_SIZE)
    font_bold = load_font(FONT_CODE_CANDIDATES, CODE_SIZE)
    font_cn = load_font(FONT_CN_CANDIDATES, 15)
    font_cn_small = load_font(FONT_CN_CANDIDATES, 13)

    char_w = font.getlength("M")
    text_w = max(font.getlength(ln) for ln in lines) if lines else 200
    gutter_w = max(font.getlength(str(end)) + GUTTER_PAD * 2, 46)
    width = int(gutter_w + text_w + GUTTER_PAD * 2)
    height = TITLE_H + LINE_PAD * 2 + int((CODE_SIZE + 8) * len(lines)) + FOOTER_H

    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    # 标题栏
    draw.rectangle([0, 0, width, TITLE_H], fill=TITLE_BG)
    draw.text((16, 9), os.path.basename(rel_path), font=font_bold, fill=TITLE_FG)
    line_info = "第 %d-%d 行 · 有效 %d 行" % (start, end, eff)
    draw.text((16, 29), line_info + " · " + " / ".join(symbols),
              font=font_cn_small, fill=TITLE_SUB)
    info_w = font_cn_small.getlength(line_info)
    draw.text((width - info_w - 16, 9), line_info, font=font_cn_small,
              fill=TITLE_SUB)

    # 代码区
    y = TITLE_H + LINE_PAD
    for idx, line in enumerate(lines, start=start):
        draw.text((GUTTER_PAD, y), str(idx), font=font, fill=GUTTER_FG)
        x = gutter_w + GUTTER_PAD
        for text, color in highlight(line):
            if text:
                draw.text((x, y), text, font=font, fill=color)
                x += font.getlength(text)
        y += CODE_SIZE + 8

    # 页脚
    draw.rectangle([0, height - FOOTER_H, width, height], fill=CODE_BG)
    draw.text((16, height - FOOTER_H + 7),
              "番茄工作台 Pomodoro Workbench · 原创代码（不含第三方库）· " + desc,
              font=font_cn_small, fill="#5b6b80")

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, filename)
    img.save(out_path)

    manifest.append({
        "file": filename,
        "path": rel_path,
        "symbols": symbols,
        "start": start,
        "end": end,
        "code_lines": end - start + 1,
        "effective_lines": eff,
        "desc": desc,
    })
    print("已生成 %-34s %s 第 %d-%d 行（有效 %d 行，%dx%d）"
          % (filename, rel_path, start, end, eff, width, height))


def main():
    manifest = []
    for spec in SPECS:
        render(spec, manifest)

    total_eff = sum(item["effective_lines"] for item in manifest)
    md_path = os.path.join(OUT_DIR, "manifest.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("# 关键代码截图清单\n\n")
        fh.write("| 截图 | 文件 | 函数/方法 | 行号区间 | 有效行数 | 说明 |\n")
        fh.write("|---|---|---|---|---|---|\n")
        for item in manifest:
            fh.write("| %s | `%s` | %s | %d-%d | %d | %s |\n" % (
                item["file"], item["path"],
                " / ".join(item["symbols"]), item["start"], item["end"],
                item["effective_lines"], item["desc"]))
        fh.write("\n共 %d 张截图，覆盖有效代码 %d 行（不含注释与空行）。\n"
                 % (len(manifest), total_eff))
    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    print("\n清单: %s（共 %d 张，覆盖有效代码 %d 行）"
          % (md_path, len(manifest), total_eff))


if __name__ == "__main__":
    main()
