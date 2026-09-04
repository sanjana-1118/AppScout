"""
experiment/verify_pricing.py
----------------------------
Verification script for Shopify App Pricing & Plan Metadata extraction and storage.
"""

from __future__ import annotations

import json
from sqlalchemy import func, select

from experiment.db.database import get_db
from experiment.db.models import App, AppPricingPlan


def verify_pricing_subsystem() -> dict:
    print("\n" + "=" * 76)
    print("APPSCOUT — PRICING & PLAN METADATA SUBSYSTEM VERIFICATION")
    print("=" * 76)

    with get_db() as session:
        total_apps = session.scalar(select(func.count(App.id))) or 0
        apps_with_pricing = session.scalar(select(func.count(App.id)).where(App.pricing_type != None)) or 0
        total_plans = session.scalar(select(func.count(AppPricingPlan.id))) or 0
        type_counts = dict(session.execute(select(App.pricing_type, func.count(App.id)).group_by(App.pricing_type)).all())

        # Sample apps representing each pricing archetype
        sample_slugs = ["judgeme", "loox", "17track", "1-all-in-one-image-optimizer", "180-translate"]
        sample_results = []

        for slug in sample_slugs:
            app = session.scalars(select(App).where(App.app_slug == slug)).first()
            if app:
                plans = session.scalars(select(AppPricingPlan).where(AppPricingPlan.app_id == app.id)).all()
                sample_results.append({
                    "slug": app.app_slug,
                    "name": app.app_name,
                    "pricing_type": app.pricing_type,
                    "free_trial_days": app.free_trial_days,
                    "plan_count": len(plans),
                    "plans": [
                        {
                            "name": p.plan_name,
                            "price": float(p.price_amount) if p.price_amount is not None else None,
                            "interval": p.billing_interval,
                            "trial_days": p.free_trial_days,
                        }
                        for p in plans
                    ],
                })

    print(f"Total Canonical Apps in DB      : {total_apps:,}")
    print(f"Apps with Pricing Populated     : {apps_with_pricing:,} ({round(apps_with_pricing/max(total_apps,1)*100, 1)}%)")
    print(f"Total Pricing Plans in DB       : {total_plans:,}")
    print("-" * 76)
    print("Pricing Distribution Breakdown:")
    for pt, count in sorted(type_counts.items(), key=lambda x: str(x[0])):
        label = str(pt) if pt is not None else "Pending backfill"
        print(f"  - {label:<22}: {count:,}")
    print("-" * 76)
    print("Representative Sample Apps Verified:")
    for s in sample_results:
        clean_name = s["name"].encode("ascii", "replace").decode("ascii") if s["name"] else "Unknown"
        print(f"\nApp: {clean_name} ({s['slug']})")
        print(f"  Pricing Type     : {s['pricing_type']}")
        print(f"  Free Trial Days  : {s['free_trial_days']}")
        print(f"  Plans Count      : {s['plan_count']}")
        for p in s["plans"]:
            p_price = f"${p['price']:.2f}" if p['price'] is not None else "Custom / Free"
            clean_plan = p["name"].encode("ascii", "replace").decode("ascii")
            print(f"    - [{clean_plan}]: {p_price} / {p['interval']} (Trial: {p['trial_days']}d)")

    print("\n" + "=" * 76 + "\n")

    return {
        "total_apps": total_apps,
        "apps_with_pricing": apps_with_pricing,
        "total_plans": total_plans,
        "type_counts": type_counts,
        "sample_results": sample_results,
    }


if __name__ == "__main__":
    verify_pricing_subsystem()
