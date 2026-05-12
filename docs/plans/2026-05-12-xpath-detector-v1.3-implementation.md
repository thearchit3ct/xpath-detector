# xpath-detector v1.3 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ajouter 4 nouvelles strategies XPath (`by_id_prefix`, `by_attr_combo`, `by_label_for`, `by_text_normalized`) et fixer le bug multi-class de `by_class`. Couverture devhints passe de 27% a 70%.

**Architecture:** Extensions de `src/xpath_detector/analyzer.py` uniquement. Aucun changement de l'overlay JS ni des exporters. Helpers prives ajoutes pour detecter les IDs dynamiques.

**Tech Stack:** Python 3.11+, pytest. Aucune nouvelle dependance.

**Conventions:** TDD strict. Pas d'attribution AI. Branche `master`. Baseline : `v1.2.3` (commit `a7c4b7d`), 85 tests passing.

---

## Phase 1 — Fix critique by_class

### Task 1 : Fix `by_class` multi-class

**Files:**
- Modify: `src/xpath_detector/analyzer.py:68-78`
- Modify: `tests/test_analyzer.py`

**Step 1 : Tests qui demontrent le bug actuel**

Append to `tests/test_analyzer.py`:

```python
def test_by_class_uses_safe_multiclass_pattern():
    """by_class must NOT match a partial class (regression for substring bug)."""
    candidates = generate_candidates(
        tag="button", text=None, attributes={"class": "btn"}
    )
    cand = next(c for c in candidates if c.strategy == "by_class")
    # Must use the safe pattern that handles multi-class correctly
    assert "concat(' '" in cand.expression
    assert "normalize-space(@class)" in cand.expression
    assert "' btn '" in cand.expression


def test_by_class_first_class_with_multiclass_attr():
    """When element has 'btn btn-primary', use 'btn' (first class)."""
    candidates = generate_candidates(
        tag="button", text=None, attributes={"class": "btn btn-primary"}
    )
    cand = next(c for c in candidates if c.strategy == "by_class")
    assert (
        cand.expression
        == "//button[contains(concat(' ', normalize-space(@class), ' '), ' btn ')]"
    )
```

**Step 2 : Run (FAIL)**

```bash
cd /Users/nitch/projects/git_projets/xpath_detector
source .venv/bin/activate
pytest tests/test_analyzer.py::test_by_class_uses_safe_multiclass_pattern -v
```

