# xpath-detector v1.1 — Design

**Date** : 2026-05-12
**Statut** : Approuve
**Cible** : Adresser tous les items deferres de v1.0.0 (I-1 a I-5, M-4, M-9, M-11)

---

## 1. Contexte

v1.0.0 a ete release avec succes. Le code reviewer final a identifie :
- 5 items Important : I-1 a I-5 (overlay target, help cmd, shell coverage, by_label_neighbor, migrate_v1)
- 3 items Minor : M-4 (DRY exporters), M-9 (console log), M-11 (escape edges)

v1.1 vise a fermer tous ces points sans introduire de nouvelles features (pas de Shadow DOM, pas de mode headless).

---

## 2. Items adresses

### I-1 — Overlay target consistency

**Probleme** : `mousemove` highlight `document.elementFromPoint(...)`, mais `click` capture `e.target`. Sur un `<button><span>Texte</span></button>` :
- Hover : highlight du button
- Click : capture du span (`e.target` = noeud terminal)
- Mismatch silencieux UX

**Fix** : dans `overlay.py`, le click handler utilise aussi `document.elementFromPoint(e.clientX, e.clientY)` au lieu de `e.target`. Coherent avec le highlight visuel.

### I-3 — Help command

**Probleme** : le shell affiche les commandes au demarrage uniquement, pas de moyen de les revoir.

**Fix** : `cmd_help(args)` dans `shell.py` qui re-affiche le greeting + un tableau rich des commandes avec description.

### I-4 — Shell coverage

**Probleme** : `shell.py` a 26% de coverage. Le `_on_capture` (pipeline metier) est non teste.

**Fix** : creer `tests/test_shell.py` avec :
- `test_load_exporters_returns_registered` : verifie qu'on a les 5 exporters
- `test_on_capture_with_no_screen_ignores` : capture ignoree si pas d'ecran courant
- `test_on_capture_adds_element_to_current_screen` : capture ajoute l'element (mock console.input)
- `test_cmd_export_all_dispatches_to_each_exporter` : export all appelle chaque exporter
- `test_cmd_export_unknown_prints_error` : message d'erreur clair

### I-5a — by_label_neighbor strategy

**Probleme** : pas de strategy pour les inputs reperes par un label visible (cas frequent dans les apps banking type vpu).

**Fix overlay** : ajouter `findNearbyLabel(el)` qui cherche :
1. `<label for="id">` via l'attribut `for`
2. Ancestor `<label>`
3. Premier `<span>`/`<label>` precedent dans les 3 niveaux d'ancetres

Renvoie le texte (max 50 chars) ou `null`. Le resultat est ajoute au payload comme `nearby_label`.

**Fix analyzer** : `generate_candidates(..., nearby_label: str | None = None)`. Si fourni, ajoute :
```python
XPathCandidate(
    strategy="by_label_neighbor",
    expression=f"//span[contains(.,{escape_xpath_literal(nearby_label)})]/../../td/{tag}",
    stability_score=50,
)
```

**Fix shell** : `_on_capture` lit `data.get("nearby_label")` et le passe a `generate_candidates`.

### I-5b — Migration script v1.0 -> v1.1

**Probleme** : sessions v1.0 ont un format different (champ `xpaths` dict, pas liste de candidates).

**Fix** : `scripts/migrate_v1.py` :

```
Usage: python scripts/migrate_v1.py <input_v1.json> <output_v11.json>
```

Mapping (best-effort) :

| Ancien champ | Strategy / Score |
|--------------|------------------|
| `xpaths.by_id` (any tag) | `by_id` / 95 |
| `xpaths.by_text` | `by_text` / 70 |
| `xpaths.by_class` | `by_class` / 60 |
| `xpaths.relative[i]` (sans pattern connu) | `legacy_relative` / 40 |
| `xpaths.absolute` | `absolute` / 10 |

Le champ `xpaths.relative` est une liste ; on garde le 1er. Strategies non reconnues vont en `legacy_relative` (score arbitraire 40). Pas de `nearby_label` retrocompatible.

### M-4 — DRY exporters

**Probleme** : `_to_constant`, `_to_pascal`, `_sanitize`, `_to_var_name` dupliques entre `java_exp.py`, `python_exp.py`, `robot_exp.py`.

**Fix** : extraire vers `src/xpath_detector/exporters/_naming.py` (module prive, prefixe underscore) :

```python
def sanitize(name: str) -> str: ...
def to_pascal(name: str) -> str: ...
def to_constant(element: Element) -> str: ...
def to_var_name(element: Element) -> str: ...
```

Importer dans les exporters. Tests directs sur ces 4 fonctions.

### M-9 — Console logging

**Probleme** : `__main__.py` configure uniquement `filename="xpath_detector.log"`. Les erreurs WARNING+ ne sont pas visibles dans le terminal.

**Fix** : configurer le logging avec 2 handlers :
```python
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("xpath_detector.log"),
        logging.StreamHandler(),  # stderr, level WARNING par defaut sur le handler
    ],
)
logging.getLogger().handlers[1].setLevel(logging.WARNING)
```

### M-11 — Escape edges

**Probleme** : `escape_xpath_literal` n'a que 2 tests (sans apostrophe, avec apostrophe simple).

**Fix** : ajouter 4 tests pour :
- `""` -> `"''"`
- `"'"` (juste une apostrophe) -> `concat('', \"'\", '')`
- `"'x'"` -> `concat('', \"'\", 'x', \"'\", '')`
- `"x''y"` -> 2 apostrophes consecutives

---

## 3. Strategie de tests

### Tests JS overlay

Le JS reste teste structurellement (string contains). Pas de moyen simple de tester l'algorithme `findNearbyLabel` sans navigateur. Trade-off accepte pour eviter de devoir installer jsdom / pyppeteer.

### Tests unit shell (nouveaux)

Utiliser `unittest.mock.patch` pour :
- Mocker `Console.input` (retourne une description fixe)
- Mocker `BrowserController` (pour eviter de lancer Playwright)

```python
@patch("xpath_detector.shell.BrowserController")
def test_on_capture_adds_element(mock_browser_class):
    shell = Shell()
    shell.current_screen = "test"
    shell.session.screens["test"] = Screen(...)
    shell._on_capture({"tag": "input", "attributes": {"id": "x"}})
    assert len(shell.session.screens["test"].elements) == 1
```

### Migration script

Test sur fixture `tests/fixtures/session_v1.json` (sample v1.0 minimal).

---

## 4. Compatibilite

- Sessions v1.0 doivent etre **lues** sans casse (le `Element.from_dict` gere bien les xpaths reduits). Mais elles n'ont pas de scoring. Migration recommandee.
- Format v1.1 reste retrocompatible : ajouter `nearby_label` optionnel ne casse pas les sessions sans ce champ.
- API publique inchangee : `Shell`, exporters, etc.

---

## 5. Livrables et metriques

- **Commits** : ~10 atomiques
- **Tests** : +8 a +10 (shell, analyzer edge, naming, migrate)
- **Coverage shell** : 26% -> 60%+
- **Tag** : v1.1.0 (cree + pushe + release GitHub)
- **CHANGELOG.md** : nouveau, listant les items adresses

---

## 6. Hors scope (a v1.2 ou plus tard)

- Shadow DOM support (M de la review)
- Mode headless / CLI batch
- Element.attributes immutable (`MappingProxyType`)
- Coverage 80%+ generale
- Integration tests Playwright

---

## 7. Prochaines etapes

Apres validation, invoquer `superpowers:writing-plans` pour generer un plan TDD detaille phase par phase.
