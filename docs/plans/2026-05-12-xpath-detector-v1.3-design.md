# xpath-detector v1.3 — Design

**Date** : 2026-05-12
**Statut** : Approuve
**Cible** : Couvrir les patterns devhints critiques manquants — fix `by_class`, support des IDs dynamiques, combinator AND, pattern `label[for]`, normalize-space.

---

## 1. Contexte

L'audit contre [devhints.io/xpath](https://devhints.io/xpath) revele que v1.2.3 couvre ~6/22 patterns courants (27%). Deux problemes concrets :

1. **`by_class` faux positifs** : `contains(@class,'btn')` matche aussi `btn-secondary`. Tests faux.
2. **IDs dynamiques cassent** : `id="vpu_amount_20260512"` ne matche plus le lendemain.

v1.3 ajoute 4 nouvelles strategies et fixe `by_class`, passant la couverture a ~70%.

---

## 2. Strategies

### 2.1 `by_class` (FIX, remplace l'existant)

**Avant** (buggy) :
```xpath
//button[contains(@class,'btn')]
```
Matche `class="btn"`, `class="btn-primary"`, `class="btn-secondary"`, etc.

**Apres** (safe) :
```xpath
//button[contains(concat(' ', normalize-space(@class), ' '), ' btn ')]
```
Matche uniquement la classe entiere `btn`, jamais sous-chaine.

**Score** : 60 (inchange).

### 2.2 `by_id_prefix` (NOUVEAU)

Quand l'`id` semble dynamique (suffixe numerique, UUID, date), genere un xpath par prefixe.

**Heuristique de detection** :
- Split sur le dernier `_` ou `-`
- Si le suffixe est :
  - 100% chiffres (`foo_123`) -> dynamique
  - 8+ caracteres alphanumeriques mixtes (`foo_abc12-3def`) -> uuid-like
  - 8+ caracteres dont uniquement chiffres et `-` (`foo_2026-05-12`) -> date-like

**Exemple** :
```python
id = "vpu_amount_20260512_143022"
# split -> prefix = "vpu_amount_20260512_", suffix = "143022"
# suffix.isdigit() True -> dynamique
xpath = "//input[starts-with(@id,'vpu_amount_20260512_')]"
```

Le split est greedy au DERNIER separateur. Pour des IDs comme `foo_20260512_143022`, on garde le prefixe le plus stable possible.

**Score** : 85 (entre `by_data_testid` 90 et `by_name` 80). Moins fiable que l'id exact mais resiste aux runs.

### 2.3 `by_attr_combo` (NOUVEAU)

Combinateur AND sur 2 attributs quand l'`id` est absent. Plus discriminant qu'un seul attribut.

**Quand** : pas d'`id` ET au moins 2 attributs parmi `{name, type, role, data-testid, placeholder}`.

**Selection** : prend les 2 premiers par priorite `name > type > role > data-testid > placeholder`. (data-testid est plus haut comme single, mais le combo de 2 attrs basics est plus universel.)

**Exemple** :
```python
attrs = {"name": "amount", "type": "text", "placeholder": "0.00"}
# Pas d'id -> on combine name + type
xpath = "//input[@name='amount' and @type='text']"
```

**Score** : 88 (plus specifique que `by_data_testid` 90 ne l'est seul).

### 2.4 `by_label_for` (NOUVEAU)

Pattern HTML standard : un `<label for="X">` pointe vers `<input id="X">`. Permet de trouver l'input via le texte de son label, meme si l'id est dynamique.

**Quand** : `nearby_label` est defini ET l'element a un attribut `id` (sinon le pattern n'a aucun sens).

**Exemple** :
```python
xpath = "//*[@id=//label[contains(.,'Compte beneficiaire :')]/@for]"
```

Si l'app n'utilise pas `<label for=>`, le xpath retourne `[]` au runtime — pas de probleme, les candidats moins prioritaires (label_neighbor, absolute) prennent le relais.

**Score** : 78 (entre `by_name` 80 et `by_aria_label` 75). Tres stable quand applicable, mais pas universel.

### 2.5 `by_text_normalized` (NOUVEAU)

Match exact apres normalisation des espaces. Plus precis que `contains()`.

**Difference** :
```python
# by_text (substring) - peut etre ambigu
//button[contains(.,'Valider')]    # matche aussi "Valider et continuer"

# by_text_normalized (exact, ignore whitespace)
//button[normalize-space()='Valider']    # matche uniquement "Valider"
```

**Quand** : meme conditions que `by_text` (texte non vide, longueur 1-49).

**Score** : 72 (entre `by_aria_label` 75 et `by_text` 70).

---

## 3. Nouvelle echelle de scoring

