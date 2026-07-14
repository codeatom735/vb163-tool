"""Application entry point for MailAutoScreenshot."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("163邮箱自动搜索截图工具")
    app.setOrganizationName("MailAutoScreenshot")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
