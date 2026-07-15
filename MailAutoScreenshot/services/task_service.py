"""Task orchestration service."""

from __future__ import annotations

import csv
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from services.browser_service import BrowserConfig, BrowserService
from services.excel_service import ExcelService
from services.mail_service import MailService
from services.screenshot_service import ScreenshotService
from utils.file_utils import ensure_directory
from utils.logger import setup_logger


LogCallback = Callable[[str], None]
ProgressCallback = Callable[["TaskProgress"], None]
FinishedCallback = Callable[["TaskSummary"], None]


@dataclass(frozen=True)
class TaskProgress:
    """Progress snapshot emitted to the GUI."""

    total: int
    current_index: int
    success_count: int
    failed_count: int
    current_name: str


@dataclass(frozen=True)
class TaskItemResult:
    """Per-keyword task result used in the final report."""

    keyword: str
    status: str
    file_path: str = ""
    error: str = ""


@dataclass(frozen=True)
class TaskSummary:
    """Final task summary."""

    total: int
    success_count: int
    failed_count: int
    stopped: bool
    report_path: str
    message: str
    results: list[TaskItemResult] = field(default_factory=list)


class TaskServiceError(RuntimeError):
    """Raised when task scheduling fails."""


class TaskService:
    """Run the full mail screenshot workflow in a background thread."""

    def __init__(
        self,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
        on_finished: FinishedCallback | None = None,
    ) -> None:
        self.on_log = on_log
        self.on_progress = on_progress
        self.on_finished = on_finished
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._logger = setup_logger()
        self._pause_event.set()

    @property
    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def start(self, options: Any) -> None:
        """Start a new task thread."""

        with self._lock:
            if self.is_running:
                raise TaskServiceError("任务正在运行，不能重复开始")

            self._stop_event.clear()
            self._pause_event.set()
            self._thread = threading.Thread(
                target=self._run,
                args=(options,),
                name="MailAutoScreenshotTask",
                daemon=True,
            )
            self._thread.start()

    def pause(self) -> None:
        if self.is_running:
            self._pause_event.clear()
            self._log("任务已暂停。")

    def resume(self) -> None:
        if self.is_running:
            self._pause_event.set()
            self._log("任务继续执行。")

    def stop(self) -> None:
        if self.is_running:
            self._stop_event.set()
            self._pause_event.set()
            self._log("正在停止任务，当前步骤结束后退出。")

    def _run(self, options: Any) -> None:
        browser_service: BrowserService | None = None
        results: list[TaskItemResult] = []
        total = 0
        success_count = 0
        failed_count = 0
        report_path = ""

        try:
            self._log("开始读取Excel邮件列表。")
            excel_result = ExcelService().read(options.excel_path)
            keywords = excel_result.keywords
            total = len(keywords)
            self._emit_progress(total, 0, 0, 0, "-")
            self._log(f"读取到 {total} 条邮件名称，工作表: {excel_result.sheet_name}")

            save_dir = ensure_directory(options.save_dir)
            browser_service = BrowserService(
                BrowserConfig(
                    chrome_profile=options.chrome_profile,
                    timeout=options.timeout,
                )
            )
            page = browser_service.start()

            mail_service = MailService(
                page=page,
                mail_url=options.mail_url,
                timeout=options.timeout,
                log_callback=self._log,
            )
            screenshot_service = ScreenshotService(timeout=options.timeout)

            mail_service.ensure_logged_in()

            for index, keyword in enumerate(keywords, start=1):
                if self._stop_event.is_set():
                    self._log("收到停止请求，结束剩余任务。")
                    break

                self._wait_if_paused()
                if self._stop_event.is_set():
                    break

                self._emit_progress(total, index, success_count, failed_count, keyword)
                try:
                    mail_service.search_and_open_mail(keyword)
                    screenshot = screenshot_service.save_mail_detail_screenshot(
                        page=page,
                        keyword=keyword,
                        save_dir=str(save_dir),
                    )
                    success_count += 1
                    results.append(TaskItemResult(keyword=keyword, status="success", file_path=screenshot.file_path))
                    self._log(f"成功: {keyword} -> {screenshot.file_path}")
                except Exception as exc:
                    failed_count += 1
                    error = str(exc)
                    results.append(TaskItemResult(keyword=keyword, status="failed", error=error))
                    self._log(f"失败: {keyword}; {error}")
                    self._logger.exception(f"处理失败: {keyword}")

                self._emit_progress(total, index, success_count, failed_count, keyword)

            report_path = self._write_report(options.save_dir, results)
            stopped = self._stop_event.is_set()
            message = "任务已停止。" if stopped else "任务已完成。"
            summary = TaskSummary(
                total=total,
                success_count=success_count,
                failed_count=failed_count,
                stopped=stopped,
                report_path=report_path,
                message=message,
                results=results,
            )
            self._log(f"{message} 成功 {success_count}，失败 {failed_count}，报告: {report_path}")
            self._emit_finished(summary)
        except Exception as exc:
            self._logger.exception("任务异常退出")
            report_path = self._write_report(getattr(options, "save_dir", "."), results)
            summary = TaskSummary(
                total=total,
                success_count=success_count,
                failed_count=failed_count or (1 if not results else failed_count),
                stopped=self._stop_event.is_set(),
                report_path=report_path,
                message=f"任务异常退出: {exc}",
                results=results,
            )
            self._log(summary.message)
            self._emit_finished(summary)
        finally:
            if browser_service is not None:
                browser_service.close()
            with self._lock:
                self._thread = None

    def _wait_if_paused(self) -> None:
        while not self._pause_event.wait(timeout=0.2):
            if self._stop_event.is_set():
                return

    def _write_report(self, save_dir: str, results: list[TaskItemResult]) -> str:
        directory = ensure_directory(save_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path(directory) / f"task_report_{timestamp}.csv"

        with report_path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["keyword", "status", "file_path", "error"],
            )
            writer.writeheader()
            for result in results:
                writer.writerow(
                    {
                        "keyword": result.keyword,
                        "status": result.status,
                        "file_path": result.file_path,
                        "error": result.error,
                    }
                )

        return str(report_path)

    def _emit_progress(
        self,
        total: int,
        current_index: int,
        success_count: int,
        failed_count: int,
        current_name: str,
    ) -> None:
        if self.on_progress is not None:
            self.on_progress(
                TaskProgress(
                    total=total,
                    current_index=current_index,
                    success_count=success_count,
                    failed_count=failed_count,
                    current_name=current_name,
                )
            )

    def _emit_finished(self, summary: TaskSummary) -> None:
        if self.on_finished is not None:
            self.on_finished(summary)

    def _log(self, message: str) -> None:
        self._logger.info(message)
        if self.on_log is not None:
            self.on_log(message)
