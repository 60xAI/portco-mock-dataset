"""Generation state and claims (SQLite + file lock)."""
from __future__ import annotations

import json
import sqlite3
import time
from collections import Counter, defaultdict
from contextlib import contextmanager

import yaml
from filelock import FileLock

from .paths import CONFIG, STATE, NUMBERS, WORLD
from . import manifest as Mf

CLAIM_TTL = 45 * 60
DB = STATE / "claims.db"
LOCK = STATE / "claims.lock"


@contextmanager
def db():
    STATE.mkdir(exist_ok=True)
    with FileLock(str(LOCK), timeout=60):
        con = sqlite3.connect(DB)
        con.row_factory = sqlite3.Row
        con.execute("""create table if not exists files(
            id text primary key, unit text, doc_type text, tier text, family text,
            state text default 'pending', claimed_by text, claimed_at real, batch text,
            attempts integer default 0, accepted_at real, summary text, last_errors text)""")
        con.execute("create table if not exists batches(id text primary key, tier text, unit text, created real, files text)")
        try:
            yield con
            con.commit()
        finally:
            con.close()


def sync(con):
    es = Mf.load_entries([])
    have = {r["id"] for r in con.execute("select id from files")}
    for e in es:
        fam = Mf.family(e)
        if e.id not in have:
            con.execute("insert into files(id, unit, doc_type, tier, family) values(?,?,?,?,?)", (e.id, e.unit, e.doc_type, e.tier, fam))
        else:
            con.execute("update files set unit=?, doc_type=?, tier=?, family=? where id=?", (e.unit, e.doc_type, e.tier, fam, e.id))
    ids = {e.id for e in es}
    for i in have - ids:
        con.execute("delete from files where id=?", (i,))
    now = time.time()
    con.execute("update files set state='pending', claimed_by=null, claimed_at=null where state='claimed' and claimed_at < ?", (now - CLAIM_TTL,))
    return {e.id: e for e in es}


def models_cfg():
    return yaml.safe_load((CONFIG / "models.yaml").read_text())


def target_for_tier(tier: str):
    cfg = models_cfg()
    return cfg["targets"][cfg["tiers"][tier]]


def next_batch(tier: str, unit: str | None, doc_type: str | None, n: int, who: str):
    n = max(1, min(8, n))
    with db() as con:
        es = sync(con)
        rows = {r["id"]: r for r in con.execute("select * from files")}
        accepted = {i for i, r in rows.items() if r["state"] == "accepted"}

        def ready(i):
            e = es[i]
            for r in e.related:
                if r.rel in ("copy_of", "version_of", "duplicate_of") and r.id in rows and r.id not in accepted:
                    return False
            return True

        cand = [i for i, r in rows.items() if r["state"] in ("pending", "rejected") and r["tier"] == tier
                and (unit is None or r["unit"] == unit) and (doc_type is None or r["doc_type"] == doc_type) and ready(i)]
        if not cand:
            blocked = [i for i, r in rows.items() if r["state"] in ("pending", "rejected") and r["tier"] == tier and not ready(i)]
            return {"files": [], "note": f"nothing claimable for tier {tier}" + (f"; {len(blocked)} waiting on their source file" if blocked else "")}
        groups = defaultdict(list)
        for i in cand:
            groups[(rows[i]["unit"], rows[i]["doc_type"])].append(i)
        key = max(groups, key=lambda k: (len(groups[k]), k))
        pick = sorted(groups[key])[:n]
        if len(pick) < min(5, n):
            fam = rows[pick[0]]["family"]
            more = sorted(i for i in cand if i not in pick and rows[i]["unit"] == key[0] and rows[i]["family"] == fam)
            pick += more[: n - len(pick)]
        nb = con.execute("select count(*) from batches where unit=?", (key[0],)).fetchone()[0] + 1
        bid = f"dev1369-content-{key[0]}-{nb:02d}" + ("" if tier != "haiku_low" else "-low")
        now = time.time()
        for i in pick:
            con.execute("update files set state='claimed', claimed_by=?, claimed_at=?, batch=? where id=?", (who, now, bid, i))
        con.execute("insert or replace into batches values(?,?,?,?,?)", (bid, tier, key[0], now, json.dumps(pick)))
        return {"batch": bid, "clientRequestId": bid, "tier": tier, "target": target_for_tier(tier),
                "unit": key[0], "doc_type": key[1], "files": pick,
                "claim_expires_min": CLAIM_TTL // 60,
                "per_file": ["uv run mockgen pack <file-id>", "write content JSON to content/<file-id>.json", "uv run mockgen submit <file-id> content/<file-id>.json"]}


