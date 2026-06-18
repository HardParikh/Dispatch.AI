"""
Persistence for Dispatch.

Important design choice: we use the Supabase Python client, which talks to
Supabase over HTTPS through its REST API (PostgREST). This is deliberately
NOT the direct Postgres connection that requires the connection pooler and
fails on IPv4-only corporate networks. The REST client just needs the project
URL and an API key over plain HTTPS, which works everywhere.

If Supabase is not configured (no env vars), we fall back to an in-memory
store so the app still runs for local development and demos. The in-memory
store resets when the server restarts.

Set these environment variables to use Supabase:
    SUPABASE_URL=https://YOUR_PROJECT.supabase.co
    SUPABASE_KEY=your_anon_or_service_key

And create the table once in the Supabase SQL editor (see schema.sql).
"""

import os
import warnings

from dotenv import load_dotenv

from models import Load

warnings.filterwarnings("ignore")
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

TABLE = "loads"

# In-memory fallback store. A dict keyed by load_id.
_memory_store = {}

# Try to set up the Supabase client. If anything is missing, stay in memory.
_supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"[store] Supabase client setup failed, using in-memory store: {e}")
        _supabase = None
else:
    print("[store] SUPABASE_URL/SUPABASE_KEY not set, using in-memory store.")


def save_load(load):
    """Insert or update a load."""
    row = load.to_dict()
    if _supabase is not None:
        try:
            _supabase.table(TABLE).upsert(row).execute()
            return
        except Exception as e:
            print(f"[store] save failed, falling back to memory: {e}")
    _memory_store[load.load_id] = row


def get_load(load_id):
    """Fetch one load by id. Returns a Load or None."""
    if _supabase is not None:
        try:
            res = _supabase.table(TABLE).select("*").eq("load_id", load_id).execute()
            if res.data:
                return Load.from_dict(res.data[0])
            return None
        except Exception as e:
            print(f"[store] get failed, falling back to memory: {e}")
    row = _memory_store.get(load_id)
    return Load.from_dict(row) if row else None


def list_loads():
    """Return all loads, newest first, as a list of dicts."""
    if _supabase is not None:
        try:
            res = _supabase.table(TABLE).select("*").order("created_at", desc=True).execute()
            return res.data or []
        except Exception as e:
            print(f"[store] list failed, falling back to memory: {e}")
    rows = list(_memory_store.values())
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return rows


def update_load_state(load_id, new_state):
    """Update just the state field of a load. Returns the updated Load or None."""
    load = get_load(load_id)
    if load is None:
        return None
    load.state = new_state
    save_load(load)
    return load
