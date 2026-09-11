"""番茄工作台 —— 程序入口。

运行方式：
    python main.py
"""

import sys

from app.context import AppContext
from app.logger import get_logger, log_exception
from ui.main_window import MainWindow


def _install_exception_hook():
    """把未捕获异常写入日志文件，并在控制台提示日志位置。"""
    def hook(exc_type, exc_value, exc_tb):
        logger = get_logger()
        logger.error("未捕获异常", exc_info=(exc_type, exc_value, exc_tb))
        from app.logger import LOG_FILE
        sys.stderr.write("程序出现异常，详情已记录到：%s\n" % LOG_FILE)

    sys.excepthook = hook


def main():
    _install_exception_hook()
    context = AppContext()
    window = MainWindow(context)
    try:
        window.mainloop()
    except Exception:
        log_exception("主循环异常退出")
        raise
    finally:
        context.close()


if __name__ == "__main__":
    main()
