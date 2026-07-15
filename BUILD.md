# Build MailAutoScreenshot.exe

## Environment

- Windows 10/11
- Python 3.11+
- Google Chrome installed

## Install Dependencies

```powershell
py -3.11 -m pip install -r requirements.txt
```

## Run From Source

```powershell
py -3.11 MailAutoScreenshot/main.py
```

## Build EXE

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1
```

If dependencies are already installed:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1 -SkipInstall
```

The output file is:

```text
dist/MailAutoScreenshot.exe
```

## Runtime Files

The EXE creates or updates these folders next to the executable:

```text
config/config.json
logs/app.log
```

Default browser profile:

```text
C:/MailAutoProfile
```

Default screenshot directory:

```text
D:/MailScreenshot
```
