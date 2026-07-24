# Printers Monitoring

MVP web application for monitoring HP printers.

## Stack

- Python
- FastAPI
- SQLite
- SNMP
- APScheduler
- SMTP

## Development

Run the application from the project directory:

```powershell
.\.venv\Scripts\python.exe run.py
```

Then open http://127.0.0.1:8000.

## Windows build

Create a standalone Windows application:

```powershell
.\build.ps1
```

The executable will be created at:

```text
dist\PrintersMonitoring\PrintersMonitoring.exe
```

When moving the application to another computer, copy the entire
`dist\PrintersMonitoring` directory. Python and VS Code are not required on the
target computer. The SQLite database is stored in the `data` subdirectory next
to the executable.