def claim_specific(ids: list[str], who: str):
    with db() as con:
        sync(con)
        for i in ids:
            con.execute("update files set state='claimed', claimed_by=?, claimed_at=? where id=? and state!='accepted'", (who, time.time(), i))


def release(file_id: str) -> str:
    with db() as con:
        sync(con)
        cur = con.execute("update files set state='pending', claimed_by=null, claimed_at=null where id=? and state='claimed'", (file_id,))
        return f"released {file_id}" if cur.rowcount else f"{file_id} was not claimed"


def mark(file_id: str, state: str, errors: list[str] | None = None, summary: str | None = None):
    with db() as con:
        sync(con)
        if state == "accepted":
            con.execute("update files set state='accepted', accepted_at=?, summary=?, last_errors=null, claimed_by=null where id=?", (time.time(), summary, file_id))
        else:
            # a rejected file stays claimed by its batch so it isn't handed out again mid-retry
            con.execute("update files set state=case when state='claimed' then 'claimed' else ? end, attempts=attempts+1, last_errors=? where id=?", (state, json.dumps(errors or []), file_id))
            touch_batch(con, file_id)


def touch_batch(con, file_id: str):
    """Refresh the claim of every file in this file's batch while a child is working on it."""
    r = con.execute("select batch from files where id=?", (file_id,)).fetchone()
    if r and r["batch"]:
        con.execute("update files set claimed_at=? where batch=? and state='claimed'", (time.time(), r["batch"]))


def touch(file_id: str):
    with db() as con:
        touch_batch(con, file_id)


def get(file_id: str):
    with db() as con:
        sync(con)
        r = con.execute("select * from files where id=?", (file_id,)).fetchone()
        return dict(r) if r else None


def summaries(ids: list[str]) -> dict[str, str]:
    with db() as con:
        out = {}
        for i in ids:
            r = con.execute("select summary from files where id=?", (i,)).fetchone()
            if r and r["summary"]:
                out[i] = r["summary"]
        return out


def status() -> str:
    lines = []
    world_files = [p.stem for p in sorted(WORLD.glob("*.yaml"))]
    n_numbers = len(list(NUMBERS.glob("PRJ*.json")))
    lines.append(f"stage world: {', '.join(world_files) or 'none'}")
    lines.append(f"stage numbers: {n_numbers} project result sets")
    es = Mf.load_entries([])
    lines.append(f"stage manifest: {len(es)} entries (cap {Mf.CAP}); units: {', '.join(u for u in Mf.UNITS if (Mf.MANIFEST / f'{u}.yaml').exists())}")
    if not es:
        return "\n".join(lines)
    with db() as con:
        sync(con)
        rows = [dict(r) for r in con.execute("select * from files")]
    st = Counter(r["state"] for r in rows)
    lines.append("stage content: " + ", ".join(f"{k} {v}" for k, v in sorted(st.items())))
    states = ["pending", "claimed", "rejected", "accepted"]
    lines.append("\nby unit:      " + " ".join(f"{s:>9}" for s in states))
    for u in Mf.UNITS:
        c = Counter(r["state"] for r in rows if r["unit"] == u)
        lines.append(f"  {u:<11} " + " ".join(f"{c[s]:>9}" for s in states))
    lines.append("\nby tier:      " + " ".join(f"{s:>9}" for s in states))
    for t in sorted({r["tier"] for r in rows}):
        c = Counter(r["state"] for r in rows if r["tier"] == t)
        lines.append(f"  {t:<11} " + " ".join(f"{c[s]:>9}" for s in states))
    lines.append("\nby type:      " + " ".join(f"{s:>9}" for s in states))
    for t in sorted({r["doc_type"] for r in rows}):
        c = Counter(r["state"] for r in rows if r["doc_type"] == t)
        lines.append(f"  {t:<17} " + " ".join(f"{c[s]:>9}" for s in states))
    return "\n".join(lines)
