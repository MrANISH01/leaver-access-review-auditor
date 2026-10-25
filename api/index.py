import os
import shutil
import sys
from pathlib import Path

# Add backend directory to sys.path so app imports work seamlessly
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Configure serverless defaults (Vercel container has read-only filesystem except /tmp)
tmp_db_path = "/tmp/auditor.sqlite3"
if "DATABASE_PATH" not in os.environ:
    os.environ["DATABASE_PATH"] = tmp_db_path

# If DB in /tmp does not exist yet, copy seeded instance db if available
try:
    if not os.path.exists(tmp_db_path):
        instance_db = backend_dir / "instance" / "auditor.sqlite3"
        if instance_db.exists():
            shutil.copyfile(str(instance_db), tmp_db_path)
except Exception:
    pass

if "DEMO_MODE" not in os.environ:
    os.environ["DEMO_MODE"] = "1"
if "ALLOW_LAN_DEMO" not in os.environ:
    os.environ["ALLOW_LAN_DEMO"] = "1"
if "APPROVER_ACTORS" not in os.environ:
    os.environ["APPROVER_ACTORS"] = "demo-approver,approver@acme.example"

from app import create_app
from app.config import Config

config = Config.from_env()
app = create_app(config)
