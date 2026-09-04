import sys
sys.path.insert(0, '.')
from experiment.db.database import get_db
from sqlalchemy import text

with get_db() as s:
    print("Testing combinations to discover exact query for 38,046:")
    
    # Let's check plan_name filters
    for cond in [
        "plan_name NOT ILIKE '%free%'",
        "plan_name NOT ILIKE 'free'",
        "plan_name != 'Free'",
        "price_amount > 0",
        "price_amount >= 1",
        "price_amount > 0 OR billing_interval = 'monthly'",
        "price_amount > 0 OR plan_name NOT ILIKE 'free'",
    ]:
        cnt = s.execute(text(f"SELECT count(*) FROM app_pricing_plans WHERE {cond}")).scalar()
        print(f"  {cond} -> {cnt}")
        
    # Check apps joining
    for join_cond in [
        "apps.pricing_type IN ('paid', 'freemium')",
        "apps.pricing_type = 'paid'",
        "apps.pricing_type != 'free'",
        "apps.pricing_type != 'unknown'",
    ]:
        cnt = s.execute(text(f"SELECT count(*) FROM app_pricing_plans JOIN apps ON app_pricing_plans.app_id = apps.id WHERE {join_cond}")).scalar()
        print(f"  JOIN {join_cond} -> {cnt}")

    # Check distinct plan names or distinct (app_id, plan_name)
    cnt_distinct = s.execute(text("SELECT count(distinct (app_id, plan_name)) FROM app_pricing_plans")).scalar()
    print(f"  distinct (app_id, plan_name) -> {cnt_distinct}")
    
    cnt_distinct_name = s.execute(text("SELECT count(distinct plan_name) FROM app_pricing_plans")).scalar()
    print(f"  distinct plan_name -> {cnt_distinct_name}")

    # Check if 42,326 - 4,280 = 38,046
    # Where does 4,280 come from?
    # Could 4,280 be the number of free tiers in freemium apps, or free trial plans, or plans with price = 0?
    cnt_free_trial = s.execute(text("SELECT count(*) FROM app_pricing_plans WHERE free_trial_days IS NOT NULL AND free_trial_days > 0")).scalar()
    print(f"  plans with free_trial_days > 0 -> {cnt_free_trial}")
    
    # Check if 4,280 apps have free plans
    cnt_apps_with_free_plan = s.execute(text("SELECT count(distinct app_id) FROM app_pricing_plans WHERE price_amount = 0")).scalar()
    print(f"  apps with price_amount = 0 -> {cnt_apps_with_free_plan}")

    cnt_apps_with_free_name = s.execute(text("SELECT count(distinct app_id) FROM app_pricing_plans WHERE plan_name ILIKE '%free%'")).scalar()
    print(f"  apps with plan_name ILIKE '%free%' -> {cnt_apps_with_free_name}")
