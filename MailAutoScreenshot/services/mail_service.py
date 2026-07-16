"""163 mail page operations."""

from __future__ import annotations

import time
import re
from dataclasses import dataclass
from typing import Any, Callable

from services.selectors import (
    AUTHENTICATED_MARKER_SELECTORS,
    AUTHENTICATED_URL_KEYWORDS,
    LOGIN_MARKER_SELECTORS,
    MAIL_DETAIL_CONTAINER_SELECTORS,
    MAIL_RESULT_CLICKABLE_SELECTORS,
    MAIL_RESULT_ITEM_SELECTORS,
    SEARCH_BUTTON_SELECTORS,
    SEARCH_INPUT_SELECTORS,
    SEARCH_LOADING_SELECTORS,
    SEARCH_RESULT_AREA_SELECTORS,
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


@dataclass(frozen=True)
class MailSearchResult:
    """Result of a single mail search operation."""

    keyword: str
    result_detected: bool
    message: str


@dataclass(frozen=True)
class MailOpenResult:
    """Result of opening a searched mail detail page."""

    keyword: str
    opened: bool
    message: str


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
        self._detail_context: Any | None = None

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

    def search_mail(self, keyword: str) -> MailSearchResult:
        """Search one mail keyword and wait for the result area."""

        clean_keyword = keyword.strip()
        if not clean_keyword:
            raise MailServiceError("搜索关键词不能为空")

        self._detail_context = None
        if not self.is_logged_in(timeout_ms=1000):
            raise LoginRequiredError("当前未检测到163邮箱登录状态，无法搜索邮件")

        self._log(f"搜索邮件: {clean_keyword}")
        search_input = self._first_visible_locator(
            SEARCH_INPUT_SELECTORS,
            self.timeout_ms,
            "搜索框",
        )

        try:
            self._activate_search_input(search_input)
            search_input.fill(clean_keyword, timeout=self.timeout_ms)
            self._activate_search_input(search_input)
        except Exception:
            try:
                self._activate_search_input(search_input)
                self.page.keyboard.press("Control+A")
                self.page.keyboard.press("Backspace")
                search_input.type(clean_keyword, timeout=self.timeout_ms)
                self._activate_search_input(search_input)
            except Exception as exc:
                raise MailServiceError(f"输入搜索关键词失败: {clean_keyword}; {exc}") from exc

        self._trigger_search(search_input)
        self._wait_for_search_result(clean_keyword)

        return MailSearchResult(
            keyword=clean_keyword,
            result_detected=True,
            message="搜索完成",
        )

    def search_and_open_mail(self, keyword: str) -> MailOpenResult:
        """Search a keyword and open the matching mail detail page."""

        self.search_mail(keyword)
        return self.open_first_search_result(keyword)

    def open_first_search_result(self, keyword: str) -> MailOpenResult:
        """Open the first search result for a keyword without using coordinates."""

        clean_keyword = keyword.strip()
        if not clean_keyword:
            raise MailServiceError("邮件关键词不能为空")

        self._log(f"打开搜索结果: {clean_keyword}")
        if self._click_search_result_by_dom(clean_keyword, double_click=False):
            self._wait_for_loading_to_finish()
            try:
                self.wait_for_mail_detail(clean_keyword)
                return MailOpenResult(
                    keyword=clean_keyword,
                    opened=True,
                    message="邮件详情已打开",
                )
            except MailServiceError:
                self._log("单击搜索结果后仍未进入详情页，尝试双击搜索结果。")
                if self._click_search_result_by_dom(clean_keyword, double_click=True):
                    self._wait_for_loading_to_finish()
                    self.wait_for_mail_detail(clean_keyword)
                    return MailOpenResult(
                        keyword=clean_keyword,
                        opened=True,
                        message="邮件详情已打开",
                    )

        result_locator = self._find_result_locator(clean_keyword)

        try:
            result_locator.click(timeout=self.timeout_ms)
        except Exception as exc:
            raise MailServiceError(f"打开搜索结果失败: {clean_keyword}; {exc}") from exc

        self._wait_for_loading_to_finish()
        self.wait_for_mail_detail(clean_keyword)

        return MailOpenResult(
            keyword=clean_keyword,
            opened=True,
            message="邮件详情已打开",
        )

    def wait_for_mail_detail(self, keyword: str) -> None:
        """Wait until the mail detail page is visible."""

        if self._wait_until_detail_opened(keyword):
            return

        if self._is_still_search_result_page():
            raise MailServiceError("点击搜索结果后仍停留在搜索结果页，未进入邮件详情")

        for context in self._page_and_frames():
            if self._context_looks_like_open_mail_view(context, keyword):
                self._detail_context = context
                url = getattr(context, "url", "")
                self._log(f"已进入邮件内部，未匹配到固定详情容器，按当前页面继续截图: {url}")
                return

        raise MailServiceError("点击搜索结果后未确认进入邮件内部，已停止截图避免截到搜索结果页")

    def get_detail_context(self) -> Any:
        """Return the Page or Frame that contains the opened mail detail."""

        return self._detail_context or self.page

    def _any_visible(self, selectors: tuple[str, ...], timeout_ms: int) -> bool:
        selector = _join_selectors(selectors)
        if not selector:
            return False

        try:
            self.page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            return False

    def _first_visible_locator(self, selectors: tuple[str, ...], timeout_ms: int, name: str) -> Any:
        selector = _join_selectors(selectors)
        if not selector:
            raise MailServiceError(f"未配置{name}选择器")

        locator = self.page.locator(selector).first
        try:
            locator.wait_for(state="visible", timeout=timeout_ms)
            return locator
        except Exception as exc:
            raise MailServiceError(f"未找到可见的{name}") from exc

    def _trigger_search(self, search_input: Any) -> None:
        self._activate_search_input(search_input)

        try:
            search_button = self._first_visible_locator(
                SEARCH_BUTTON_SELECTORS,
                2000,
                "搜索按钮",
            )
            search_button.click(timeout=self.timeout_ms)
        except MailServiceError:
            try:
                self._activate_search_input(search_input)
                self.page.keyboard.press("Enter")
            except Exception as exc:
                raise MailServiceError(f"触发搜索失败: {exc}") from exc
        except Exception as exc:
            try:
                self._activate_search_input(search_input)
                self.page.keyboard.press("Enter")
            except Exception:
                raise MailServiceError(f"点击搜索按钮失败: {exc}") from exc

        self._wait_for_loading_to_finish()

    def _activate_search_input(self, search_input: Any) -> None:
        try:
            self.page.bring_to_front()
        except Exception:
            pass

        try:
            search_input.scroll_into_view_if_needed(timeout=self.timeout_ms)
        except Exception:
            pass

        try:
            search_input.click(timeout=self.timeout_ms, force=True)
        except Exception:
            search_input.click(timeout=self.timeout_ms)

        try:
            search_input.evaluate(
                """
                (element) => {
                    element.focus();
                    if (typeof element.select === "function") {
                        element.select();
                    }
                }
                """
            )
        except Exception:
            pass

        time.sleep(0.05)

    def _wait_for_search_result(self, keyword: str) -> None:
        self._wait_for_loading_to_finish()

        for token in _identity_tokens(keyword) + _keyword_tokens(keyword):
            try:
                self.page.get_by_text(token, exact=False).first.wait_for(
                    state="visible",
                    timeout=self.timeout_ms,
                )
                self._log(f"搜索结果已出现关键词片段: {token}")
                return
            except Exception:
                pass

        try:
            result_area = self._first_visible_locator(
                SEARCH_RESULT_AREA_SELECTORS,
                self.timeout_ms,
                "搜索结果区域",
            )
            result_area.wait_for(state="visible", timeout=self.timeout_ms)
        except MailServiceError:
            pass

        try:
            self._first_visible_locator(MAIL_RESULT_ITEM_SELECTORS, self.timeout_ms, "搜索结果邮件")
        except Exception as exc:
            raise MailServiceError(f"搜索后未检测到结果区域或关键词: {keyword}") from exc

    def _find_result_locator(self, keyword: str) -> Any:
        for token in _identity_tokens(keyword) + _keyword_tokens(keyword):
            locator = self._try_result_row_by_text(token)
            if locator is not None:
                self._log(f"定位到搜索结果邮件片段: {token}")
                return locator

        for token in _identity_tokens(keyword) + _keyword_tokens(keyword):
            try:
                keyword_locator = self.page.get_by_text(token, exact=False).first
                keyword_locator.wait_for(state="visible", timeout=3000)
                self._log(f"定位到搜索结果文本片段: {token}")
                return keyword_locator
            except Exception:
                pass

        return self._first_visible_locator(
            MAIL_RESULT_ITEM_SELECTORS,
            self.timeout_ms,
            "搜索结果邮件",
        )

    def _try_result_row_by_text(self, token: str) -> Any | None:
        escaped_token = _escape_css_text(token)
        for selector in MAIL_RESULT_CLICKABLE_SELECTORS:
            try:
                locator = self.page.locator(f'{selector}:has-text("{escaped_token}")').first
                locator.wait_for(state="visible", timeout=2000)
                return locator
            except Exception:
                pass

        return None

    def _click_search_result_by_dom(self, keyword: str, double_click: bool = False) -> bool:
        marker = f"mail-auto-result-{time.monotonic_ns()}"
        result = self.page.evaluate(
            """
            ({ tokens, identityTokens, marker }) => {
                const badTexts = [
                    "已搜索到",
                    "继续用AI",
                    "完善条件",
                    "追加问题",
                    "批量操作",
                    "全文搜索",
                    "删除所有邮件"
                ];

                function normalize(text) {
                    return (text || "").replace(/\\s+/g, " ").trim();
                }

                function visible(element) {
                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);
                    return rect.width > 1
                        && rect.height > 1
                        && style.visibility !== "hidden"
                        && style.display !== "none";
                }

                function badSearchHint(text) {
                    return badTexts.some((bad) => text.includes(bad));
                }

                function mailboxContext(text) {
                    return text.includes("[收件箱]")
                        || text.includes("收件箱")
                        || text.includes("project_process");
                }

                function identityMatched(text) {
                    if (!identityTokens.length) {
                        return true;
                    }
                    const matchedCount = identityTokens.filter((token) => text.includes(token)).length;
                    const requiredCount = identityTokens.length >= 2 ? 2 : 1;
                    return matchedCount >= requiredCount;
                }

                function clickableTarget(element) {
                    let current = element;
                    let depth = 0;
                    while (current && current !== document.body && depth < 8) {
                        if (visible(current)) {
                            if (current.matches("a,button,[role='button'],[role='link'],[role='row'],tr,li,[class*='mail'],[class*='Mail'],[class*='result'],[class*='Result'],[class*='subject'],[class*='Subject'],[class*='title'],[class*='Title']")) {
                                return current;
                            }
                            const style = window.getComputedStyle(current);
                            if (style.cursor === "pointer" || current.onclick) {
                                return current;
                            }
                        }
                        current = current.parentElement;
                        depth += 1;
                    }
                    return element;
                }

                let best = null;
                let bestScore = -1;

                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    {
                        acceptNode(node) {
                            const text = normalize(node.nodeValue);
                            if (!text || !tokens.some((token) => text.includes(token))) {
                                return NodeFilter.FILTER_REJECT;
                            }
                            return NodeFilter.FILTER_ACCEPT;
                        }
                    }
                );

                let node = walker.nextNode();
                while (node) {
                    const nodeText = normalize(node.nodeValue);
                    const parent = node.parentElement;
                    if (!parent || !visible(parent)) {
                        node = walker.nextNode();
                        continue;
                    }

                    const matchedTokens = tokens.filter((token) => nodeText.includes(token));
                    let ancestor = parent;
                    let depth = 0;
                    while (ancestor && ancestor !== document.body && depth < 8) {
                        if (visible(ancestor)) {
                            const contextText = normalize(ancestor.innerText || ancestor.textContent);
                            if (contextText && contextText.length <= 900) {
                                if (!identityMatched(contextText)) {
                                    ancestor = ancestor.parentElement;
                                    depth += 1;
                                    continue;
                                }

                                const hasMailbox = mailboxContext(contextText);
                                const hasBadHint = badSearchHint(contextText);
                                if (!hasBadHint || hasMailbox) {
                                    let score = 0;
                                    score += matchedTokens.reduce((sum, token) => sum + token.length * 3, 0);
                                    if (nodeText.includes(tokens[0])) score += 260;
                                    if (contextText.includes(tokens[0])) score += 160;
                                    if (hasMailbox) score += 500;
                                    if (contextText.includes("project_process")) score += 160;
                                    if (contextText.includes("[收件箱]")) score += 180;
                                    if (!hasBadHint) score += 120;
                                    if (ancestor.matches("span,a,td,tr,li,[role='row']")) score += 80;
                                    score += Math.max(0, 320 - contextText.length);
                                    score -= depth * 25;

                                    const target = clickableTarget(ancestor);
                                    if (score > bestScore) {
                                        best = {
                                            element: target,
                                            text: contextText,
                                            nodeText,
                                            score
                                        };
                                        bestScore = score;
                                    }
                                }
                            }
                        }
                        ancestor = ancestor.parentElement;
                        depth += 1;
                    }

                    node = walker.nextNode();
                }

                if (!best) {
                    return { found: false };
                }

                best.element.setAttribute("data-mail-auto-result-target", marker);
                return {
                    found: true,
                    text: best.text.slice(0, 260),
                    nodeText: best.nodeText.slice(0, 260),
                    tag: best.element.tagName,
                    score: best.score
                };
            }
            """,
            {
                "tokens": _keyword_tokens(keyword),
                "identityTokens": _identity_tokens(keyword),
                "marker": marker,
            },
        )

        if not result or not result.get("found"):
            return False

        self._log(f"定位到搜索结果标题文本: {result.get('nodeText')}")
        target = self.page.locator(f'[data-mail-auto-result-target="{marker}"]').first
        target.wait_for(state="visible", timeout=self.timeout_ms)
        target.scroll_into_view_if_needed(timeout=self.timeout_ms)
        if double_click:
            target.dblclick(timeout=self.timeout_ms)
        else:
            target.click(timeout=self.timeout_ms)
        return True

    def _wait_until_detail_opened(self, keyword: str) -> bool:
        tokens = _keyword_tokens(keyword)
        identity_tokens = _identity_tokens(keyword)
        detail_selectors = _join_selectors(MAIL_DETAIL_CONTAINER_SELECTORS)
        for context in self._page_and_frames():
            if self._wait_context_has_mail_detail(context, tokens, identity_tokens, detail_selectors):
                self._detail_context = context
                url = getattr(context, "url", "")
                self._log(f"已确认进入邮件详情页: {url}")
                return True

        return False

    def _page_and_frames(self) -> list[Any]:
        contexts = [self.page]
        try:
            contexts.extend(self.page.frames)
        except Exception:
            pass
        return contexts

    def _wait_context_has_mail_detail(
        self,
        context: Any,
        tokens: list[str],
        identity_tokens: list[str],
        detail_selectors: str,
    ) -> bool:
        try:
            context.wait_for_function(
                """
                ({ tokens, identityTokens, detailSelector }) => {
                    const bodyText = (document.body && document.body.innerText || "").replace(/\\s+/g, " ");
                    const matchTokens = identityTokens.length ? identityTokens : tokens;
                    if (!bodyText || !matchTokens.some((token) => bodyText.includes(token))) {
                        return false;
                    }

                    function visible(element) {
                        const rect = element.getBoundingClientRect();
                        const style = window.getComputedStyle(element);
                        return rect.width > 20
                            && rect.height > 20
                            && style.visibility !== "hidden"
                            && style.display !== "none";
                    }

                    function containsIdentity(text) {
                        const source = (text || "").replace(/\\s+/g, " ");
                        if (!identityTokens.length) {
                            return tokens.some((token) => source.includes(token));
                        }
                        const matchedCount = identityTokens.filter((token) => source.includes(token)).length;
                        const requiredCount = identityTokens.length >= 2 ? 2 : 1;
                        return matchedCount >= requiredCount;
                    }

                    const stillSearchResultPage = /已搜索到\\s*\\d+\\s*封/.test(bodyText)
                        || bodyText.includes("继续用AI")
                        || bodyText.includes("批量操作搜索更多邮件");
                    const hasMailHeader = bodyText.includes("发件人")
                        && (bodyText.includes("收件人") || bodyText.includes("时 间") || bodyText.includes("时间"));
                    if (stillSearchResultPage && !hasMailHeader) {
                        return false;
                    }

                    if (detailSelector) {
                        const candidates = Array.from(document.querySelectorAll(detailSelector));
                        if (candidates.some((element) => {
                            const text = element.innerText || element.textContent || "";
                            return visible(element) && containsIdentity(text);
                        })) {
                            return true;
                        }
                    }

                    const strongBodyMatch = containsIdentity(bodyText);
                    if (strongBodyMatch && (!stillSearchResultPage || hasMailHeader)) {
                        return true;
                    }

                    return false;
                }
                """,
                {"tokens": tokens, "identityTokens": identity_tokens, "detailSelector": detail_selectors},
                timeout=3000,
            )
            return True
        except Exception:
            return False

    def _context_looks_like_open_mail_view(self, context: Any, keyword: str) -> bool:
        try:
            return bool(
                context.evaluate(
                    """
                    ({ identityTokens }) => {
                        const text = (document.body && document.body.innerText || "").replace(/\\s+/g, " ");
                        if (!text) {
                            return false;
                        }

                        const hasIdentity = !identityTokens.length
                            || identityTokens.some((token) => text.includes(token));
                        const hasSearchHints = /已搜索到\\s*\\d+\\s*封/.test(text)
                            || text.includes("继续用AI")
                            || text.includes("批量操作搜索更多邮件");
                        const hasMailHeader = text.includes("发件人")
                            && (text.includes("收件人") || text.includes("时 间") || text.includes("时间"));

                        return hasIdentity && hasMailHeader && !hasSearchHints;
                    }
                    """,
                    {"identityTokens": _identity_tokens(keyword)},
                )
            )
        except Exception:
            return False

    def _is_still_search_result_page(self) -> bool:
        try:
            return bool(
                self.page.evaluate(
                    """
                    () => {
                        const text = (document.body && document.body.innerText || "").replace(/\\s+/g, " ");
                        const hasSearchHints = /已搜索到\\s*\\d+\\s*封/.test(text)
                            || text.includes("继续用AI")
                            || text.includes("批量操作搜索更多邮件");
                        const hasMailHeader = text.includes("发件人")
                            && (text.includes("收件人") || text.includes("时 间") || text.includes("时间"));
                        return hasSearchHints && !hasMailHeader;
                    }
                    """
                )
            )
        except Exception:
            return False

    def _wait_for_loading_to_finish(self) -> None:
        loading_selector = _join_selectors(SEARCH_LOADING_SELECTORS)
        if loading_selector:
            try:
                self.page.locator(loading_selector).first.wait_for(
                    state="hidden",
                    timeout=self.timeout_ms,
                )
            except Exception:
                pass

        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=self.timeout_ms)
        except Exception:
            pass

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


