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
    "input[title*='搜索']",
    "input[class*='search']",
    "input[id*='search']",
    "[role='searchbox']",
    "[contenteditable='true'][aria-label*='搜索']",
)

SEARCH_BUTTON_SELECTORS = (
    "button[aria-label*='搜索']",
    "button[title*='搜索']",
    "[title*='搜索']",
    "[role='button'][aria-label*='搜索']",
    "[class*='search'][role='button']",
)

SEARCH_RESULT_AREA_SELECTORS = (
    "[id*='dvContainer']",
    "[class*='mail-list']",
    "[class*='mailList']",
    "[class*='result']",
    "[class*='search']",
)

SEARCH_LOADING_SELECTORS = (
    "[class*='loading']",
    "[id*='loading']",
    "[aria-busy='true']",
)

MAIL_RESULT_ITEM_SELECTORS = (
    "[class*='mail-list'] [role='row']",
    "[class*='mailList'] [role='row']",
    "[class*='mail-list'] li",
    "[class*='mailList'] li",
    "[class*='result'] [role='row']",
    "[class*='result'] li",
    "tr",
)

MAIL_DETAIL_CONTAINER_SELECTORS = (
    "[class*='mail-content']",
    "[class*='mailContent']",
    "[class*='readmail']",
    "[class*='readMail']",
    "[class*='mail-detail']",
    "[class*='mailDetail']",
    "[id*='mailContent']",
    "[id*='MailContent']",
    "[id*='dvMailContent']",
    "[class*='letter']",
)

MAIL_DETAIL_TITLE_SELECTORS = (
    "[class*='subject']",
    "[class*='Subject']",
    "[id*='subject']",
    "[id*='Subject']",
    "[class*='title']",
    "[class*='Title']",
    "[role='heading']",
    "h1",
    "h2",
)

MAIL_DETAIL_QR_CODE_SELECTORS = (
    "img[alt*='二维码']",
    "img[title*='二维码']",
    "img[src*='qrcode']",
    "img[src*='QRCode']",
    "img[src*='qr']",
    "[class*='qrcode']",
    "[class*='qrCode']",
    "[id*='qrcode']",
    "[id*='QRCode']",
    "canvas",
)

MAIL_SELECTORS = {
    "login_markers": LOGIN_MARKER_SELECTORS,
    "authenticated_markers": AUTHENTICATED_MARKER_SELECTORS,
    "search_input": SEARCH_INPUT_SELECTORS,
    "search_button": SEARCH_BUTTON_SELECTORS,
    "search_result_area": SEARCH_RESULT_AREA_SELECTORS,
    "search_loading": SEARCH_LOADING_SELECTORS,
    "mail_result_item": MAIL_RESULT_ITEM_SELECTORS,
    "mail_detail_container": MAIL_DETAIL_CONTAINER_SELECTORS,
    "mail_detail_title": MAIL_DETAIL_TITLE_SELECTORS,
    "mail_detail_qr_code": MAIL_DETAIL_QR_CODE_SELECTORS,
}
