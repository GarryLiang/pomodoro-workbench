"""多阶段提醒铃声合成：用标准库 wave / math / struct 生成不同旋律的 WAV 闹铃。

完全自产自销，不引入任何第三方音频库与外部资源文件。

三种阶段各有专属铃声，方便闭眼就能区分当前发生了什么：
- focus       专注结束 → 明亮的 C 大调上行琶音（凯旋/完成感）
- short_break 短休息结束 → 柔和的两音上行提示（G5-C6，轻声提醒回到专注）
- long_break  长休息结束 → 激昂的 G 大调上行琶音（G5-B5-D6-G6，冲刺号角）
"""

import hashlib
import math
import os
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 22050
AMPLITUDE = 0.42
# 每个音符后的小间隔（秒），避免粘连感
NOTE_GAP = 0.05
# 渐入渐出时长（秒），消除爆音
FADE = 0.008

# 阶段键名（与 app.pomodoro 的阶段常量保持一致）
KIND_FOCUS = "focus"
KIND_SHORT = "short_break"
KIND_LONG = "long_break"
KINDS = (KIND_FOCUS, KIND_SHORT, KIND_LONG)
DEFAULT_KIND = KIND_FOCUS

# 各阶段的旋律：(频率Hz, 时长秒)。None 表示静音停顿。
ALARM_PATTERNS = {
    KIND_FOCUS: [
        (523.25, 0.14),   # C5
        (659.25, 0.14),   # E5
        (783.99, 0.14),   # G5
        (1046.50, 0.32),  # C6
        (None, 0.38),     # 停顿
    ],
    KIND_SHORT: [
        (783.99, 0.16),   # G5
        (1046.50, 0.32),  # C6
        (None, 0.48),     # 停顿
    ],
    KIND_LONG: [
        (783.99, 0.13),   # G5
        (987.77, 0.13),   # B5
        (1174.66, 0.13),  # D6
        (1567.98, 0.34),  # G6
        (None, 0.44),     # 停顿
    ],
}

# 各阶段对应的铃声文件名
WAV_FILENAMES = {
    KIND_FOCUS: "alarm_focus.wav",
    KIND_SHORT: "alarm_short_break.wav",
    KIND_LONG: "alarm_long_break.wav",
}

DEFAULT_WAV_DIR = str(Path.home() / ".pomodoro_workbench")


def _validate_kind(kind):
    if kind not in ALARM_PATTERNS:
        raise ValueError("未知的铃声类型: %s（可选 %s）"
                         % (kind, "/".join(KINDS)))
    return kind


def wav_path_for(kind, wav_path=None):
    """返回某阶段铃声的默认文件路径（未指定时）。"""
    _validate_kind(kind)
    if wav_path:
        return str(wav_path)
    return os.path.join(DEFAULT_WAV_DIR, WAV_FILENAMES[kind])


def _envelope(index, total):
    """返回该采样点的淡入淡出系数 [0,1]，避免开头结尾爆音。"""
    fade_samples = max(1, int(FADE * SAMPLE_RATE))
    if index < fade_samples:
        return index / fade_samples
    if index > total - fade_samples:
        return max(0.0, (total - index) / fade_samples)
    return 1.0


def _render_note(frequency, duration):
    """渲染单个音符的 16 位 PCM 采样列表。frequency=None 表示静音。"""
    count = int(duration * SAMPLE_RATE)
    samples = []
    if frequency is None:
        return [0] * count
    step = 2.0 * math.pi * frequency / SAMPLE_RATE
    for i in range(count):
        envelope = _envelope(i, count)
        value = AMPLITUDE * envelope * math.sin(step * i)
        samples.append(int(value * 32767))
    return samples


def synthesize_alarm(kind=DEFAULT_KIND, wav_path=None):
    """按指定阶段旋律合成循环闹铃 WAV，返回输出路径。"""
    kind = _validate_kind(kind)
    out_path = wav_path_for(kind, wav_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pcm = []
    for frequency, duration in ALARM_PATTERNS[kind]:
        pcm.extend(_render_note(frequency, duration))
        if frequency is not None:
            pcm.extend(_render_note(None, NOTE_GAP))

    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(
            struct.pack("<h", sample) for sample in pcm))

    return str(out_path)


def ensure_alarm_wav(kind=DEFAULT_KIND, wav_path=None):
    """确保某阶段铃声文件存在；不存在则现场合成，返回文件路径。"""
    kind = _validate_kind(kind)
    target = Path(wav_path_for(kind, wav_path))
    if not target.exists() or target.stat().st_size < 100:
        return synthesize_alarm(kind, str(target))
    return str(target)


def alarm_path_for(kind=DEFAULT_KIND, custom_path=None):
    """解析实际要播放的铃声文件路径。

    - 若用户指定了自定义铃声且文件存在，则使用自定义铃声（所有阶段通用）
    - 否则返回该阶段内置合成铃声（必要时现场生成）
    """
    kind = _validate_kind(kind)
    if custom_path:
        candidate = Path(custom_path)
        if candidate.is_file() and candidate.stat().st_size > 100:
            return str(candidate)
    return ensure_alarm_wav(kind)


def all_alarm_fingerprints():
    """生成全部阶段铃声，返回 {kind: md5指纹}，供测试校验铃声互不相同。"""
    fingerprints = {}
    for kind in KINDS:
        path = synthesize_alarm(kind)
        with open(path, "rb") as fh:
            fingerprints[kind] = hashlib.md5(fh.read()).hexdigest()
    return fingerprints


if __name__ == "__main__":
    for kind in KINDS:
        path = synthesize_alarm(kind)
        print("已生成 [%s] 闹铃文件: %s" % (kind, path))
