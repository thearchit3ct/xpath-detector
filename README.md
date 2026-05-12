# xpath-detector

Outil interactif de capture XPath pour applications web.

## Installation

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
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
- `quit` - quitte

Dans le navigateur :
- **Survol** : surligne l'element en rouge
- **Ctrl+clic** : capture l'element
- **Escape** : active/desactive l'overlay

## Tests

```bash
pytest
```

## Architecture

Voir `docs/plans/2026-05-12-xpath-detector-redesign.md`.
