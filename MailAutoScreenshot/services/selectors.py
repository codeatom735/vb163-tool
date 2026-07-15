"""Centralized selectors for the 163 mail web UI.

163 Mail changes its DOM over time. Keep all selectors in this module so page
changes can be handled without rewriting service logic.
"""


LOGIN_URL_KEYWORDS = (
    "mail.163.com",
    "reg.163.com",
    "dl.reg.163.com",
)

AUTHENTICATED_URL_KEYWORDS = (
    "/js6/main.jsp",
    "/jy6/main.jsp",
    "/mailbox",
)

LOGIN_MARKER_SELECTORS = (
    "iframe[id*='URS']",
    "iframe[src*='reg.163.com']",
    "iframe[src*='dl.reg.163.com']",
    "input[name='email']",
    "input[name='password']",
    "input[type='password']",
    "[id*='login']",
    "[class*='login']",
)

AUTHENTICATED_MARKER_SELECTORS = (
    "input[placeholder*='搜索']",
    "input[aria-label*='搜索']",
    "[role='searchbox']",
    "[title*='写信']",
    "[aria-label*='写信']",
    "a[href*='logout']",
    "[id*='spnUid']",
    "[id*='dvNavTop']",
)

SEARCH_INPUT_SELECTORS = (
    "input[placeholder*='搜索']",
    "input[aria-label*='搜索']",
    "[role='searchbox']",
)

SEARCH_BUTTON_SELECTORS = (
    "button[aria-label*='搜索']",
    "[title*='搜索']",
    "[role='button'][aria-label*='搜索']",
)

SEARCH_RESULT_AREA_SELECTORS = (
    "[id*='dvContainer']",
    "[class*='mail-list']",
    "[class*='search']",
)

MAIL_SELECTORS = {
    "login_markers": LOGIN_MARKER_SELECTORS,
    "authenticated_markers": AUTHENTICATED_MARKER_SELECTORS,
    "search_input": SEARCH_INPUT_SELECTORS,
    "search_button": SEARCH_BUTTON_SELECTORS,
    "search_result_area": SEARCH_RESULT_AREA_SELECTORS,
}
