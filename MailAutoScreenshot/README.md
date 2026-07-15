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
