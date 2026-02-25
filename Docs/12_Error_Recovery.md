# Error States & Recovery

Autonomous systems will fail. Plan for it.

## 7.1 Error Categories

| Category | Examples | Recovery Strategy |
| :--- | :--- | :--- |
| Transient | Network timeout, API rate limit | Exponential backoff retry |
| Authentication | Expired token, revoked access | Alert human, pause operations |
| Logic | Claude misinterprets message | Human review queue |
| Data | Corrupted file, missing field | Quarantine + alert |
| System | Orchestrator crash, disk full | Watchdog + auto-restart |

## 7.2 Retry Logic

```python
# retry_handler.py
import time
from functools import wraps

def with_retry(max_attempts=3, base_delay=1, max_delay=60):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except TransientError as e:
                    if attempt == max_attempts - 1:
                        raise
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(f'Attempt {attempt+1} failed, retrying in {delay}s')
                    time.sleep(delay)
        return wrapper
    return decorator
```

## 7.3 Graceful Degradation

When components fail, the system should degrade gracefully:

- **Gmail API down:** Queue outgoing emails locally, process when restored
- **Banking API timeout:** Never retry payments automatically, always require fresh approval
- **Claude Code unavailable:** Watchers continue collecting, queue grows for later processing
- **Obsidian vault locked:** Write to temporary folder, sync when available

## 7.4 Watchdog Process

```python
# watchdog.py - Monitor and restart critical processes
import subprocess
import time
from pathlib import Path

PROCESSES = {
    'orchestrator': 'python orchestrator.py',
    'gmail_watcher': 'python gmail_watcher.py',
    'file_watcher': 'python filesystem_watcher.py'
}

def check_and_restart():
    for name, cmd in PROCESSES.items():
        pid_file = Path(f'/tmp/{name}.pid')
        if not is_process_running(pid_file):
            logger.warning(f'{name} not running, restarting...')
            proc = subprocess.Popen(cmd.split())
            pid_file.write_text(str(proc.pid))
            notify_human(f'{name} was restarted')

while True:
    check_and_restart()
    time.sleep(60)
```
