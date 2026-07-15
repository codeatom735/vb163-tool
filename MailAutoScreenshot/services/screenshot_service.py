"""Screenshot capture and file output service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.selectors import (
    MAIL_DETAIL_CONTAINER_SELECTORS,
    MAIL_DETAIL_QR_CODE_SELECTORS,
    MAIL_DETAIL_TITLE_SELECTORS,
)
from utils.file_utils import safe_filename, unique_path


class ScreenshotServiceError(RuntimeError):
    """Raised when screenshot capture fails."""


@dataclass(frozen=True)
class ScreenshotResult:
    """Result of saving one screenshot."""

    keyword: str
    file_path: str
    mode: str
    message: str


class ScreenshotService:
    """Save PNG screenshots for opened 163 mail detail pages."""

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = max(1, timeout)
        self.timeout_ms = self.timeout * 1000

    def save_mail_detail_screenshot(self, page: Any, keyword: str, save_dir: str) -> ScreenshotResult:
        """Save a screenshot using the original Excel content as filename.

        Priority:
        1. Clip from mail title to the bottom of the QR code.
        2. Screenshot the mail detail container.
        3. Screenshot the full page.
        """

        file_path = unique_path(save_dir, safe_filename(keyword))

        try:
            if self._screenshot_title_to_qr(page, file_path):
                self._validate_png(file_path)
                return ScreenshotResult(str(keyword), str(file_path), "title_to_qr", "截图成功")

            if self._screenshot_detail_container(page, file_path):
                self._validate_png(file_path)
                return ScreenshotResult(str(keyword), str(file_path), "detail_container", "截图成功")

            page.screenshot(path=str(file_path), full_page=True, timeout=self.timeout_ms)
            self._validate_png(file_path)
            return ScreenshotResult(str(keyword), str(file_path), "full_page", "截图成功")
        except Exception as exc:
            raise ScreenshotServiceError(f"截图保存失败: {keyword}; {exc}") from exc

    def _screenshot_title_to_qr(self, page: Any, file_path: Path) -> bool:
        title_locator = self._optional_visible_locator(page, MAIL_DETAIL_TITLE_SELECTORS, 3000)
        qr_locator = self._optional_visible_locator(page, MAIL_DETAIL_QR_CODE_SELECTORS, 3000)

        if title_locator is None or qr_locator is None:
            return False

        title_box = title_locator.bounding_box()
        qr_box = qr_locator.bounding_box()
        if not title_box or not qr_box:
            return False

        container_box = None
        container_locator = self._optional_visible_locator(page, MAIL_DETAIL_CONTAINER_SELECTORS, 1000)
        if container_locator is not None:
            container_box = container_locator.bounding_box()

        viewport = page.viewport_size or {"width": 1440, "height": 900}
        x = max(0, container_box["x"] if container_box else min(title_box["x"], qr_box["x"]))
        y = max(0, min(title_box["y"], qr_box["y"]))
        right = container_box["x"] + container_box["width"] if container_box else viewport["width"]
        bottom = max(title_box["y"] + title_box["height"], qr_box["y"] + qr_box["height"])

        clip = {
            "x": x,
            "y": y,
            "width": max(1, right - x),
            "height": max(1, bottom - y),
        }
        page.screenshot(path=str(file_path), clip=clip, timeout=self.timeout_ms)
        return True

    def _screenshot_detail_container(self, page: Any, file_path: Path) -> bool:
        container_locator = self._optional_visible_locator(
            page,
            MAIL_DETAIL_CONTAINER_SELECTORS,
            self.timeout_ms,
        )
        if container_locator is None:
            return False

        container_locator.screenshot(path=str(file_path), timeout=self.timeout_ms)
        return True

    def _optional_visible_locator(self, page: Any, selectors: tuple[str, ...], timeout_ms: int) -> Any | None:
        selector = ", ".join(selector for selector in selectors if selector.strip())
        if not selector:
            return None

        locator = page.locator(selector).first
        try:
            locator.wait_for(state="visible", timeout=timeout_ms)
            return locator
        except Exception:
            return None

    @staticmethod
    def _validate_png(file_path: Path) -> None:
        try:
            from PIL import Image
        except ImportError as exc:
            raise ScreenshotServiceError("未安装Pillow，请先执行: pip install -r requirements.txt") from exc

        with Image.open(file_path) as image:
            width, height = image.size
            if width < 200 or height < 120:
                raise ScreenshotServiceError(f"截图尺寸异常: {width}x{height}")
            image.verify()
