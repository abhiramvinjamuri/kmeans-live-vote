"""Shared classroom poll, with atomic submission/closure and separate rounds."""
import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from model import POINTS

DATABASE = os.getenv("VOTE_DB_PATH", str(Path(__file__).with_name("votes_1d.sqlite3")))
DATASET = hashlib.sha256(json.dumps(POINTS, sort_keys=True).encode()).hexdigest()[:16]


@contextmanager
def db():
    connection = sqlite3.connect(DATABASE, timeout=15)
    try:
        connection.execute("PRAGMA busy_timeout=15000")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE IF NOT EXISTS ballots_1d (dataset TEXT, round INTEGER, seat INTEGER, choices TEXT NOT NULL, PRIMARY KEY(dataset, round, seat))")
        connection.execute("CREATE TABLE IF NOT EXISTS settings_1d (dataset TEXT, name TEXT, value TEXT NOT NULL, PRIMARY KEY(dataset, name))")
        connection.commit()
        with connection:
            yield connection
    finally:
        connection.close()


def read_setting(connection, name, default=""):
    row = connection.execute("SELECT value FROM settings_1d WHERE dataset=? AND name=?", (DATASET, name)).fetchone()
    return row[0] if row else default


def setting(name, default=""):
    with db() as connection:
        return read_setting(connection, name, default)


def write_setting(connection, name, value):
    connection.execute("INSERT INTO settings_1d VALUES (?,?,?) ON CONFLICT(dataset,name) DO UPDATE SET value=excluded.value", (DATASET, name, str(value)))


def change_setting(name, value):
    with db() as connection:
        write_setting(connection, name, value)


def votes():
    with db() as connection:
        rows = connection.execute("SELECT choices FROM ballots_1d WHERE dataset=? AND round=COALESCE((SELECT CAST(value AS INTEGER) FROM settings_1d WHERE dataset=? AND name='round'),1)", (DATASET, DATASET)).fetchall()
    counts = {name: [0, 0] for name in POINTS}
    for (raw,) in rows:
        for name, choice in json.loads(raw).items():
            if name in counts and choice in ("Blue", "Orange"):
                counts[name][0 if choice == "Blue" else 1] += 1
    return counts, len(rows)


def vote_once(seat, choices, expected_round):
    if type(seat) is not int or not 1 <= seat <= 60 or set(choices) != set(POINTS) or any(v not in ("Blue", "Orange") for v in choices.values()):
        return "invalid"
    try:
        with db() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if int(read_setting(connection, "round", "1")) != expected_round:
                return "stale"
            if read_setting(connection, "voting", "open") != "open":
                return "closed"
            connection.execute("INSERT INTO ballots_1d VALUES (?,?,?,?)", (DATASET, expected_round, seat, json.dumps(choices)))
        return "recorded"
    except sqlite3.IntegrityError:
        return "duplicate"


def new_round():
    # Retain previous rounds locally, so restarting the class poll is reversible.
    with db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        write_setting(connection, "round", int(read_setting(connection, "round", "1")) + 1)
        for name, value in {"stage": "0", "audience_reveal": "no", "voting": "closed"}.items():
            write_setting(connection, name, value)