def _keyword_tokens(keyword: str) -> list[str]:
    """Return search-result text fragments likely to appear in highlighted DOM."""

    clean_keyword = keyword.strip()
    raw_tokens = [clean_keyword]
    raw_tokens.extend(part.strip() for part in re.split(r"[_\s]+", clean_keyword) if part.strip())

    tokens: list[str] = []
    for token in raw_tokens:
        if len(token) < 3 and not _has_cjk(token):
            continue
        if token not in tokens:
            tokens.append(token)

    tokens.sort(key=len, reverse=True)
    return tokens[:8]


def _identity_tokens(keyword: str) -> list[str]:
    """Return fragments that identify one mail better than generic subject words."""

    clean_keyword = keyword.strip()
    raw_parts = [part.strip() for part in re.split(r"[_\s]+", clean_keyword) if part.strip()]

    tokens: list[str] = []
    if clean_keyword:
        tokens.append(clean_keyword)

    for part in raw_parts:
        upper_part = part.upper()
        has_digit = any(char.isdigit() for char in part)
        has_cjk = _has_cjk(part)
        looks_like_code = bool(re.search(r"[A-Z]{1,}-[A-Z0-9-]{6,}", upper_part))

        if looks_like_code or (has_digit and len(part) >= 8) or (has_cjk and len(part) >= 3 and part != "结题通知"):
            if part not in tokens:
                tokens.append(part)

    tokens.sort(key=len, reverse=True)
    return tokens[:6]


def _escape_css_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)
