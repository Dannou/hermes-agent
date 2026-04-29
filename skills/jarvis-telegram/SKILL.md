---
name: jarvis-telegram
description: Commandes Telegram personnalisées pour JarvisV3 - /sync et /status
version: 1.0.0
author: Dannou
enabled: true
---

# Jarvis Telegram Commands

Commandes personnalisées pour le bot Telegram Jarvisfather.

## /sync

Synchronise le fork JarvisV3 avec le repo officiel hermes-agent.

```bash
cd /root/hermes-agent && git fetch upstream && git checkout main && git merge upstream/main && git push origin main && git checkout JarvisV3 && git rebase main && git push origin JarvisV3 --force-with-lease
```

## /status

Affiche le statut du système JarvisV3.

```bash
echo "=== JarvisV3 Status ===" && cd /root/hermes-agent && git status && echo "---" && git log --oneline -5 && echo "---" && hermes gateway status
```

## Temperature Rule (IMMUTABLE)

**La temperature du modèle DOIT toujours rester à 0.6.**
C'est une exigence non-négociable de kimi-for-code.
