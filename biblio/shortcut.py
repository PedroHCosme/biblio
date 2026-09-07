"""Cria o .lnk via PowerShell e instala a skill. ponytail: sem pywin32, o Windows ja tem COM."""
import subprocess
import sys
from pathlib import Path

from biblio import skill

SCRIPT = """
$a = (New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}')
$a.TargetPath = '{alvo}'
$a.Arguments = '-m biblio.cli gui'
$a.WorkingDirectory = '{trabalho}'
$a.Description = 'biblio - ingestao de documentos'
$a.Save()
"""


def criar() -> Path | None:
    skill.instalar()  # instalacao manual de skill e um passo que o usuario esquece
    if sys.platform != "win32":
        # ponytail: atalho e conveniencia de Windows; o resto do produto e portatil
        print("Atalho so no Windows. Nos outros sistemas, rode `biblio gui`.")
        return None
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():  # console preto e feio, mas melhor que atalho quebrado
        pythonw = Path(sys.executable)
    lnk = Path.home() / "Desktop" / "biblio.lnk"
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         SCRIPT.format(lnk=lnk, alvo=pythonw, trabalho=Path.home())],
        check=True,
    )
    return lnk