| Score | Strategy | Pattern XPath |
|:-----:|----------|---------------|
| 95 | by_id | `//tag[@id='X']` |
| 90 | by_data_testid | `//tag[@data-testid='X']` |
| **88** | **by_attr_combo** | `//tag[@a='X' and @b='Y']` |
| **85** | **by_id_prefix** | `//tag[starts-with(@id,'prefix')]` |
| 80 | by_name | `//tag[@name='X']` |
| **78** | **by_label_for** | `//*[@id=//label[contains(.,'L')]/@for]` |
| 75 | by_aria_label | `//tag[@aria-label='X']` |
| **72** | **by_text_normalized** | `//tag[normalize-space()='X']` |
| 70 | by_text | `//tag[contains(.,'X')]` |
| 60 | by_class | `//tag[contains(concat(' ',normalize-space(@class),' '),' X ')]` |
| 50 | by_label_neighbor | `//span[contains(.,'L')]/../../td/tag` |
| 10 | absolute | `/html/body/...` |

12 strategies au total (10 actives + 2 conditionnelles).

---

## 4. Implementation par module

### 4.1 `analyzer.py` — extensions

Ajouter 3 helpers prives :

```python
def _split_dynamic_id(id_value: str) -> str | None: ...
def _safe_class_xpath(tag: str, class_name: str) -> str: ...
# (les autres sont inline dans generate_candidates)
```

`generate_candidates` gagne 4 nouvelles strategies, insertions dans cet ordre apres la generation actuelle :

1. Apres by_id -> by_id_prefix (si heuristique positive)
2. Apres by_aria_label -> by_attr_combo (si pas d'id, >= 2 attrs)
3. Apres by_aria_label -> by_label_for (si nearby_label + id present)
4. Avant by_text -> by_text_normalized (memes conditions que by_text)
5. by_class : remplace l'expression (memes conditions)

### 4.2 `overlay.py` — pas de changement

Le pattern `by_label_for` se construit cote Python a partir de l'`id` et du `nearby_label` deja envoyes. Pas de modif JS necessaire.

### 4.3 Exporters — pas de changement

Prennent toujours `xpaths[0]` (meilleur score). Les nouveaux candidats s'inserent dans le tri automatiquement.

---

## 5. Compatibilite

- **API publique** inchangee
- **Sessions JSON v1.0-v1.2** : lisibles, mais ne contiennent pas les nouvelles strategies (xpaths plus courts)
- **Scoring** : un element capture en v1.2 et reexporte en v1.3 garde les memes scores (analyzer ne re-evalue pas le passe)
- **Migration** : non necessaire. Pour beneficier des nouvelles strategies, recapturer en v1.3.

---

## 6. Strategie de tests

### Tests unitaires (priorite haute)

| Strategy | Nb tests | Cas couverts |
|----------|:--------:|--------------|
| `by_class` fix | 4 | classe simple, plusieurs classes, classe avec sous-chaine, classe vide |
| `by_id_prefix` | 6 | id statique (skip), id avec digits, id avec UUID, id avec date, id sans separateur, suffixe court (skip) |
| `by_attr_combo` | 4 | avec id (skip), 1 attr (skip), 2 attrs basics, 3 attrs (prend 2) |
| `by_label_for` | 3 | sans id (skip), avec id+label, avec id sans label (skip) |
| `by_text_normalized` | 3 | texte simple, texte avec espaces, texte trop long (skip) |
| Edge cases | 2 | apostrophe dans label, scoring stable apres ajouts |

Total : **+22 tests**.

### Test integration

Le test e2e existant continue de passer (verifie qu'aucun regression).

---

## 7. Risques

| Risque | Impact | Mitigation |
|--------|:------:|------------|
| Heuristique dynamique fausse positive (split sur id legitime) | Moyen | Tests detailes, on garde aussi by_id (95) en candidat |
| `by_label_for` xpath retourne `[]` si pas de `<label for=>` | Faible | Les autres candidats prennent le relais |
| Trop de candidats par element (UX HTML report verbeux) | Faible | Le rapport HTML truncate ou trie deja |
| Score 88/85/78/72 entre les existants -> tri instable | Faible | Tri par `-stability_score` strict |

---

## 8. Livrables

- **Commits** : 10-12 atomiques TDD
- **Tests** : +22
- **Coverage analyzer** : reste 100%
- **Tag** : `v1.3.0`
- **CHANGELOG** : nouvelle section
- **Release GitHub** avec exemples concrets

---

## 9. Hors scope (v1.4+)

- `by_sibling` (`following-sibling::`, `preceding-sibling::`)
- Commande shell `xpath <element_index> <strategy>` pour choisir manuellement
- `[not(@disabled)]`, `[position()]`, `[last()]`
- XPath 2.0 (`ends-with`, regex)
- Shadow DOM support

---

## 10. Prochaines etapes

Apres validation, invoquer `superpowers:writing-plans` pour generer le plan TDD detaille.
