"""163 mail page operations."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from services.selectors import (
    AUTHENTICATED_MARKER_SELECTORS,
    AUTHENTICATED_URL_KEYWORDS,
    LOGIN_MARKER_SELECTORS,
)


class MailServiceError(RuntimeError):
    """Raised when 163 mail page operations fail."""


class LoginRequiredError(MailServiceError):
    """Raised when the user does not complete manual login in time."""


@dataclass(frozen=True)
class LoginCheckResult:
    """Result of checking the current 163 login state."""

    is_logged_in: bool
    reason: str
    current_url: str


class MailService:
    """Handle 163 mail navigation and login-state detection.

    This service never enters usernames or passwords. If 163 requires login,
    the browser remains open and the caller can tell the user to complete
    manual login.
    """

    def __init__(
        self,
        page: Any,
        mail_url: str,
        timeout: int = 20,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.page = page
        self.mail_url = mail_url
        self.timeout = max(1, timeout)
        self.timeout_ms = self.timeout * 1000
        self.log_callback = log_callback

    def open_mail(self) -> None:
        """Open 163 mail and wait for the first document load."""

        self._log(f"打开163邮箱: {self.mail_url}")
        try:
            self.page.goto(self.mail_url, wait_until="domcontentloaded", timeout=self.timeout_ms)
            self.page.wait_for_load_state("domcontentloaded", timeout=self.timeout_ms)
        except Exception as exc:
            raise MailServiceError(f"打开163邮箱失败: {exc}") from exc

    def check_login_state(self, timeout_ms: int = 3000) -> LoginCheckResult:
        """Return the current login state without blocking for a long time."""

        current_url = self._safe_current_url()

        if self._url_looks_authenticated(current_url):
            return LoginCheckResult(True, "URL显示已进入邮箱主界面", current_url)

        if self._any_visible(AUTHENTICATED_MARKER_SELECTORS, timeout_ms):
            return LoginCheckResult(True, "检测到邮箱主界面元素", current_url)

        if self._any_visible(LOGIN_MARKER_SELECTORS, timeout_ms):
            return LoginCheckResult(False, "检测到登录页或登录框", current_url)

        return LoginCheckResult(False, "暂未检测到已登录状态", current_url)

    def is_logged_in(self, timeout_ms: int = 3000) -> bool:
        """Return whether the current page appears to be logged in."""

        return self.check_login_state(timeout_ms).is_logged_in

    def ensure_logged_in(self, manual_login_timeout: int = 600) -> LoginCheckResult:
        """Open 163 mail and wait for manual login when needed."""

        self.open_mail()
        state = self.check_login_state()
        self._log(state.reason)

        if state.is_logged_in:
            return state

        self._log("163邮箱未登录，请在打开的浏览器中扫码或手动登录。")
        return self.wait_for_manual_login(manual_login_timeout)

    def wait_for_manual_login(self, timeout_seconds: int = 600) -> LoginCheckResult:
        """Wait until the user completes manual login in the browser."""

        deadline = time.monotonic() + max(1, timeout_seconds)
        last_state = self.check_login_state(timeout_ms=1000)

        while time.monotonic() < deadline:
            remaining_ms = int((deadline - time.monotonic()) * 1000)
            wait_ms = max(500, min(self.timeout_ms, remaining_ms))

            if self._any_visible(AUTHENTICATED_MARKER_SELECTORS, wait_ms):
                result = self.check_login_state(timeout_ms=1000)
                if result.is_logged_in:
                    self._log("登录完成，继续执行任务。")
                    return result

            current_url = self._safe_current_url()
            if self._url_looks_authenticated(current_url):
                result = LoginCheckResult(True, "URL显示已进入邮箱主界面", current_url)
                self._log("登录完成，继续执行任务。")
                return result

            last_state = LoginCheckResult(False, "等待用户完成登录", current_url)

        raise LoginRequiredError(
            f"等待用户登录超时，最后状态: {last_state.reason}; URL: {last_state.current_url}"
        )

    def _any_visible(self, selectors: tuple[str, ...], timeout_ms: int) -> bool:
        selector = _join_selectors(selectors)
        if not selector:
            return False

        try:
            self.page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            return False

    def _safe_current_url(self) -> str:
        try:
            return str(self.page.url)
        except Exception:
            return ""

    @staticmethod
    def _url_looks_authenticated(url: str) -> bool:
        lowered_url = url.lower()
        return any(keyword.lower() in lowered_url for keyword in AUTHENTICATED_URL_KEYWORDS)

    def _log(self, message: str) -> None:
        if self.log_callback is not None:
            self.log_callback(message)


def _join_selectors(selectors: tuple[str, ...]) -> str:
    return ", ".join(selector for selector in selectors if selector.strip())
