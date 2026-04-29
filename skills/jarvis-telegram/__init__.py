"""
Jarvis Telegram Commands Plugin

Fournit les commandes /sync et /status pour le bot Telegram Jarvisfather.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def _run_shell(command: str, cwd: Optional[str] = None) -> str:
    """Exécute une commande shell et retourne la sortie."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=cwd,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return f"Erreur (code {result.returncode}): {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "Timeout - la commande a pris trop de temps"
    except Exception as e:
        return f"Exception: {str(e)}"


def sync_command() -> str:
    """/sync - Synchronise le fork avec upstream"""
    logger.info("[jarvis-telegram] /sync exécuté")
    
    commands = [
        "cd /root/hermes-agent",
        "git fetch upstream",
        "git checkout main",
        "git merge upstream/main --no-edit",
        "git push origin main",
        "git checkout JarvisV3",
        "git rebase main",
        "git push origin JarvisV3 --force-with-lease",
    ]
    
    results = []
    for cmd in commands:
        output = _run_shell(cmd)
        results.append(f"$ {cmd}\n{output}")
    
    return "🔄 **Sync JarvisV3**\n\n" + "\n\n".join(results)


def status_command() -> str:
    """/status - Affiche le statut du système"""
    logger.info("[jarvis-telegram] /status exécuté")
    
    # Statut git
    git_status = _run_shell("cd /root/hermes-agent && git status --short")
    git_log = _run_shell("cd /root/hermes-agent && git log --oneline -5")
    
    # Statut gateway
    gateway_status = _run_shell("hermes gateway status 2>&1 || echo 'Gateway non running'")
    
    # Statut cron
    cron_list = _run_shell("hermes cron list 2>&1 || echo 'Cron non disponible'")
    
    return f"""📊 **Status JarvisV3**

**Git Status:**
```
{git_status or 'Working tree clean'}
```

**Derniers commits:**
```
{git_log}
```

**Gateway:**
```
{gateway_status}
```

**Cron Jobs:**
```
{cron_list}
```

🌡️ **Temperature:** 0.6 (immutable)
"""


def register(ctx) -> None:
    """Enregistre les commandes dans Hermes"""
    ctx.register_command("sync", sync_command, description="Sync le fork avec upstream")
    ctx.register_command("status", status_command, description="Affiche le statut JarvisV3")
    logger.info("[jarvis-telegram] Commandes /sync et /status enregistrées")
