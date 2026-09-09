"""番茄工作台 —— 程序入口。

运行方式：
    python main.py
"""

from app.context import AppContext
from ui.main_window import MainWindow


def main():
    context = AppContext()
    window = MainWindow(context)
    try:
        window.mainloop()
    finally:
        context.close()


if __name__ == "__main__":
    main()
