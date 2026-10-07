import json
import sqlite3
import time
from pathlib import Path

DB=Path(__file__).resolve().parent.parent/"health_history.db"

def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init():
    c=conn(); c.executescript('''CREATE TABLE IF NOT EXISTS metrics (id INTEGER PRIMARY KEY, ts REAL NOT NULL, cpu REAL, memory REAL, swap REAL, rx REAL, tx REAL, findings INTEGER); CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(ts);'''); c.commit(); c.close()

HISTORY_INTERVAL = 60
HISTORY_RETENTION = 3600

def save(s, findings):
    m=s.get("memory",{}).get("data",{}); cpu=s.get("cpu",{}).get("data",{}); net=s.get("network",{}).get("data",{}); total_rx=sum(i.get("rx_bytes",0) for i in net.get("interfaces",[])); total_tx=sum(i.get("tx_bytes",0) for i in net.get("interfaces",[]))
    now=time.time()
    c=conn()
    last=c.execute("SELECT ts FROM metrics ORDER BY ts DESC LIMIT 1").fetchone()
    if last and now-float(last[0]) < HISTORY_INTERVAL:
        c.close(); return False
    c.execute("INSERT INTO metrics(ts,cpu,memory,swap,rx,tx,findings) VALUES(?,?,?,?,?,?,?)",(now,cpu.get("percent"),m.get("percent"),m.get("swap_percent"),total_rx,total_tx,len(findings)))
    c.execute("DELETE FROM metrics WHERE ts < ?",(now-HISTORY_RETENTION,))
    c.commit(); c.close(); return True

def history(limit=300):
    c=conn(); rows=[dict(r) for r in c.execute("SELECT * FROM metrics ORDER BY ts DESC LIMIT ?",(limit,)).fetchall()]; c.close(); return list(reversed(rows))
