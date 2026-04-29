"""
Jarvis Telegram Commands - Plugin pour Hermes

Fournit les commandes /sync et /status pour le bot Telegram.
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


def sync_command(args: str = "") -> str:
    """/sync - Synchronise le fork avec upstream"""
    logger.info("[jarvis-telegram] /sync exécuté")
    
    commands = [
        ("git fetch upstream", "/root/hermes-agent"),
        ("git checkout main", "/root/hermes-agent"),
        ("git merge upstream/main --no-edit", "/root/hermes-agent"),
        ("git push origin main", "/root/hermes-agent"),
        ("git checkout JarvisV3", "/root/hermes-agent"),
        ("git rebase main", "/root/hermes-agent"),
        ("git push origin JarvisV3 --force-with-lease", "/root/hermes-agent"),
    ]
    
    results = []
    for cmd, cwd in commands:
        output = _run_shell(cmd, cwd)
        results.append(f"$ {cmd}\n{output}")
    
    return "🔄 **Sync JarvisV3**\n\n" + "\n\n".join(results)


def status_command(args: str = "") -> str:
    """/status - Affiche le statut du système"""
    logger.info("[jarvis-telegram] /status exécuté")
    
    # Statut git
    git_status = _run_shell("git status --short", "/root/hermes-agent")
    git_log = _run_shell("git log --oneline -5", "/root/hermes-agent")
    
    # Statut gateway
    gateway_status = _run_shell("hermes gateway status 2>&1 || echo 'Gateway non running'")
    
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

🌡️ **Temperature:** 0.6 (immutable)
"""


def register(ctx) -> None:
    """Enregistre les commandes dans Hermes"""
    ctx.register_command("sync", sync_command, description="Sync le fork avec upstream")
    ctx.register_command("status", status_command, description="Affiche le statut JarvisV3")
    logger.info("[jarvis-telegram] Commandes /sync et /status enregistrées")
