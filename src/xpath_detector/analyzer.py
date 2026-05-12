"""XPath candidate generation with stability scoring."""

from __future__ import annotations

from xpath_detector.models import XPathCandidate


def escape_xpath_literal(value: str) -> str:
    """Echappe une chaine pour usage dans un xpath (gere les apostrophes via concat)."""
    if "'" not in value:
        return f"'{value}'"
    parts = value.split("'")
    quoted = [f"'{p}'" for p in parts]
    return "concat(" + ', "\'", '.join(quoted) + ")"


def generate_candidates(
    tag: str,
    text: str | None,
    attributes: dict[str, str],
    absolute_xpath: str | None = None,
    nearby_label: str | None = None,
) -> list[XPathCandidate]:
    """Genere une liste de candidats xpath tries par score decroissant."""
    candidates: list[XPathCandidate] = []

    if attributes.get("id"):
        candidates.append(
            XPathCandidate(
                strategy="by_id",
                expression=f"//{tag}[@id='{attributes['id']}']",
                stability_score=95,
            )
        )

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

    for attr, strategy, score in [
        ("data-testid", "by_data_testid", 90),
        ("name", "by_name", 80),
        ("aria-label", "by_aria_label", 75),
    ]:
        if attributes.get(attr):
            candidates.append(
                XPathCandidate(
                    strategy=strategy,
                    expression=f"//{tag}[@{attr}='{attributes[attr]}']",
                    stability_score=score,
                )
            )

    if text and 0 < len(text) < 50:
        candidates.append(
            XPathCandidate(
                strategy="by_text",
                expression=f"//{tag}[contains(.,{escape_xpath_literal(text)})]",
                stability_score=70,
            )
        )

    if nearby_label and 0 < len(nearby_label) < 50:
        candidates.append(
            XPathCandidate(
                strategy="by_label_neighbor",
                expression=f"//span[contains(.,{escape_xpath_literal(nearby_label)})]/../../td/{tag}",
                stability_score=50,
            )
        )

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

    if absolute_xpath:
        candidates.append(
            XPathCandidate(
                strategy="absolute",
                expression=absolute_xpath,
                stability_score=10,
            )
        )

    candidates.sort(key=lambda c: -c.stability_score)
    return candidates


def _split_dynamic_id(id_value: str) -> str | None:
    """Detect dynamic IDs (with timestamp/uuid/digit suffix) and return their stable prefix."""
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
    if (
        len(suffix) >= 8
        and any(c.isdigit() for c in suffix)
        and any(c.isalpha() for c in suffix)
    ):
        return True
    if len(suffix) >= 8 and all(c.isdigit() or c == "-" for c in suffix):
        return True
    return False
