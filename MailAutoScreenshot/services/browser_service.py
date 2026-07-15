"""Playwright browser lifecycle service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class BrowserServiceError(RuntimeError):
    """Raised when browser automation cannot be started or used."""


@dataclass(frozen=True)
class BrowserConfig:
    """Browser launch options used by the automation task."""

    chrome_profile: str
    timeout: int = 20
    headless: bool = False
    channel: str = "chrome"
    viewport_width: int = 1440
    viewport_height: int = 900

    @property
    def timeout_ms(self) -> int:
        return max(1, self.timeout) * 1000


class BrowserService:
    """Manage a Playwright persistent Chromium context.

    The persistent context stores cookies and local storage in `chrome_profile`,
    so a manual 163 login can be reused in later runs.
    """

    def __init__(self, config: BrowserConfig) -> None:
        self.config = config
        self._playwright: Any | None = None
        self._context: Any | None = None
        self._page: Any | None = None

    @property
    def is_started(self) -> bool:
        return self._context is not None and self._page is not None

    def start(self) -> Any:
        """Start Chrome with a persistent profile and return the active page."""

        if self.is_started:
            return self._page

        sync_playwright = self._import_sync_playwright()
        profile_path = self._ensure_profile_dir()

        try:
            self._playwright = sync_playwright().start()
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_path),
                channel=self.config.channel,
                headless=self.config.headless,
                accept_downloads=True,
                timeout=self.config.timeout_ms,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            )
            self._context.set_default_timeout(self.config.timeout_ms)
            self._context.set_default_navigation_timeout(self.config.timeout_ms)
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
            self._page.set_default_timeout(self.config.timeout_ms)
            self._page.set_default_navigation_timeout(self.config.timeout_ms)
            return self._page
        except Exception as exc:
            self.close()
            raise BrowserServiceError(f"启动Chrome浏览器失败: {exc}") from exc

    def open_url(self, url: str) -> Any:
        """Open a URL and wait until the document is ready."""

        page = self.get_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=self.config.timeout_ms)
            return page
        except Exception as exc:
            raise BrowserServiceError(f"打开网页失败: {url}; {exc}") from exc

    def get_page(self) -> Any:
        """Return the active Playwright page, starting Chrome if needed."""

        if not self.is_started:
            return self.start()
        return self._page

    def get_context(self) -> Any:
        """Return the active Playwright browser context."""

        if not self.is_started:
            self.start()
        return self._context

    def close(self) -> None:
        """Close the persistent context and stop Playwright."""

        context = self._context
        playwright = self._playwright
        self._page = None
        self._context = None
        self._playwright = None

        if context is not None:
            try:
                context.close()
            except Exception:
                pass

        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                pass

    def __enter__(self) -> "BrowserService":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def _ensure_profile_dir(self) -> Path:
        profile_path = Path(self.config.chrome_profile).expanduser()
        profile_path.mkdir(parents=True, exist_ok=True)
        return profile_path

    @staticmethod
    def _import_sync_playwright() -> Any:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserServiceError(
                "未安装Playwright，请先执行: pip install -r requirements.txt && playwright install chromium"
            ) from exc

        return sync_playwright
