from datetime import datetime
from pathlib import Path

from pkg_upgrade._subprocess import run_command


class Notifier:
    def __init__(self, log_path: str | None, notify: bool = True) -> None:
        self.log_path = log_path
        self.notify = notify
        if self.log_path:
            Path(self.log_path).touch()

    def log(self, manager_key: str, message: str) -> None:
        if not self.log_path:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"{ts}  {manager_key:8s}  {message}\n"
        with Path(self.log_path).open("a") as f:
            f.write(line)

    async def send_notification(self, title: str, body: str) -> None:
        if not self.notify:
            return
        # AppleScript strings need backslash AND double-quote escaping.
        safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
        safe_body = body.replace("\\", "\\\\").replace('"', '\\"')
        script = f'display notification "{safe_body}" with title "{safe_title}"'
        await run_command(["osascript", "-e", script])
