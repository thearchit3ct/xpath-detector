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
                    expression=f"//{tag}[contains(@class,'{first_class}')]",
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
