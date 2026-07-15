# MailAutoScreenshot

163 mail automatic search and screenshot tool.

## Stage 1

This stage creates the maintainable project structure only.

## Stage 2

This stage implements the PySide6 desktop shell:

- Excel file selector
- Screenshot save directory selector
- Chrome profile directory selector
- Start, pause, resume, and stop buttons
- Total, current, success, and failed counters
- Progress bar
- Real-time log panel
- UI signals for later task-service integration

## Stage 3

This stage implements configuration loading and saving:

- Reads `config/config.json` on startup
- Creates the config file with defaults if it is missing
- Validates and normalizes `timeout`
- Loads the default screenshot save path into the GUI
- Loads the Chrome persistent profile directory into the GUI
- Saves changed save/profile paths back to `config/config.json`

## Stage 4

This stage implements the Playwright browser wrapper:

- Uses `chromium.launch_persistent_context`
- Stores browser data in `chrome_profile`, such as `C:/MailAutoProfile`
- Opens real Chrome through the `chrome` channel
- Keeps cookies and login state between runs
- Provides `start`, `open_url`, `get_page`, `get_context`, and `close`
- Avoids fixed sleeps; later services will use locators and wait APIs

## Stage 5

This stage implements 163 login detection:

- Opens 163 mail
- Detects whether the mailbox main page is already logged in
- Detects login pages/forms without entering credentials
- Waits for the user to complete QR/manual login
- Uses Playwright locator `wait_for` instead of fixed sleeps
- Keeps all 163 selectors centralized in `services/selectors.py`

## Stage 6

This stage implements Excel reading:

- Uses `openpyxl`
- Reads the first worksheet by default
- Reads the first column as mail names
- Filters empty rows
- Converts cell values to trimmed strings
- Returns `list[str]`
- Handles missing files, unsupported formats, missing sheets, and empty data

## Stage 7

This stage implements mail search:

- Locates the 163 search input with centralized selectors
- Fills the mail name keyword
- Clicks the search button when available
- Falls back to pressing Enter from the search input
- Waits for loading/result indicators with Playwright wait APIs
- Returns a structured `MailSearchResult`
- Does not use mouse coordinates or fixed sleeps

## Stage 8

This stage implements screenshot saving:

- Opens a searched mail detail page before screenshot capture
- Saves PNG files with the original Excel mail name
- Does not add an index prefix such as `001_`
- Replaces only Windows-illegal filename characters
- Prefers clipping from the mail title to the bottom QR code
- Falls back to the mail detail container
- Falls back to a full-page screenshot
- Validates PNG output with Pillow

## Stage 9

This stage implements background task scheduling:

- Runs the full workflow in a background thread
- Keeps the PySide6 GUI responsive
- Supports start, pause, resume, and stop
- Reads Excel mail names
- Starts the persistent Chrome browser
- Waits for manual 163 login when needed
- Searches and opens each mail
- Saves screenshots using the Excel mail name
- Continues after per-item failures
- Emits real-time logs and progress to the GUI through Qt signals
- Generates `task_report_YYYYMMDD_HHMMSS.csv` in the screenshot directory
- Writes runtime logs to `logs/app.log`

Business logic will be implemented stage by stage:

- Stage 2: PySide6 GUI
- Stage 3: Configuration loading
- Stage 4: Playwright browser wrapper
- Stage 5: 163 login detection
- Stage 6: Excel reading
- Stage 7: Mail search
- Stage 8: Screenshot saving
- Stage 9: Task scheduling
- Stage 10: EXE packaging

## Run Structure Check

```powershell
python -m py_compile MailAutoScreenshot/main.py
```

## Run GUI

Install dependencies first:

```powershell
pip install -r requirements.txt
```

Then run:

```powershell
python MailAutoScreenshot/main.py
```
