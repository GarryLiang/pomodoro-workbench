"""日志工具：把意外异常写入本地日志文件，便于用户反馈问题时排查。

日志位置：~/.pomodoro_workbench/app.log（自动轮转，最多 3 个 256KB 文件）。
注意：界面里的 TclError 多为窗口销毁竞态，属于预期情况，调用方直接忽略即可；
只有非预期异常才写日志。
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path.home() / ".pomodoro_workbench"
LOG_FILE = LOG_DIR / "app.log"

_logger = None


def get_logger():
    """返回（并首次配置）应用日志器。"""
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("pomodoro_workbench")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                str(LOG_FILE), maxBytes=256 * 1024, backupCount=2,
                encoding="utf-8")
            handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s"))
            logger.addHandler(handler)
        except OSError:
            # 日志不可写时降级为静默，不影响主程序
            logger.addHandler(logging.NullHandler())
    _logger = logger
    return logger


def log_exception(message):
    """记录一次异常（需在 except 块内调用，会带上堆栈）。"""
    get_logger().exception(message)
