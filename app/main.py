import asyncio
import time
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .collectors import collect_all, journal_events
from .analyzer import analyze
from .db import init, save, history

BASE=Path(__file__).resolve().parent.parent
app=FastAPI(title="Kali Health Checker", version="0.9.0")
app.mount("/static",StaticFiles(directory=BASE/"static"),name="static")
_latest=None; _last_collect=0.0; _last_rate_time=0.0; _last_rx=0; _last_tx=0; _last_disk_time=0.0; _last_disk_read=0; _last_disk_write=0; _lock=asyncio.Lock()

@app.on_event("startup")
async def startup():
    init()

async def snapshot(force=False):
    global _latest,_last_collect
    async with _lock:
        if not force and _latest and time.time()-_last_collect < 3: return _latest
        data=await asyncio.to_thread(collect_all)
        # Add current network transfer rates from consecutive runtime samples.
        global _last_rate_time, _last_rx, _last_tx, _last_disk_time, _last_disk_read, _last_disk_write
        now=time.time()
        net=data.get("network",{}).get("data",{})
        total_rx=sum(int(i.get("rx_bytes",0) or 0) for i in net.get("interfaces",[]) or [])
        total_tx=sum(int(i.get("tx_bytes",0) or 0) for i in net.get("interfaces",[]) or [])
        elapsed=now-_last_rate_time if _last_rate_time else 0
        if elapsed > 0.25 and _last_rate_time and total_rx >= _last_rx and total_tx >= _last_tx:
            net["current_speed"]={"download_bps":(total_rx-_last_rx)/elapsed,"upload_bps":(total_tx-_last_tx)/elapsed,"interval_seconds":elapsed}
        else:
            net["current_speed"]={"download_bps":0,"upload_bps":0,"interval_seconds":0}
        _last_rx, _last_tx, _last_rate_time = total_rx, total_tx, now
        storage=data.get("storage",{}).get("data",{})
        io=storage.get("io",{}) or {}
        read_bytes=int(io.get("read_bytes",0) or 0); write_bytes=int(io.get("write_bytes",0) or 0)
        disk_elapsed=now-_last_disk_time if _last_disk_time else 0
        if disk_elapsed > 0.25 and _last_disk_time and read_bytes >= _last_disk_read and write_bytes >= _last_disk_write:
            io["current_speed"]={"read_bps":(read_bytes-_last_disk_read)/disk_elapsed,"write_bps":(write_bytes-_last_disk_write)/disk_elapsed,"interval_seconds":disk_elapsed}
        else:
            io["current_speed"]={"read_bps":0,"write_bps":0,"interval_seconds":0}
        _last_disk_read, _last_disk_write, _last_disk_time = read_bytes, write_bytes, now
        analysis=analyze(data)
        snap={"timestamp":now,"collected_at":data.get("system",{}).get("collected_at"),"sections":data,"analysis":analysis}
        _latest=snap; _last_collect=now; save(data,analysis["findings"])
        return snap

@app.get("/")
def index(): return FileResponse(BASE/"static"/"index.html")

@app.get("/favicon.ico")
def favicon(): return FileResponse(BASE/"static"/"assets"/"favicon.ico", media_type="image/x-icon")

@app.get("/api/health")
async def health():
    s=await snapshot(); return {"ok":True,"connected":True,"snapshot":s}

@app.get("/api/history")
def get_history(limit:int=Query(300,ge=1,le=5000)): return {"ok":True,"history":history(limit)}

@app.get("/api/logs")
async def logs(limit:int=Query(120,ge=1,le=500)): return {"ok":True,"result":await asyncio.to_thread(journal_events,False,limit)}

@app.get("/api/kernel")
async def kernel(limit:int=Query(120,ge=1,le=500)): return {"ok":True,"result":await asyncio.to_thread(journal_events,True,limit)}

@app.get("/api/refresh")
async def refresh(): return {"ok":True,"snapshot":await snapshot(True)}
