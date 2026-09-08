"""Creates the .lnk via PowerShell and installs the skill. ponytail: no pywin32."""
import subprocess
import sys
from pathlib import Path

from biblio import skill

SCRIPT = """
$a = (New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}')
$a.TargetPath = '{target}'
$a.Arguments = '-m biblio.cli gui'
$a.WorkingDirectory = '{workdir}'
$a.Description = 'biblio - document ingestion'
$a.Save()
"""


def create() -> Path | None:
    skill.install()
    if sys.platform != "win32":
        print("Shortcut is Windows-only. On other systems, run `biblio gui`.")
        return None
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = Path(sys.executable)
    lnk = Path.home() / "Desktop" / "biblio.lnk"
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         SCRIPT.format(lnk=lnk, target=pythonw, workdir=Path.home())],
        check=True,
    )
    return lnk
