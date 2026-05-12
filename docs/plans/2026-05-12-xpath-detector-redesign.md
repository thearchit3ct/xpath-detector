# Refonte xpath-detector — Design

**Date** : 2026-05-12
**Statut** : Approuve
**Cible** : Outil generique de capture xpath multi-framework

---

## 1. Contexte

L'outil actuel (`xpath_detective.py` + `interactive_shell.py`, 1 119 lignes Python) presente plusieurs bugs critiques identifies lors de l'audit :

- Menu casse (option Export inaccessible, option Quitter mal mappee)
- `switch_to.active_element` ne capture pas l'element clique mais l'element focused
- `os.startfile()` Windows-only
- XSS dans le rapport HTML (pas d'echappement)
- XPath generes non echappes (apostrophes)
- `except:` nus, pas de tests, pas de logging

La refonte vise un outil **production-ready** generique, utilisable pour n'importe quelle application web, avec exports multi-frameworks.

---

## 2. Decisions de design

| # | Sujet | Choix |
|---|-------|-------|
| 1 | Usage | Generique (n'importe quelle app web) |
| 2 | Execution | Shell interactif uniquement |
| 3 | Capture clics | Highlight on hover + clic = capture (Ctrl-clic pour eviter conflits) |
| 4 | Exports | JSON + HTML + Robot Framework + Java/Selenium + Python/Selenium |
| 5 | Concurrence | Playwright sync |
| 6 | Outillage | pyproject.toml (uv) + pytest + ruff + black + pre-commit |

---

## 3. Architecture

### Structure du projet

```
xpath_detector/
├── pyproject.toml
├── README.md
├── .pre-commit-config.yaml
├── src/
│   └── xpath_detector/
│       ├── __init__.py
│       ├── __main__.py
│       ├── models.py
│       ├── browser.py
│       ├── overlay.py
│       ├── analyzer.py
│       ├── shell.py
│       ├── session.py
│       └── exporters/
│           ├── __init__.py
│           ├── base.py
│           ├── json_exp.py
│           ├── html_exp.py
│           ├── robot_exp.py
│           ├── java_exp.py
│           └── python_exp.py
├── tests/
│   ├── conftest.py
│   ├── test_analyzer.py
│   ├── test_session.py
│   ├── test_exporters.py
│   └── fixtures/
│       └── sample.html
└── docs/
    └── plans/
        └── 2026-05-12-xpath-detector-redesign.md
```

### Modules cles

#### `models.py`

Dataclasses immutables, base de toute la chaine de traitement :

```python
@dataclass(frozen=True)
class XPathCandidate:
    strategy: str
    expression: str
    stability_score: int  # 0-100

@dataclass
class Element:
    tag: str
    text: str | None
    attributes: dict[str, str]
    xpaths: list[XPathCandidate]
    is_visible: bool
    is_enabled: bool
    description: str

@dataclass
class Screen:
    name: str
    url: str
    title: str
    timestamp: datetime
    elements: list[Element]

@dataclass
class Session:
    id: str
    screens: dict[str, Screen]
```

#### `browser.py`

Wrapper Playwright sync, encapsule :
- Lancement Chromium
- Navigation
- Injection du script `overlay.py`
- Lecture des messages console (canal de communication overlay -> Python)

#### `overlay.py`

Script JS injecte dans la page cible. Comportement :

1. **Hover** : ajoute classe CSS `__xpath_detector_highlight` (bordure rouge + tooltip) sur l'element survole
2. **Ctrl+clic** :
   - `event.preventDefault()` + `event.stopPropagation()`
   - Serialize l'element en JSON (tag, attrs, text, outerHTML)
   - Envoie via `console.log("__XPATH_CAPTURE__" + JSON.stringify(data))`
3. **Touche `Esc`** : desactive temporairement l'overlay pour permettre la navigation normale

Le canal `console.log` evite la complexite d'un serveur WebSocket local.

#### `analyzer.py`

Genere les candidats xpath avec score de stabilite. Strategies :

| Strategie | Score | Pattern xpath | Condition |
|-----------|:-----:|---------------|-----------|
| by_id | 95 | `//tag[@id='X']` | id present, unique |
| by_data_testid | 90 | `//tag[@data-testid='X']` | data-testid present |
| by_name | 80 | `//tag[@name='X']` | name present |
| by_aria_label | 75 | `//tag[@aria-label='X']` | aria-label present |
| by_text | 70 | `//tag[contains(.,'X')]` | texte court (<50) et unique |
| by_class | 60 | `//tag[contains(@class,'X')]` | classe non generique |
| by_label_neighbor | 50 | `//span[contains(.,'Label')]/../../td/input` | input avec label visible |
| absolute | 10 | `/html/body/.../tag[n]` | fallback |

Toutes les expressions echappent les apostrophes via la technique `concat()` XPath 1.0.

#### `shell.py`

Boucle interactive avec [rich](https://rich.readthedocs.io/) :

- Couleurs ANSI (pas d'emojis)
- Tableaux pour la liste des ecrans
- Spinner pendant chargements
- Syntax highlight pour les xpath captures

Commandes :

| Commande | Description |
|----------|-------------|
| `open <url>` | Demarre une session sur une URL |
| `screen <nom>` | Cree/bascule sur un ecran |
| `list` | Liste les ecrans et nombre d'elements |
| `show` | Affiche les elements de l'ecran courant |
| `export <format>` | Exporte vers un format (json/html/robot/java/python/all) |
| `save` | Sauvegarde la session |
| `load <path>` | Recharge une session |
| `quit` | Quitte (ferme Playwright) |

#### `exporters/base.py`

```python
class Exporter(ABC):
    name: str
    extension: str

    @abstractmethod
    def export(self, session: Session, output_dir: Path) -> Path:
        ...
```

Chaque exporter implementation independante. Le registry `EXPORTERS: dict[str, Exporter]` est peuple via `importlib.metadata.entry_points` (declaration dans `pyproject.toml`).

---

## 4. Flux de capture detaille

```
1. User -> shell : "open https://app.exemple.fr"
2. Shell -> Browser : page.goto(url)
3. Browser -> Page : injecte overlay.js
4. Page -> User : navigateur Chromium s'ouvre
5. User -> Page : navigue manuellement (login, etc.)
6. User -> Page : Ctrl+clic sur un bouton
7. Page -> Console : log("__XPATH_CAPTURE__" + JSON)
8. Shell (listener) : intercepte le message
9. Shell -> User : "Description ? > "
10. User -> Shell : "Bouton Valider"
11. Shell -> Analyzer : genere xpaths candidats
12. Shell -> Session : ajoute Element au Screen courant
13. Shell -> User : affiche xpath retenu + score
```

---

## 5. Persistance

Format JSON unique, sauvegarde par defaut dans `sessions/<session_id>.json` :

```json
{
  "id": "20260512_143022",
  "screens": {
    "login": {
      "name": "login",
      "url": "https://app.exemple.fr/login",
      "title": "Login",
      "timestamp": "2026-05-12T14:30:22",
      "elements": [
        {
          "tag": "input",
          "text": null,
          "attributes": {"id": "_login", "type": "text"},
          "xpaths": [
            {"strategy": "by_id", "expression": "//input[@id='_login']", "stability_score": 95}
          ],
          "is_visible": true,
          "is_enabled": true,
          "description": "Champ Login"
        }
      ]
    }
  }
}
```

Compatible re-export depuis une session sauvegardee (utile pour iteration sur les formats).

---

## 6. Gestion d'erreurs

| Cas | Comportement |
|-----|--------------|
| URL invalide | Catch `PlaywrightError`, message clair, retour au prompt |
| Navigateur ferme par l'user | Detection, message, possibilite de relancer |
| Element disparait (DOM change) | Capture quand meme via serialisation immediate en JS |
| Erreur d'export | Log + message, sauvegarde session de toute facon |
| Apostrophes dans texte/attributs | Echappement xpath via `concat()` |

**Logging** : module `logging` standard. Niveaux DEBUG/INFO/WARNING/ERROR. Output console (INFO+) et fichier `xpath_detector.log` (DEBUG+).

---

## 7. Strategie de test

### Tests unitaires (priorite haute)

| Module | Tests |
|--------|-------|
| `analyzer.py` | Generation xpath, scoring, echappement apostrophes, stabilite |
| `models.py` | Serialisation/deserialisation JSON, validation |
| `session.py` | Save/load, fusion d'elements, renommage d'ecran |
| `exporters/*.py` | Output exact attendu pour une session fixture |

### Tests d'integration (priorite moyenne)

Hors scope du choix B mais a noter :
- Lancer Playwright sur `tests/fixtures/sample.html` (page statique locale)
- Verifier que l'overlay s'injecte et envoie bien les messages

### Couverture cible : > 70%

---

## 8. pyproject.toml (extrait)

```toml
[project]
name = "xpath-detector"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "playwright>=1.40",
    "rich>=13.0",
    "click>=8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "ruff>=0.4",
    "black>=24.0",
    "pre-commit>=3.0",
]

[project.scripts]
xpath-detector = "xpath_detector.__main__:main"

[project.entry-points."xpath_detector.exporters"]
json = "xpath_detector.exporters.json_exp:JsonExporter"
html = "xpath_detector.exporters.html_exp:HtmlExporter"
robot = "xpath_detector.exporters.robot_exp:RobotExporter"
java = "xpath_detector.exporters.java_exp:JavaExporter"
python = "xpath_detector.exporters.python_exp:PythonExporter"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.black]
line-length = 100

[tool.pytest.ini_options]
addopts = "--cov=xpath_detector --cov-report=term-missing"
```

---

## 9. Migrations depuis l'ancien outil

L'ancien outil utilise un format JSON different. Un script `scripts/migrate_v1.py` permettra de convertir une session de l'ancien format vers le nouveau (best-effort, certains scores devront etre recalcules).

---

## 10. Risques et mitigations

| Risque | Impact | Mitigation |
|--------|:------:|------------|
| Playwright pas installable sur poste entreprise (proxy) | Eleve | Documenter `playwright install chromium` + variables proxy |
| Communication console.log limitee en taille | Moyen | Chunking JSON si > 8 Ko (peu probable pour un element) |
| Ctrl+clic intercepte par l'app | Faible | Touche configurable (defaut Ctrl, fallback Alt) |
| Pages avec Shadow DOM | Moyen | Documenter limitation, ajouter strategie shadow plus tard |

---

## 11. Hors scope (YAGNI)

- Capture multi-frame (iframes) — ajoute en v1.1 si besoin
- Mode headless — l'outil est interactif par nature
- Replay de session — pas demande
- GUI desktop — shell suffit
- API REST — pas demande

---

## 12. Prochaines etapes

Apres validation de ce design, invoquer `superpowers:writing-plans` pour generer le plan d'implementation phase par phase.
