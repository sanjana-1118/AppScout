"""
experiment/extract_pricing.py
-----------------------------
Production-grade Shopify App Store Pricing & Plan Extractor.

Extracts:
1. App-level pricing information:
   - pricing_type ('free', 'freemium', 'paid', 'unknown')
   - free_trial_days (e.g. 14, 7, 2, or None)
2. Plan-level pricing information:
   - plan_name (e.g. 'Basic', 'Growth', 'Enterprise')
   - price_amount (float / Decimal or None for custom/free)
   - currency (e.g. 'USD')
   - billing_interval ('monthly', 'annual', 'one_time', 'usage_based', 'custom')
   - free_trial_days (e.g. 14, 7, or None)
   - features (list of feature string bullets)
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any
from bs4 import BeautifulSoup


@dataclasses.dataclass
class PlanData:
    """Structured pricing plan tier."""
    plan_name: str
    price_amount: float | None
    currency: str = "USD"
    billing_interval: str = "monthly"
    free_trial_days: int | None = None
    features: list[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class AppPricingData:
    """App-level pricing summary and child plans."""
    pricing_type: str  # 'free', 'freemium', 'paid', 'unknown'
    free_trial_days: int | None = None
    plans: list[PlanData] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pricing_type": self.pricing_type,
            "free_trial_days": self.free_trial_days,
            "plans": [p.to_dict() for p in self.plans],
        }


def extract_pricing_from_soup(soup: BeautifulSoup) -> AppPricingData:
    """Extract structured pricing metadata from parsed BeautifulSoup object."""
    # Find pricing container
    pricing_sec = (
        soup.find(attrs={"id": "adp-pricing"})
        or soup.find("div", attrs={"data-controller": "pricing-component"})
        or soup.find(attrs={"data-test-id": "pricing-cards-track"})
        or soup.find("section", class_=lambda c: c and "pricing" in c.lower())
    )

    if not pricing_sec:
        # Check fallback text in header for free app indicator
        body_text = soup.get_text(" ", strip=True)
        if "Free to install" in body_text or "Free plan available" in body_text:
            return AppPricingData(pricing_type="freemium", free_trial_days=None, plans=[])
        elif "Free" in body_text and "Pricing" not in body_text:
            return AppPricingData(pricing_type="free", free_trial_days=None, plans=[])
        return AppPricingData(pricing_type="unknown", free_trial_days=None, plans=[])

    track = (
        pricing_sec.find(attrs={"data-test-id": "pricing-cards-track"})
        or pricing_sec.find(attrs={"data-pricing-component-target": "track"})
    )

    if track:
        cards = track.find_all("div", recursive=False)
    else:
        cards = pricing_sec.find_all("div", class_=lambda c: c and ("pricingcard" in c.lower() or "shadow-pricing" in c.lower()))
        if not cards:
            cards = pricing_sec.find_all("div", class_=lambda c: c and "rounded" in c.lower() and "overflow-hidden" in c.lower())

    plans: list[PlanData] = []
    has_free = False
    has_paid = False
    max_trial_days = None

    for card in cards:
        card_text = card.get_text(" | ", strip=True)
        lines = [l.strip() for l in card_text.split(" | ") if l.strip()]
        if not lines or len(lines) < 1:
            continue

        # Plan Name is usually first heading or first line
        plan_name = lines[0]
        if plan_name.lower() in ("pricing", "features") and len(lines) > 1:
            plan_name = lines[1]

        price_amount: float | None = None
        currency = "USD"
        billing_interval = "monthly"
        trial_days: int | None = None

        # Price parsing
        price_match = re.search(r"\$\s*(\d+(?:\.\d+)?)", card_text)
        if price_match:
            try:
                price_amount = float(price_match.group(1))
                if price_amount > 0:
                    has_paid = True
                else:
                    has_free = True
            except ValueError:
                price_amount = None
        elif "free" in card_text.lower():
            price_amount = 0.0
            has_free = True

        # Billing Interval
        lower_card = card_text.lower()
        if "/ month" in lower_card or "every 30 days" in lower_card or "per month" in lower_card:
            billing_interval = "monthly"
        elif "/ year" in lower_card or "per year" in lower_card or "/year" in lower_card:
            billing_interval = "annual"
        elif "one-time" in lower_card or "one time" in lower_card:
            billing_interval = "one_time"
        elif "usage" in lower_card:
            billing_interval = "usage_based"

        # Free Trial Days
        trial_match = re.search(r"(\d+)[-\s]day\s+free\s+trial", card_text, re.I)
        if trial_match:
            try:
                trial_days = int(trial_match.group(1))
                if max_trial_days is None or trial_days > max_trial_days:
                    max_trial_days = trial_days
            except ValueError:
                trial_days = None

        # Feature bullet points
        features: list[str] = []
        if "Features" in lines:
            f_idx = lines.index("Features")
            features = [x for x in lines[f_idx + 1:] if x not in ("Choose plan", "Get started", "Install")]

        plans.append(
            PlanData(
                plan_name=plan_name[:250],
                price_amount=price_amount,
                currency=currency,
                billing_interval=billing_interval,
                free_trial_days=trial_days,
                features=features[:10],
            )
        )

    # Classify overall pricing type
    if has_free and has_paid:
        p_type = "freemium"
    elif has_paid and not has_free:
        p_type = "paid"
    elif has_free and not has_paid:
        p_type = "free"
    else:
        p_type = "free" if any(p.price_amount == 0.0 for p in plans) else ("paid" if plans else "unknown")

    return AppPricingData(
        pricing_type=p_type,
        free_trial_days=max_trial_days,
        plans=plans,
    )
