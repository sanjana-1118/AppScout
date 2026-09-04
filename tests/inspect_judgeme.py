import sys
sys.path.insert(0, '.')
from experiment.db.database import get_db
from sqlalchemy import text

with get_db() as s:
    app = s.execute(text("SELECT id, app_slug, app_name, description, developer_name, app_url FROM apps WHERE app_slug = 'judgeme'")).mappings().first()
    if app:
        print("DB RECORD FOR JUDGEME:")
        print("  id:", app["id"])
        print("  app_slug:", app["app_slug"])
        print("  app_name:", app["app_name"])
        print("  developer_name:", app["developer_name"])
        print("  description:", repr(app["description"]))
        print("  app_url:", app["app_url"])
    else:
        print("Judge.me not found in apps table!")

    # Check total apps with NULL description
    null_desc = s.execute(text("SELECT count(*) FROM apps WHERE description IS NULL OR description = ''")).scalar()
    print("Total apps with NULL or empty description:", null_desc)
