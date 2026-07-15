"""Main window for the 163 mail screenshot automation tool."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from services.task_service import TaskProgress, TaskService, TaskServiceError, TaskSummary
from utils.config_manager import AppConfig, load_config, save_config


@dataclass(frozen=True)
class TaskOptions:
    """Options collected from the UI before starting a task."""

    excel_path: str
    save_dir: str
    chrome_profile: str
    timeout: int
    mail_url: str


class MainWindow(QMainWindow):
    """Primary desktop window.

    This class owns only UI state in stage 2. Task orchestration and background
    execution will be connected in stage 9.
    """

    start_requested = Signal(object)
    pause_requested = Signal()
    resume_requested = Signal()
    stop_requested = Signal()
    task_log_received = Signal(str)
    task_progress_received = Signal(object)
    task_finished_received = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.config = self._load_initial_config()
        self.task_service = TaskService(
            on_log=self.task_log_received.emit,
            on_progress=self.task_progress_received.emit,
            on_finished=self.task_finished_received.emit,
        )
        self.setWindowTitle("163邮箱自动搜索截图工具")
        self.resize(980, 680)
        self.setMinimumSize(860, 580)

        self.excel_path_edit = QLineEdit()
        self.save_dir_edit = QLineEdit(self.config.save_path)
        self.chrome_profile_edit = QLineEdit(self.config.chrome_profile)

        self.total_value = QLabel("0")
        self.current_value = QLabel("-")
        self.success_value = QLabel("0")
        self.failed_value = QLabel("0")

        self.progress_bar = QProgressBar()
        self.log_text = QPlainTextEdit()

        self.start_button = QPushButton("开始任务")
        self.start_button.setObjectName("primaryButton")
        self.pause_button = QPushButton("暂停")
        self.resume_button = QPushButton("继续")
        self.stop_button = QPushButton("停止")

        self._build_ui()
        self._connect_signals()
        self.set_idle_state()
        self.append_log("界面已就绪，请选择Excel文件和截图保存目录。")
        self.append_log(f"已加载配置：超时 {self.config.timeout} 秒。")

    def _build_ui(self) -> None:
        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 16, 18, 16)
        root_layout.setSpacing(12)

        title = QLabel("163邮箱自动搜索截图工具")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        root_layout.addWidget(title)

        path_group = QGroupBox("任务配置")
        form_layout = QFormLayout(path_group)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(10)

        form_layout.addRow("Excel文件：", self._path_row(self.excel_path_edit, "选择", self._choose_excel_file))
        form_layout.addRow("保存目录：", self._path_row(self.save_dir_edit, "选择", self._choose_save_dir))
        form_layout.addRow(
            "Chrome用户目录：",
            self._path_row(self.chrome_profile_edit, "选择", self._choose_chrome_profile_dir),
        )
        root_layout.addWidget(path_group)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        controls.addWidget(self.start_button)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.resume_button)
        controls.addWidget(self.stop_button)
        controls.addStretch(1)
        root_layout.addLayout(controls)

        status_group = QGroupBox("任务状态")
        status_layout = QGridLayout(status_group)
        status_layout.setHorizontalSpacing(18)
        status_layout.setVerticalSpacing(10)
        status_layout.addWidget(QLabel("总数量"), 0, 0)
        status_layout.addWidget(self.total_value, 0, 1)
        status_layout.addWidget(QLabel("当前处理"), 0, 2)
        status_layout.addWidget(self.current_value, 0, 3)
        status_layout.addWidget(QLabel("成功数量"), 1, 0)
        status_layout.addWidget(self.success_value, 1, 1)
        status_layout.addWidget(QLabel("失败数量"), 1, 2)
        status_layout.addWidget(self.failed_value, 1, 3)
        status_layout.addWidget(self.progress_bar, 2, 0, 1, 4)
        status_layout.setColumnStretch(1, 1)
        status_layout.setColumnStretch(3, 1)
        root_layout.addWidget(status_group)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        root_layout.addWidget(separator)

        log_group = QGroupBox("实时日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log_text.setPlaceholderText("任务运行日志会显示在这里")
        log_layout.addWidget(self.log_text)
        root_layout.addWidget(log_group, stretch=1)

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        for line_edit in (self.excel_path_edit, self.save_dir_edit, self.chrome_profile_edit):
            line_edit.setMinimumHeight(32)
            line_edit.setClearButtonEnabled(True)
            line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._apply_style()
        self.setCentralWidget(root)

    def _path_row(self, line_edit: QLineEdit, button_text: str, slot) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        button = QPushButton(button_text)
        button.setFixedWidth(82)
        button.clicked.connect(slot)

        layout.addWidget(line_edit)
        layout.addWidget(button)
        return container

    def _connect_signals(self) -> None:
        self.start_button.clicked.connect(self._handle_start_clicked)
        self.pause_button.clicked.connect(self._handle_pause_clicked)
        self.resume_button.clicked.connect(self._handle_resume_clicked)
        self.stop_button.clicked.connect(self._handle_stop_clicked)
        self.start_requested.connect(self._start_task)
        self.pause_requested.connect(self.task_service.pause)
        self.resume_requested.connect(self.task_service.resume)
        self.stop_requested.connect(self.task_service.stop)
        self.task_log_received.connect(self.append_log)
        self.task_progress_received.connect(self._handle_task_progress)
        self.task_finished_received.connect(self._handle_task_finished)
        self.save_dir_edit.editingFinished.connect(self._persist_config_safely)
        self.chrome_profile_edit.editingFinished.connect(self._persist_config_safely)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f6f7f9;
            }
            QLabel#titleLabel {
                color: #1f2937;
                font-size: 22px;
                font-weight: 700;
            }
            QGroupBox {
                background: #ffffff;
                border: 1px solid #d8dde6;
                border-radius: 6px;
                margin-top: 10px;
                padding: 14px 12px 12px 12px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QLineEdit, QPlainTextEdit {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 6px 8px;
                background: #ffffff;
                color: #111827;
            }
            QLineEdit:focus, QPlainTextEdit:focus {
                border-color: #2563eb;
            }
            QPushButton {
                min-height: 32px;
                padding: 5px 14px;
                border-radius: 4px;
                border: 1px solid #a8b3c5;
                background: #ffffff;
                color: #111827;
            }
            QPushButton:hover {
                background: #eef2f7;
            }
            QPushButton:disabled {
                color: #94a3b8;
                background: #f1f5f9;
            }
            QPushButton#primaryButton {
                background: #1d4ed8;
                border-color: #1d4ed8;
                color: #ffffff;
            }
            QPushButton#primaryButton:hover {
                background: #1e40af;
            }
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                height: 18px;
                text-align: center;
                background: #ffffff;
            }
            QProgressBar::chunk {
                background: #16a34a;
                border-radius: 3px;
            }
            """
        )

    @Slot()
    def _choose_excel_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择Excel文件",
            "",
            "Excel Files (*.xlsx *.xlsm *.xltx *.xltm);;All Files (*)",
        )
        if file_path:
            self.excel_path_edit.setText(file_path)

    @Slot()
    def _choose_save_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择截图保存目录")
        if directory:
            self.save_dir_edit.setText(directory)
            self._persist_config_safely()

    @Slot()
    def _choose_chrome_profile_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择Chrome用户目录")
        if directory:
            self.chrome_profile_edit.setText(directory)
            self._persist_config_safely()

    @Slot()
    def _handle_start_clicked(self) -> None:
        options = self._collect_task_options()
        if options is None:
            return

        self.set_running_state()
        self.reset_progress()
        self.append_log("收到开始任务请求，正在启动后台任务。")
        self.start_requested.emit(options)

    @Slot()
    def _handle_pause_clicked(self) -> None:
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(True)
        self.append_log("收到暂停请求。")
        self.pause_requested.emit()

    @Slot()
    def _handle_resume_clicked(self) -> None:
        self.pause_button.setEnabled(True)
        self.resume_button.setEnabled(False)
        self.append_log("收到继续请求。")
        self.resume_requested.emit()

    @Slot()
    def _handle_stop_clicked(self) -> None:
        self.set_stopping_state()
        self.append_log("收到停止请求。")
        self.stop_requested.emit()

    @Slot(object)
    def _start_task(self, options: TaskOptions) -> None:
        try:
            self.task_service.start(options)
        except TaskServiceError as exc:
            self.append_log(f"任务启动失败：{exc}")
            self.set_idle_state()

    def _collect_task_options(self) -> TaskOptions | None:
        excel_path = self.excel_path_edit.text().strip()
        save_dir = self.save_dir_edit.text().strip()
        chrome_profile = self.chrome_profile_edit.text().strip()

        if not excel_path:
            QMessageBox.warning(self, "缺少Excel文件", "请先选择Excel文件。")
            return None
        if not Path(excel_path).is_file():
            QMessageBox.warning(self, "Excel文件不存在", "请选择有效的Excel文件。")
            return None
        if not save_dir:
            QMessageBox.warning(self, "缺少保存目录", "请先选择截图保存目录。")
            return None
        if not chrome_profile:
            QMessageBox.warning(self, "缺少Chrome用户目录", "请先选择Chrome用户目录。")
            return None

        return TaskOptions(
            excel_path=excel_path,
            save_dir=save_dir,
            chrome_profile=chrome_profile,
            timeout=self.config.timeout,
            mail_url=self.config.mail_url,
        )

    def _load_initial_config(self) -> AppConfig:
        try:
            return load_config()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "配置读取失败",
                f"配置文件读取失败，将使用默认配置。\n\n{exc}",
            )
            return AppConfig()

    @Slot()
    def _persist_config_safely(self) -> None:
        updated_config = AppConfig(
            chrome_profile=self.chrome_profile_edit.text().strip() or self.config.chrome_profile,
            timeout=self.config.timeout,
            save_path=self.save_dir_edit.text().strip() or self.config.save_path,
            mail_url=self.config.mail_url,
        )

        try:
            save_config(updated_config)
        except Exception as exc:
            self.append_log(f"配置保存失败：{exc}")
            return

        self.config = updated_config

    def set_idle_state(self) -> None:
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    def set_running_state(self) -> None:
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.resume_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def set_stopping_state(self) -> None:
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    def reset_progress(self) -> None:
        self.total_value.setText("0")
        self.current_value.setText("-")
        self.success_value.setText("0")
        self.failed_value.setText("0")
        self.progress_bar.setValue(0)

    @Slot(int, int, int, int, str)
    def update_task_status(
        self,
        total: int,
        current_index: int,
        success_count: int,
        failed_count: int,
        current_name: str,
    ) -> None:
        self.total_value.setText(str(total))
        self.current_value.setText(f"{current_index}/{total} {current_name}".strip())
        self.success_value.setText(str(success_count))
        self.failed_value.setText(str(failed_count))

        progress = int(current_index / total * 100) if total else 0
        self.progress_bar.setValue(max(0, min(progress, 100)))

    @Slot(object)
    def _handle_task_progress(self, progress: TaskProgress) -> None:
        self.update_task_status(
            progress.total,
            progress.current_index,
            progress.success_count,
            progress.failed_count,
            progress.current_name,
        )

    @Slot(object)
    def _handle_task_finished(self, summary: TaskSummary) -> None:
        self.set_idle_state()
        self.update_task_status(
            summary.total,
            summary.total,
            summary.success_count,
            summary.failed_count,
            "完成" if not summary.stopped else "已停止",
        )
        self.append_log(summary.message)
        if summary.report_path:
            self.append_log(f"任务报告：{summary.report_path}")

    @Slot(str)
    def append_log(self, message: str) -> None:
        self.log_text.appendPlainText(message)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def closeEvent(self, event) -> None:
        if self.task_service.is_running:
            self.task_service.stop()
            self.append_log("窗口关闭，已请求停止后台任务。")
        super().closeEvent(event)