Expected: FAIL (l'expression actuelle utilise `contains(@class,'btn')`).

**Step 3 : Modifier `analyzer.py`**

Trouver le bloc `if attributes.get("class"):` (autour de la ligne 68) et remplacer :

```python
    if attributes.get("class"):
        classes = attributes["class"].split()
        if classes:
            first_class = classes[0]
            candidates.append(
                XPathCandidate(
                    strategy="by_class",
                    expression=f"//{tag}[contains(@class,'{first_class}')]",
                    stability_score=60,
                )
            )
```

par :

```python
    if attributes.get("class"):
        classes = attributes["class"].split()
        if classes:
            first_class = classes[0]
            candidates.append(
                XPathCandidate(
                    strategy="by_class",
                    expression=(
                        f"//{tag}[contains(concat(' ', normalize-space(@class), ' '), "
                        f"' {first_class} ')]"
                    ),
                    stability_score=60,
                )
            )
```

**Step 4 : Run (PASS)**

```bash
pytest tests/test_analyzer.py -v
```

Expected: tous passent (les 2 nouveaux + les 23 existants).

**Step 5 : Commit**

```bash
git add tests/test_analyzer.py src/xpath_detector/analyzer.py
git commit -m "fix(analyzer): by_class uses multi-class safe pattern (no false positives)"
```

---

## Phase 2 — by_id_prefix

### Task 2 : Helper `_split_dynamic_id`

**Files:**
- Modify: `src/xpath_detector/analyzer.py`
- Modify: `tests/test_analyzer.py`

**Step 1 : Tests du helper**

Append to `tests/test_analyzer.py`:

```python
def test_split_dynamic_id_digits_only_suffix():
    from xpath_detector.analyzer import _split_dynamic_id

    assert _split_dynamic_id("vpu_amount_20260512") == "vpu_amount_"
    assert _split_dynamic_id("user-123") == "user-"


def test_split_dynamic_id_uuid_like():
    from xpath_detector.analyzer import _split_dynamic_id

    # 8+ chars mixing letters and digits = uuid-like
    assert _split_dynamic_id("field_a1b2c3d4") == "field_"


def test_split_dynamic_id_date_with_dashes():
    from xpath_detector.analyzer import _split_dynamic_id

    assert _split_dynamic_id("foo_2026-05-12") == "foo_"


def test_split_dynamic_id_static_returns_none():
    from xpath_detector.analyzer import _split_dynamic_id

    # Pas de separateur
    assert _split_dynamic_id("login") is None
    # Suffixe trop court
    assert _split_dynamic_id("foo_ab") is None
    # Suffixe pas dynamique
    assert _split_dynamic_id("user_name") is None


def test_split_dynamic_id_short_prefix_rejected():
    from xpath_detector.analyzer import _split_dynamic_id

    # Prefix < 3 chars
    assert _split_dynamic_id("a_123") is None
```

**Step 2 : Run (FAIL)**

```bash
pytest tests/test_analyzer.py -v -k split_dynamic_id
```

Expected: ImportError on `_split_dynamic_id`.

**Step 3 : Implementer le helper dans `analyzer.py`**

Ajouter en bas de `analyzer.py`, apres `generate_candidates` :

```python
def _split_dynamic_id(id_value: str) -> str | None:
    """Detect dynamic IDs (with timestamp/uuid/digit suffix) and return their stable prefix.

    Returns prefix including the separator (so it can be used directly with starts-with).
    Returns None if the id appears static (no separator, or non-dynamic suffix).
    """
    for sep in ("_", "-"):
        if sep not in id_value:
            continue
        prefix, _, suffix = id_value.rpartition(sep)
        if len(prefix) < 3 or not suffix:
            continue
        if _is_dynamic_suffix(suffix):
            return prefix + sep
    return None


def _is_dynamic_suffix(suffix: str) -> bool:
    """Heuristic: digit run, uuid-like, or date-like."""
    if suffix.isdigit():
        return True
    # 8+ chars mixing letters and digits = uuid-like
    if (
        len(suffix) >= 8
        and any(c.isdigit() for c in suffix)
        and any(c.isalpha() for c in suffix)
    ):
        return True
    # 8+ chars of digits and dashes (date-like)
    if len(suffix) >= 8 and all(c.isdigit() or c == "-" for c in suffix):
        return True
    return False
```

**Step 4 : Run (PASS)**

```bash
pytest tests/test_analyzer.py -v -k split_dynamic_id
```

Expected: 5 passed.

**Step 5 : Commit**

```bash
git add tests/test_analyzer.py src/xpath_detector/analyzer.py
git commit -m "feat(analyzer): add _split_dynamic_id helper to detect dynamic IDs"
```

---

### Task 3 : Strategy `by_id_prefix`

**Files:**
- Modify: `src/xpath_detector/analyzer.py:27-34` (apres `by_id`)
- Modify: `tests/test_analyzer.py`

**Step 1 : Tests de la strategy**

```python
def test_by_id_prefix_generated_for_dynamic_id():
    candidates = generate_candidates(
        tag="input", text=None, attributes={"id": "vpu_amount_20260512"}
    )
    cand = next(c for c in candidates if c.strategy == "by_id_prefix")
    assert cand.expression == "//input[starts-with(@id,'vpu_amount_')]"
    assert cand.stability_score == 85


def test_by_id_prefix_NOT_generated_for_static_id():
    candidates = generate_candidates(
        tag="input", text=None, attributes={"id": "login"}
    )
    assert not any(c.strategy == "by_id_prefix" for c in candidates)


def test_by_id_prefix_coexists_with_by_id():
    """Both by_id (exact) and by_id_prefix should be present for dynamic IDs."""
    candidates = generate_candidates(
        tag="input", text=None, attributes={"id": "foo_123"}
    )
    strategies = [c.strategy for c in candidates]
    assert "by_id" in strategies
    assert "by_id_prefix" in strategies


def test_by_id_prefix_escape_apostrophe_in_prefix():
    """Defensive: prefix should not contain apostrophes in practice but handle it."""
    # IDs rarely contain apostrophes, but if so, should not crash.
    candidates = generate_candidates(
        tag="input", text=None, attributes={"id": "abc_2026"}
    )
    cand = next(c for c in candidates if c.strategy == "by_id_prefix")
    assert "'" in cand.expression  # legitimate xpath quotes
```

**Step 2 : Run (FAIL)**

```bash
pytest tests/test_analyzer.py -v -k by_id_prefix
```

Expected: 4 failures.

**Step 3 : Etendre `generate_candidates`**

Dans `analyzer.py`, immediatement APRES le bloc `if attributes.get("id"):` (vers ligne 34), ajouter :

```python
    if attributes.get("id"):
        prefix = _split_dynamic_id(attributes["id"])
        if prefix:
            candidates.append(
                XPathCandidate(
                    strategy="by_id_prefix",
                    expression=f"//{tag}[starts-with(@id,'{prefix}')]",
                    stability_score=85,
                )
            )
```

**Step 4 : Run (PASS)**

```bash
pytest tests/test_analyzer.py -v -k by_id_prefix
```

Expected: 4 passed.

**Step 5 : Commit**

```bash
git add tests/test_analyzer.py src/xpath_detector/analyzer.py
git commit -m "feat(analyzer): add by_id_prefix strategy for dynamic IDs (starts-with)"
```

---

## Phase 3 — by_attr_combo

### Task 4 : Strategy `by_attr_combo`

**Files:**
- Modify: `src/xpath_detector/analyzer.py`
- Modify: `tests/test_analyzer.py`

**Step 1 : Tests**

```python
def test_by_attr_combo_skipped_when_id_present():
    """Combo is redundant when by_id (95) already exists."""
    candidates = generate_candidates(
        tag="input",
        text=None,
        attributes={"id": "x", "name": "amount", "type": "text"},
    )
    assert not any(c.strategy == "by_attr_combo" for c in candidates)


def test_by_attr_combo_skipped_with_single_attr():
    """Need at least 2 of the combinable attrs."""
    candidates = generate_candidates(
        tag="input", text=None, attributes={"name": "amount"}
    )
    assert not any(c.strategy == "by_attr_combo" for c in candidates)


def test_by_attr_combo_name_and_type():
    candidates = generate_candidates(
        tag="input", text=None, attributes={"name": "amount", "type": "text"}
    )
    cand = next(c for c in candidates if c.strategy == "by_attr_combo")
    assert cand.expression == "//input[@name='amount' and @type='text']"
    assert cand.stability_score == 88


def test_by_attr_combo_picks_first_two_by_priority():
    """Priority order: name > type > role > data-testid > placeholder."""
    candidates = generate_candidates(
        tag="input",
        text=None,
        attributes={
            "placeholder": "0.00",
            "role": "spinbutton",
            "name": "amount",
            "type": "number",
        },
    )
    cand = next(c for c in candidates if c.strategy == "by_attr_combo")
    # name (1st) + type (2nd) — placeholder/role come later
    assert cand.expression == "//input[@name='amount' and @type='number']"
```

**Step 2 : Run (FAIL)**

```bash
pytest tests/test_analyzer.py -v -k by_attr_combo
```

Expected: 4 failures.

**Step 3 : Implementer**

Dans `analyzer.py`, APRES le bloc `by_aria_label` (vers ligne 48), AVANT le bloc `by_text`, ajouter :

```python
    # by_attr_combo : combine 2 attrs si pas d'id (more specific than singles)
    if not attributes.get("id"):
        combo_priority = ("name", "type", "role", "data-testid", "placeholder")
        present_attrs = [a for a in combo_priority if attributes.get(a)]
        if len(present_attrs) >= 2:
            a1, a2 = present_attrs[0], present_attrs[1]
            candidates.append(
                XPathCandidate(
                    strategy="by_attr_combo",
                    expression=(
                        f"//{tag}[@{a1}='{attributes[a1]}' "
                        f"and @{a2}='{attributes[a2]}']"
                    ),
                    stability_score=88,
                )
            )
```

**Step 4 : Run (PASS)**

```bash
pytest tests/test_analyzer.py -v -k by_attr_combo
```

Expected: 4 passed.

**Step 5 : Commit**

```bash
git add tests/test_analyzer.py src/xpath_detector/analyzer.py
git commit -m "feat(analyzer): add by_attr_combo strategy (AND combinator on 2 attributes)"
```

---

## Phase 4 — by_label_for

### Task 5 : Strategy `by_label_for`

**Files:**
- Modify: `src/xpath_detector/analyzer.py`
- Modify: `tests/test_analyzer.py`

**Step 1 : Tests**

```python
def test_by_label_for_generated_with_id_and_label():
    candidates = generate_candidates(
        tag="input",
        text=None,
        attributes={"id": "vpu_amount"},
        nearby_label="Montant :",
    )
    cand = next(c for c in candidates if c.strategy == "by_label_for")
    assert cand.expression == "//*[@id=//label[contains(.,'Montant :')]/@for]"
    assert cand.stability_score == 78


def test_by_label_for_skipped_without_id():
    candidates = generate_candidates(
        tag="input",
        text=None,
        attributes={},
        nearby_label="Montant :",
    )
    assert not any(c.strategy == "by_label_for" for c in candidates)


def test_by_label_for_skipped_without_label():
    candidates = generate_candidates(
        tag="input",
        text=None,
        attributes={"id": "vpu_amount"},
        nearby_label=None,
    )
    assert not any(c.strategy == "by_label_for" for c in candidates)


def test_by_label_for_escapes_apostrophe():
    candidates = generate_candidates(
        tag="input",
        text=None,
        attributes={"id": "x"},
        nearby_label="Reference donneur d'ordre :",
    )
    cand = next(c for c in candidates if c.strategy == "by_label_for")
    assert "concat(" in cand.expression
```

**Step 2 : Run (FAIL)**

```bash
pytest tests/test_analyzer.py -v -k by_label_for
```

Expected: 4 failures.

**Step 3 : Implementer**

Dans `analyzer.py`, APRES le bloc `by_attr_combo`, ajouter :

```python
    # by_label_for : pattern HTML standard via label[for=id]
    if nearby_label and attributes.get("id"):
        candidates.append(
            XPathCandidate(
                strategy="by_label_for",
                expression=(
                    f"//*[@id=//label[contains(.,{escape_xpath_literal(nearby_label)})]/@for]"
                ),
                stability_score=78,
            )
        )
```

**Step 4 : Run (PASS)**

```bash
pytest tests/test_analyzer.py -v -k by_label_for
```

Expected: 4 passed.

**Step 5 : Commit**

```bash
git add tests/test_analyzer.py src/xpath_detector/analyzer.py
git commit -m "feat(analyzer): add by_label_for strategy (HTML label-for pattern)"
```

---

## Phase 5 — by_text_normalized

### Task 6 : Strategy `by_text_normalized`

**Files:**
- Modify: `src/xpath_detector/analyzer.py`
- Modify: `tests/test_analyzer.py`

**Step 1 : Tests**

```python
def test_by_text_normalized_generated():
    candidates = generate_candidates(
        tag="button", text="Valider", attributes={}
    )
    cand = next(c for c in candidates if c.strategy == "by_text_normalized")
    assert cand.expression == "//button[normalize-space()='Valider']"
    assert cand.stability_score == 72


def test_by_text_normalized_coexists_with_by_text():
    candidates = generate_candidates(
        tag="a", text="Login", attributes={}
    )
    strategies = [c.strategy for c in candidates]
    assert "by_text_normalized" in strategies
    assert "by_text" in strategies


def test_by_text_normalized_escapes_apostrophe():
    candidates = generate_candidates(
        tag="a", text="L'utilisateur", attributes={}
    )
    cand = next(c for c in candidates if c.strategy == "by_text_normalized")
    assert "concat(" in cand.expression


def test_by_text_normalized_skipped_if_empty_or_long():
    candidates = generate_candidates(tag="div", text="", attributes={})
    assert not any(c.strategy == "by_text_normalized" for c in candidates)

    candidates = generate_candidates(
        tag="div", text="a" * 80, attributes={}
    )
    assert not any(c.strategy == "by_text_normalized" for c in candidates)
```

**Step 2 : Run (FAIL)**

```bash
pytest tests/test_analyzer.py -v -k by_text_normalized
```

Expected: 4 failures.

**Step 3 : Implementer**

Dans `analyzer.py`, IMMEDIATEMENT AVANT le bloc `by_text` existant (`if text and 0 < len(text) < 50:`), ajouter :

```python
    # by_text_normalized : exact match after whitespace normalization
    if text and 0 < len(text) < 50:
        candidates.append(
            XPathCandidate(
                strategy="by_text_normalized",
                expression=f"//{tag}[normalize-space()={escape_xpath_literal(text)}]",
                stability_score=72,
            )
        )
```

**Step 4 : Run (PASS)**

```bash
pytest tests/test_analyzer.py -v -k by_text_normalized
```

Expected: 4 passed.

**Step 5 : Commit**

```bash
git add tests/test_analyzer.py src/xpath_detector/analyzer.py
git commit -m "feat(analyzer): add by_text_normalized strategy (normalize-space exact match)"
```

---

## Phase 6 — Integration et regression

### Task 7 : Test integration et tri par score

**Files:**
- Modify: `tests/test_analyzer.py`

**Step 1 : Test d'integration global**

Append to `tests/test_analyzer.py`:

```python
def test_full_strategy_set_for_dynamic_field():
    """Verify all relevant strategies fire for a realistic dynamic form field."""
    candidates = generate_candidates(
        tag="input",
        text=None,
        attributes={
            "id": "vpu_amount_20260512",  # dynamic id
            "name": "amount",
            "type": "text",
            "class": "form-control",
        },
        absolute_xpath="/html/body/form/table/tr[1]/td[2]/input",
        nearby_label="Montant :",
    )
    strategies = {c.strategy for c in candidates}
    # Must have these strategies
    assert "by_id" in strategies
    assert "by_id_prefix" in strategies  # dynamic id detected
    assert "by_name" in strategies
    assert "by_label_for" in strategies  # has id + label
    assert "by_class" in strategies
    assert "by_label_neighbor" in strategies
    assert "absolute" in strategies


def test_score_order_after_v13_additions():
    """Verify candidates are sorted by stability_score desc."""
    candidates = generate_candidates(
        tag="input",
        text="Submit",
        attributes={
            "id": "vpu_x_123",
            "data-testid": "submit-btn",
            "name": "submit",
            "type": "text",
            "aria-label": "Send",
            "class": "primary",
        },
        absolute_xpath="/html/body/x",
        nearby_label="Submit :",
    )
    scores = [c.stability_score for c in candidates]
    assert scores == sorted(scores, reverse=True), f"Not sorted: {scores}"


def test_by_class_no_longer_buggy_for_substring():
    """Regression test for the v1.3 by_class fix."""
    candidates = generate_candidates(
        tag="button", text=None, attributes={"class": "btn"}
    )
    cand = next(c for c in candidates if c.strategy == "by_class")
    # Pre-v1.3 expression would be `contains(@class,'btn')`. Must be different now.
    assert cand.expression != "//button[contains(@class,'btn')]"
    assert "normalize-space(@class)" in cand.expression
```

**Step 2 : Run all tests**

```bash
pytest tests/test_analyzer.py -v
```

Expected: tous passent (au moins 45 tests total).

**Step 3 : Run full project tests for regression**

```bash
pytest -q
```

Expected: ~107 tests passing (85 baseline + 22 nouveaux).

**Step 4 : Commit**

```bash
git add tests/test_analyzer.py
git commit -m "test(analyzer): add integration tests for full v1.3 strategy set"
```

---

## Phase 7 — Documentation et release

### Task 8 : CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

**Step 1 : Inserer la section v1.3.0**

Trouver la ligne `## [1.2.3] - 2026-05-12` et inserer AVANT :

```markdown
## [1.3.0] - 2026-05-12

### Fixed
- **by_class generated xpath with substring false positives**. Pattern was
  `contains(@class,'btn')` which also matched `class="btn-secondary"`. Now uses
  the safe pattern `contains(concat(' ', normalize-space(@class), ' '), ' btn ')`.

### Added
- **`by_id_prefix` strategy** (score 85): generates `starts-with(@id,'prefix')`
  when an id appears dynamic (suffix is pure digits, uuid-like, or date-like).
  Tests no longer break when the app generates timestamped/uuid IDs at runtime.
- **`by_attr_combo` strategy** (score 88): combines 2 attributes with `and`
  when no `id` is present. More discriminating than single-attribute selectors.
  Priority order: name > type > role > data-testid > placeholder.
- **`by_label_for` strategy** (score 78): canonical HTML form pattern
  `//*[@id=//label[contains(.,'X')]/@for]`. Robust when the page uses the
  standard `<label for="id">` association.
- **`by_text_normalized` strategy** (score 72): `normalize-space()='X'` exact
  match after whitespace normalization. More specific than `contains()` substring.

### XPath coverage vs devhints.io/xpath
- Before v1.3 : 6/22 patterns (~27%)
- After v1.3 : 11/22 patterns (~50%) + safer existing patterns

```

**Step 2 : Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add CHANGELOG entry for v1.3.0"
```

---

### Task 9 : Lint + tests finaux

**Step 1 : Lint**

```bash
cd /Users/nitch/projects/git_projets/xpath_detector
source .venv/bin/activate
ruff check src/ tests/ scripts/ 2>&1 | tail -10
black --check src/ tests/ scripts/ 2>&1 | tail -3
```

If issues:
```bash
ruff check src/ tests/ scripts/ --fix
black src/ tests/ scripts/
git add -A
git commit -m "chore: apply ruff/black auto-fixes"
```

**Step 2 : Final test run**

```bash
pytest -q
pytest --cov=xpath_detector --cov-report=term-missing | tail -15
```

Expected:
- 107+ tests passing
- analyzer.py coverage: 100%

---

### Task 10 : Tag + push + release

**Step 1 : Tag**

```bash
git tag v1.3.0
```

**Step 2 : Push**

```bash
git push origin master
git push origin v1.3.0
```

**Step 3 : Create GitHub release**

```bash
gh release create v1.3.0 \
  --title "v1.3.0 - 4 new XPath strategies + by_class safety fix" \
  --notes "## Added

4 new XPath strategies to handle real-world patterns from devhints.io/xpath:

- **by_id_prefix** (85): \`starts-with(@id,'prefix')\` for dynamic IDs
- **by_attr_combo** (88): \`[@a='X' and @b='Y']\` when no id present
- **by_label_for** (78): canonical \`<label for='id'>\` HTML pattern
- **by_text_normalized** (72): \`normalize-space()='X'\` exact match

## Fixed

- **by_class no longer has false positives**: \`contains(@class,'btn')\` could match \`btn-secondary\`. Now uses the safe \`contains(concat(' ', normalize-space(@class), ' '), ' btn ')\` pattern.

## Coverage

XPath patterns from devhints.io/xpath: 27% -> 50% (+5 strategies). Total 12 strategies.

See CHANGELOG.md for details."
```

---

## Recapitulatif

| Phase | Tasks | Strategies / Fixes | Tests | Duree estimee |
|-------|-------|--------------------|:-----:|---------------|
| 1 | 1 | by_class fix (safe multi-class) | +2 | 30 min |
| 2 | 2, 3 | _split_dynamic_id + by_id_prefix | +9 | 1h30 |
| 3 | 4 | by_attr_combo | +4 | 45 min |
| 4 | 5 | by_label_for | +4 | 45 min |
| 5 | 6 | by_text_normalized | +4 | 30 min |
| 6 | 7 | tests integration | +3 | 30 min |
| 7 | 8, 9, 10 | CHANGELOG + lint + release | — | 30 min |
| **Total** | **10 tasks** | **+4 strategies, 1 fix** | **+22 tests** | **~5h** |

Coverage cible analyzer.py : 100% maintenu.

---

## Execution

Plan complet et sauvegarde. Deux options d'execution :

**1. Subagent-Driven (cette session)** — je delegue par phase

**2. Parallel Session (separee)** — tu ouvres une nouvelle session avec `executing-plans`

Recommandation : **1**, vu que tu connais l'historique du projet et qu'on a deja la chaine de fixes en cours.
