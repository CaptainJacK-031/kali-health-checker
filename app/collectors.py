import os
import platform
import re
import socket
import time
from typing import Any, Callable

import psutil

from .utils import command_exists, json_loads, now_iso, run_cmd, safe_float


def envelope(name: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        data = fn()
        return {"status": "ok", "data": data or {}, "errors": [], "collected_at": now_iso(), "duration_ms": round((time.perf_counter()-started)*1000, 1)}
    except PermissionError as e:
        return {"status": "unavailable", "data": {}, "errors": [str(e) or "Permission denied"], "collected_at": now_iso(), "duration_ms": round((time.perf_counter()-started)*1000, 1)}
    except Exception as e:
        return {"status": "error", "data": {}, "errors": [f"{type(e).__name__}: {e}"], "collected_at": now_iso(), "duration_ms": round((time.perf_counter()-started)*1000, 1)}


def system():
    def f():
        uname = platform.uname()
        return {"hostname": socket.gethostname(), "os": uname.system, "release": uname.release, "version": uname.version,
                "machine": uname.machine, "python": platform.python_version(), "boot_time": psutil.boot_time(),
                "uptime_seconds": max(0, time.time()-psutil.boot_time()), "virtualization": virtualization(), "current_user": os.getenv("USER", "unknown")}
    return envelope("system", f)


def virtualization():
    r = run_cmd(["systemd-detect-virt"], 3)
    if r["ok"] and r["stdout"]:
        return r["stdout"]
    return "none/unknown"


def cpu():
    def f():
        freq = psutil.cpu_freq()
        per = psutil.cpu_percent(interval=0.15, percpu=True)
        model = cpu_model()
        current = round(freq.current,1) if freq and freq.current is not None else None
        minimum = round(freq.min,1) if freq and freq.min else None
        supported = supported_cpu_frequency_mhz()
        if supported is None and freq and freq.max and freq.max > 0:
            supported = round(freq.max,1)
        return {"percent": psutil.cpu_percent(interval=None), "per_core": per, "logical_cpus": psutil.cpu_count() or 0,
                "physical_cpus": psutil.cpu_count(logical=False) or 0, "frequency_mhz": current,
                "min_mhz": minimum, "max_mhz": supported,
                "load1_5_15": list(os.getloadavg()) if hasattr(os, "getloadavg") else [],
                "temperature": cpu_temp(), "model": model}
    return envelope("cpu", f)


def supported_cpu_frequency_mhz():
    """Return a real supported/max CPU frequency from Linux cpufreq or lscpu."""
    candidates = []
    for cpu_dir in glob_cpu_dirs():
        for name in ("cpuinfo_max_freq", "scaling_max_freq"):
            path = os.path.join(cpu_dir, "cpufreq", name)
            try:
                raw = float(open(path, encoding="utf-8").read().strip())
                if raw > 0:
                    # Linux cpufreq sysfs values are expressed in kHz.
                    value = raw / 1000.0
                    if 200 <= value <= 20000:
                        candidates.append(value)
            except (OSError, ValueError):
                continue
    if candidates:
        return round(max(candidates), 1)
    if command_exists("lscpu"):
        r = run_cmd(["lscpu"], 3)
        if r["ok"]:
            for line in r["stdout"].splitlines():
                if re.match(r"^CPU max MHz\s*:", line, re.I):
                    try:
                        value = float(line.split(":", 1)[1].strip())
                        if value > 0:
                            return round(value, 1)
                    except ValueError:
                        pass
    return None


def glob_cpu_dirs():
    base = "/sys/devices/system/cpu"
    try:
        names = [n for n in os.listdir(base) if re.fullmatch(r"cpu\d+", n)]
        return [os.path.join(base, n) for n in sorted(names)[:32]]
    except OSError:
        return []


def cpu_model():
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.lower().startswith(("model name", "hardware")) and ":" in line:
                    value=line.split(":",1)[1].strip()
                    if value: return value
    except Exception:
        pass
    return platform.processor() or "Unknown CPU"


def cpu_temp():
    """Return a validated runtime CPU/package temperature; never invent a value."""
    candidates=[]
    # psutil reads hwmon/thermal sources when available.
    try:
        temps = psutil.sensors_temperatures(fahrenheit=False)
        preferred=("coretemp","k10temp","zenpower","cpu_thermal","cpu","soc_thermal")
        ordered=[]
        for key, entries in temps.items():
            rank=0 if key.lower() in preferred else 1
            for e in entries:
                if e.current is not None:
                    try: ordered.append((rank,float(e.current),key,getattr(e,"label","")))
                    except (TypeError,ValueError): pass
        ordered.sort(key=lambda x:x[0])
        for _,value,_,_ in ordered:
            if -20 <= value <= 130:
                candidates.append(value)
        if candidates:
            return round(max(candidates),1)
    except Exception:
        pass
    # Direct thermal-zone fallback for systems where psutil exposes nothing.
    try:
        base="/sys/class/thermal"
        for name in os.listdir(base):
            if not name.startswith("thermal_zone"): continue
            tp=os.path.join(base,name,"temp")
            try:
                raw=float(open(tp,encoding="utf-8").read().strip())
                value=raw/1000.0 if abs(raw)>200 else raw
                if -20 <= value <= 130:
                    candidates.append(value)
            except (OSError,ValueError):
                continue
        if candidates:
            return round(max(candidates),1)
    except OSError:
        pass
    return None


def memory():
    def f():
        v=psutil.virtual_memory(); s=psutil.swap_memory()
        return {"total":v.total,"used":v.used,"available":v.available,"free":v.free,"percent":v.percent,"cached":getattr(v,"cached",0),"buffers":getattr(v,"buffers",0),"swap_total":s.total,"swap_used":s.used,"swap_free":s.free,"swap_percent":s.percent}
    return envelope("memory", f)


def processes():
    def f():
        rows=[]
        for p in psutil.process_iter(["pid","name","username","status","cmdline","memory_percent"]):
            try:
                cpu=p.cpu_percent(interval=None)
                info=p.info
                rows.append({"pid":info["pid"],"name":info.get("name") or "?","user":info.get("username") or "?","status":info.get("status") or "?","cpu_percent":round(cpu,1),"memory_percent":round(float(info.get("memory_percent") or 0),1),"command":" ".join(info.get("cmdline") or [])[:300]})
            except (psutil.NoSuchProcess, psutil.AccessDenied): continue
        return {"processes":rows,"count":len(rows),"top_cpu":sorted(rows,key=lambda x:x["cpu_percent"],reverse=True)[:10],"top_memory":sorted(rows,key=lambda x:x["memory_percent"],reverse=True)[:15]}
    return envelope("processes", f)


def threads():
    def f():
        total = running = sleeping = blocked = other = 0
        per_process = []
        for proc in psutil.process_iter(["pid", "name", "status"]):
            try:
                count = proc.num_threads()
                if count < 0: continue
                info = proc.info
                total += count
                status = info.get("status") or ""
                if status == psutil.STATUS_RUNNING:
                    running += count
                elif status in (psutil.STATUS_SLEEPING, psutil.STATUS_IDLE, psutil.STATUS_WAKING):
                    sleeping += count
                elif status in (psutil.STATUS_DISK_SLEEP, psutil.STATUS_WAITING):
                    blocked += count
                else:
                    other += count
                per_process.append({"pid": info.get("pid"), "name": info.get("name") or "?", "threads": count, "status": status})
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return {"total": total, "running": running, "sleeping": sleeping, "blocked": blocked, "other": other,
                "top_processes": sorted(per_process, key=lambda x: x["threads"], reverse=True)[:8]}
    return envelope("threads", f)


def network():
    def f():
        stats=psutil.net_io_counters(pernic=True); addrs=psutil.net_if_addrs(); states=psutil.net_if_stats()
        interfaces=[]
        for name,st in stats.items():
            ips=[]
            for a in addrs.get(name,[]):
                if getattr(a,"family",None) in (socket.AF_INET,socket.AF_INET6): ips.append(a.address)
            state=states.get(name)
            interfaces.append({"name":name,"up":bool(state.isup) if state else False,"speed_mbps":getattr(state,"speed",0) if state else 0,"addresses":ips,"rx_bytes":st.bytes_recv,"tx_bytes":st.bytes_sent,"rx_packets":st.packets_recv,"tx_packets":st.packets_sent,"rx_errors":st.errin,"tx_errors":st.errout,"rx_drops":st.dropin,"tx_drops":st.dropout})
        conns=[]
        try:
            for c in psutil.net_connections(kind="inet")[:300]: conns.append({"fd":c.fd,"family":str(c.family),"type":str(c.type),"local":f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "","remote":f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "","status":c.status,"pid":c.pid})
        except psutil.AccessDenied: pass
        return {"interfaces":interfaces,"connections":conns,"connection_count":len(conns)}
    return envelope("network", f)


def storage():
    def f():
        files=[]
        for p in psutil.disk_partitions(all=False):
            try:
                u=psutil.disk_usage(p.mountpoint); st=os.statvfs(p.mountpoint)
                total_i=st.f_files; free_i=st.f_ffree; used_i=total_i-free_i
                files.append({"device":p.device,"mountpoint":p.mountpoint,"fstype":p.fstype,"opts":p.opts,"total":u.total,"used":u.used,"free":u.free,"percent":u.percent,"inode_total":total_i,"inode_used":used_i,"inode_percent":round(used_i/total_i*100,1) if total_i else 0})
            except (PermissionError,OSError): continue
        io=psutil.disk_io_counters(); io_data={"read_bytes":io.read_bytes,"write_bytes":io.write_bytes,"read_count":io.read_count,"write_count":io.write_count} if io else {}
        devices=lsblk()
        physical=[d for d in devices if d.get("type")=="disk"]
        physical_total=sum(int(d.get("size_bytes",0) or 0) for d in physical)
        root=None
        for f in files:
            if f.get("mountpoint")=="/": root=f; break
        smart=smart_summary(devices)
        return {"filesystems":files,"io":io_data,"devices":devices,"physical_disks":physical,"physical_total":physical_total,"root_filesystem":root,"smart":smart}
    return envelope("storage", f)


def lsblk():
    r=run_cmd(["lsblk","-b","-J","-o","NAME,KNAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS,MODEL,ROTA,TRAN"],5)
    rows=json_loads(r["stdout"],{}).get("blockdevices",[]) if r["ok"] else []
    def enrich(items):
        for d in items:
            d["size_bytes"]=int(d.get("size") or 0)
            for child in d.get("children") or []: enrich([child])
    enrich(rows)
    return rows


def smart_summary(devices):
    if not command_exists("smartctl"): return {"available":False,"reason":"smartctl not installed"}
    out=[]
    for d in devices:
        if d.get("type") != "disk" or not d.get("name"): continue
        path="/dev/"+d["name"]
        r=run_cmd(["smartctl","-H",path],6)
        text=(r["stdout"]+"\n"+r["stderr"]).strip()
        out.append({"device":path,"ok":r["ok"],"output":text[-2500:]})
    return {"available":True,"devices":out}


def services():
    def f():
        r=run_cmd(["systemctl","--failed","--no-legend","--no-pager"],5); failed=r["stdout"].splitlines() if r["ok"] else []
        return {"failed":failed,"failed_count":len(failed),"systemd_available":command_exists("systemctl")}
    return envelope("services", f)


def apt():
    def f():
        check=run_cmd(["apt-get","check"],20); audit=run_cmd(["dpkg","--audit"],10); up=run_cmd(["apt","list","--upgradable"],20); held=run_cmd(["apt-mark","showhold"],10)
        return {"check":{"ok":check["ok"],"stdout":check["stdout"],"stderr":check["stderr"]},"dpkg_audit":{"ok":audit["ok"],"stdout":audit["stdout"],"stderr":audit["stderr"]},"upgradeable":up["stdout"],"held":held["stdout"],"dpkg_audit_ok":audit["ok"],"apt_check_ok":check["ok"]}
    return envelope("apt", f)


def journal_events(kernel=False, limit=80):
    def f():
        cmd=["journalctl"]
        if kernel: cmd += ["-k"]
        cmd += ["-n",str(limit),"--no-pager","-o","json"]
        r=run_cmd(cmd,10)
        events=[]
        if not r["ok"]:
            # fallback to short output, useful on restricted journal access
            fcmd=["journalctl"] + (["-k"] if kernel else []) + ["-n",str(limit),"--no-pager","-o","short-iso"]
            fr=run_cmd(fcmd,10)
            if fr["ok"]:
                for line in fr["stdout"].splitlines(): events.append({"timestamp":"","severity":"UNKNOWN","source":"journalctl","message":line,"raw":line})
                return {"events":events,"count":len(events),"raw_error":r["stderr"]}
            raise RuntimeError(r["stderr"] or fr["stderr"] or "journalctl failed")
        for line in r["stdout"].splitlines():
            obj=json_loads(line,{})
            if not obj: continue
            pri=int(obj.get("PRIORITY","6")) if str(obj.get("PRIORITY","6")).isdigit() else 6
            sev={0:"EMERGENCY",1:"ALERT",2:"CRITICAL",3:"ERROR",4:"WARNING",5:"NOTICE",6:"INFO",7:"DEBUG"}.get(pri,"UNKNOWN")
            events.append({"timestamp":obj.get("__REALTIME_TIMESTAMP") or obj.get("_SOURCE_REALTIME_TIMESTAMP") or "","severity":sev,"priority":pri,"source":obj.get("_SYSTEMD_UNIT") or obj.get("SYSLOG_IDENTIFIER") or obj.get("_COMM") or "kernel" if kernel else "system","message":obj.get("MESSAGE","") ,"unit":obj.get("_SYSTEMD_UNIT",""),"pid":obj.get("_PID",""),"raw":obj})
        return {"events":events,"count":len(events)}
    return envelope("kernel_events" if kernel else "logs", f)


def security():
    def f():
        ufw=run_cmd(["ufw","status"],5) if command_exists("ufw") else {"ok":False,"stderr":"ufw not installed","stdout":""}
        nft=run_cmd(["nft","list","ruleset"],6) if command_exists("nft") else {"ok":False,"stderr":"nft not installed","stdout":""}
        aa=run_cmd(["aa-status","--json"],6) if command_exists("aa-status") else {"ok":False,"stderr":"aa-status not installed","stdout":""}
        ssh=run_cmd(["systemctl","is-active","ssh"],4)
        return {"ufw":{"active":ufw["ok"] and "Status: active" in ufw["stdout"],"output":ufw["stdout"] or ufw["stderr"]},"nftables":{"available":nft["ok"],"rules_preview":nft["stdout"][:4000],"error":nft["stderr"]},"apparmor":{"available":aa["ok"],"output":aa["stdout"][:4000],"error":aa["stderr"]},"ssh_active":ssh["ok"] and ssh["stdout"].strip()=="active",
                "firewall_protected": (ufw["ok"] and "Status: active" in ufw["stdout"]) or (nft["ok"] and bool(nft["stdout"].strip()))}
    return envelope("security", f)


def hardware():
    def f():
        sensors=run_cmd(["sensors","-j"],6) if command_exists("sensors") else {"ok":False,"stderr":"lm-sensors not installed","stdout":""}
        lscpu=run_cmd(["lscpu"],5)
        pci=run_cmd(["lspci","-mm"],6) if command_exists("lspci") else {"ok":False,"stdout":"","stderr":"lspci not installed"}
        usb=run_cmd(["lsusb"],6) if command_exists("lsusb") else {"ok":False,"stdout":"","stderr":"lsusb not installed"}
        return {"sensors":{"available":sensors["ok"],"data":json_loads(sensors["stdout"],{}) if sensors["ok"] else {},"error":sensors["stderr"]},"lscpu":lscpu["stdout"],"pci":pci["stdout"],"usb":usb["stdout"]}
    return envelope("hardware", f)


def boot():
    def f():
        total=run_cmd(["systemd-analyze"],5); blame=run_cmd(["systemd-analyze","blame"],8)
        return {"summary":total["stdout"] or total["stderr"],"blame":blame["stdout"].splitlines()[:30],"available":total["ok"]}
    return envelope("boot", f)


def gpu():
    def f():
        if command_exists("nvidia-smi"):
            r=run_cmd(["nvidia-smi","--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu","--format=csv,noheader,nounits"],5)
            rows=[]
            for line in r["stdout"].splitlines():
                x=[v.strip() for v in line.split(",")]
                if len(x)>=5: rows.append({"name":x[0],"utilization":safe_float(x[1]),"memory_used_mb":safe_float(x[2]),"memory_total_mb":safe_float(x[3]),"temperature":safe_float(x[4])})
            return {"available":bool(rows),"gpus":rows,"source":"nvidia-smi"}
        return {"available":False,"gpus":[],"source":"none"}
    return envelope("gpu", f)



def users():
    def f():
        import pwd
        rows=[]
        for u in pwd.getpwall():
            try:
                rows.append({"name":u.pw_name,"uid":u.pw_uid,"gid":u.pw_gid,"home":u.pw_dir,"shell":u.pw_shell,"type":"regular" if 1000 <= u.pw_uid < 60000 else "system"})
            except Exception:
                continue
        regular=[x for x in rows if x["type"]=="regular"]
        system=[x for x in rows if x["type"]=="system"]
        return {"count":len(rows),"regular_count":len(regular),"system_count":len(system),"users":rows}
    return envelope("users", f)

def collect_all():
    return {"system":system(),"cpu":cpu(),"memory":memory(),"processes":processes(),"threads":threads(),"network":network(),"storage":storage(),"services":services(),"apt":apt(),"logs":journal_events(False,80),"kernel_events":journal_events(True,80),"security":security(),"hardware":hardware(),"boot":boot(),"gpu":gpu(),"users":users()}
