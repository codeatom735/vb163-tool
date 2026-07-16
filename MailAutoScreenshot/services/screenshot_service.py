"""Screenshot capture and file output service."""

from __future__ import annotations

import re
import time
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
        1. Screenshot the current opened mail page.
        2. Fall back to visible body/container screenshots.
        """

        file_path = unique_path(save_dir, safe_filename(keyword))

        try:
            if hasattr(page, "screenshot"):
                page.screenshot(path=str(file_path), full_page=True, timeout=self.timeout_ms)
                self._validate_png(file_path)
                return ScreenshotResult(str(keyword), str(file_path), "full_page", "截图成功")

            if self._try_strategy(self._screenshot_body, page, file_path):
                self._validate_png(file_path)
                return ScreenshotResult(str(keyword), str(file_path), "body", "截图成功")

            if self._try_strategy(self._screenshot_title_to_qr, page, file_path):
                self._validate_png(file_path)
                return ScreenshotResult(str(keyword), str(file_path), "title_to_qr", "截图成功")

            if self._try_strategy(
                lambda current_page, current_file: self._screenshot_keyword_area(current_page, keyword, current_file),
                page,
                file_path,
            ):
                self._validate_png(file_path)
                return ScreenshotResult(str(keyword), str(file_path), "keyword_area", "截图成功")

            if self._try_strategy(self._screenshot_detail_container, page, file_path):
                self._validate_png(file_path)
                return ScreenshotResult(str(keyword), str(file_path), "detail_container", "截图成功")

            raise ScreenshotServiceError("未找到可截图的邮件详情内容")
        except Exception as exc:
            raise ScreenshotServiceError(f"截图保存失败: {keyword}; {exc}") from exc

    @staticmethod
    def _try_strategy(strategy: Any, page: Any, file_path: Path) -> bool:
        try:
            return bool(strategy(page, file_path))
        except Exception:
            return False

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

    def _screenshot_keyword_area(self, page: Any, keyword: str, file_path: Path) -> bool:
        tokens = _identity_tokens(keyword)
        if not tokens:
            return False

        marker = f"mail-auto-screenshot-{time.monotonic_ns()}"
        result = page.evaluate(
            """
            ({ tokens, marker }) => {
                function normalize(text) {
                    return (text || "").replace(/\\s+/g, " ").trim();
                }

                function visible(element) {
                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);
                    return rect.width >= 200
                        && rect.height >= 120
                        && style.visibility !== "hidden"
                        && style.display !== "none";
                }

                function containsIdentity(text) {
                    const normalized = normalize(text);
                    const matchedCount = tokens.filter((token) => normalized.includes(token)).length;
                    const requiredCount = tokens.length >= 2 ? 2 : 1;
                    return matchedCount >= requiredCount;
                }

                const detailSignals = ["发件人", "收件人", "时 间", "时间", "附件", "回复", "转发", "打印"];
                const searchHints = ["已搜索到", "继续用AI", "批量操作", "全文搜索", "删除所有邮件"];
                let best = null;
                let bestScore = -1;

                for (const element of Array.from(document.querySelectorAll("div,section,article,main,td,iframe,body"))) {
                    if (!visible(element)) {
                        continue;
                    }

                    const text = normalize(element.innerText || element.textContent);
                    if (!containsIdentity(text)) {
                        continue;
                    }

                    const rect = element.getBoundingClientRect();
                    let score = 0;
                    score += detailSignals.filter((signal) => text.includes(signal)).length * 220;
                    score += Math.min(rect.width, 1200) + Math.min(rect.height, 1600);
                    score -= searchHints.filter((hint) => text.includes(hint)).length * 350;
                    score -= element.tagName === "BODY" ? 500 : 0;
                    score -= Math.max(0, text.length - 2500) / 10;

                    if (score > bestScore) {
                        best = element;
                        bestScore = score;
                    }
                }

                if (!best) {
                    return { found: false };
                }

                best.setAttribute("data-mail-auto-screenshot-target", marker);
                return { found: true, tag: best.tagName, score: bestScore };
            }
            """,
            {"tokens": tokens, "marker": marker},
        )
        if not result or not result.get("found"):
            return False

        locator = page.locator(f'[data-mail-auto-screenshot-target="{marker}"]').first
        locator.wait_for(state="visible", timeout=self.timeout_ms)
        locator.screenshot(path=str(file_path), timeout=self.timeout_ms)
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

    def _screenshot_body(self, page: Any, file_path: Path) -> bool:
        try:
            body = page.locator("body").first
            body.wait_for(state="visible", timeout=self.timeout_ms)
            body.screenshot(path=str(file_path), timeout=self.timeout_ms)
            return True
        except Exception:
            return False

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


def _identity_tokens(keyword: str) -> list[str]:
    clean_keyword = keyword.strip()
    raw_parts = [part.strip() for part in re.split(r"[_\s]+", clean_keyword) if part.strip()]

    tokens: list[str] = []
    if clean_keyword:
        tokens.append(clean_keyword)

    for part in raw_parts:
        upper_part = part.upper()
        has_digit = any(char.isdigit() for char in part)
        has_cjk = any("\u4e00" <= char <= "\u9fff" for char in part)
        looks_like_code = bool(re.search(r"[A-Z]{1,}-[A-Z0-9-]{6,}", upper_part))

        if looks_like_code or (has_digit and len(part) >= 8) or (has_cjk and len(part) >= 3 and part != "结题通知"):
            if part not in tokens:
                tokens.append(part)

    tokens.sort(key=len, reverse=True)
    return tokens[:6]
