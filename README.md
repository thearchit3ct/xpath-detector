# xpath-detector

Outil interactif de capture XPath pour applications web. Supporte Selenium (defaut) ou Playwright (optionnel).

## Installation

Default install (Selenium backend, recommande pour environnements corporate):

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Selenium utilise le Chrome systeme — aucun download de binaire supplementaire.

### Optionnel : Playwright backend

Si tu prefere Playwright (plus rapide, plus de features) et que tu peux telecharger Chromium :

```bash
pip install -e ".[dev,playwright]"
playwright install chromium
```

## Usage

```bash
python -m xpath_detector
```

Commandes :
- `open <url>` - ouvre une URL
- `screen <name>` - cree/bascule sur un ecran
- `list` - liste les ecrans
- `show` - affiche les elements de l'ecran courant
- `export <format>` - exporte (json/html/robot/java/python/all)
- `save` - sauvegarde la session JSON
- `load <path>` - recharge une session
- `help` - affiche la liste des commandes
- `quit` - quitte

Dans le navigateur :
- **Survol** : surligne l'element en rouge
- **Ctrl+clic** : capture l'element
- **Escape** : active/desactive l'overlay

## Choosing a backend

Par defaut, xpath-detector utilise Selenium. Pour basculer sur Playwright :

```bash
export XPATH_DETECTOR_BACKEND=playwright
python -m xpath_detector
```

Valeurs supportees : `selenium` (defaut), `playwright` (necessite l'extra `[playwright]`).

## Tests

```bash
pytest
```

## Architecture

Voir `docs/plans/2026-05-12-xpath-detector-redesign.md`.
