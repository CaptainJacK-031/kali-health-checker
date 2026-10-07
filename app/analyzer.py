from typing import Any
from .utils import human_bytes


def d(section: dict, key: str, default=None):
    return (section or {}).get("data",{}).get(key,default)


def analyze(s: dict[str,Any]) -> dict[str,Any]:
    findings=[]
    cpu=d(s.get("cpu",{}),"percent",0); mem=d(s.get("memory",{}),"percent",0); swap=d(s.get("memory",{}),"swap_percent",0)
    if cpu >= 90: findings.append({"severity":"CRITICAL","area":"CPU","title":"CPU usage is very high","detail":f"Current CPU usage is {cpu:.1f}%. Review the Processes and CPU tabs."})
    elif cpu >= 75: findings.append({"severity":"WARNING","area":"CPU","title":"CPU usage is high","detail":f"Current CPU usage is {cpu:.1f}%."})
    if mem >= 90: findings.append({"severity":"CRITICAL","area":"Memory","title":"Memory usage is very high","detail":f"RAM usage is {mem:.1f}%."})
    elif mem >= 80: findings.append({"severity":"WARNING","area":"Memory","title":"Memory usage is high","detail":f"RAM usage is {mem:.1f}%."})
    if swap >= 80: findings.append({"severity":"WARNING","area":"Memory","title":"Swap usage is high","detail":f"Swap usage is {swap:.1f}%."})
    for fs in d(s.get("storage",{}),"filesystems",[]) or []:
        if fs.get("percent",0) >= 95: findings.append({"severity":"CRITICAL","area":"Storage","title":f"{fs.get('mountpoint','filesystem')} is almost full","detail":f"{fs.get('percent',0):.1f}% used ({human_bytes(fs.get('free',0))} free)."})
        elif fs.get("percent",0) >= 85: findings.append({"severity":"WARNING","area":"Storage","title":f"{fs.get('mountpoint','filesystem')} is filling up","detail":f"{fs.get('percent',0):.1f}% used."})
        if fs.get("inode_percent",0) >= 90: findings.append({"severity":"WARNING","area":"Storage","title":f"Inode usage is high on {fs.get('mountpoint','filesystem')}","detail":f"{fs.get('inode_percent',0):.1f}% inodes used."})
    apt=d(s.get("apt",{}),"apt_check_ok",True)
    audit=d(s.get("apt",{}),"dpkg_audit_ok",True)
    if not apt: findings.append({"severity":"WARNING","area":"APT","title":"APT dependency check reported a problem","detail":"Open APT / Packages for stdout/stderr and dpkg audit details."})
    if not audit: findings.append({"severity":"WARNING","area":"APT","title":"dpkg audit reported packages needing attention","detail":"Open APT / Packages for the exact audit output."})
    failed=d(s.get("services",{}),"failed_count",0)
    if failed: findings.append({"severity":"WARNING","area":"Services","title":f"{failed} failed systemd service(s)","detail":"Open Services to inspect the failed units."})
    k=s.get("kernel_events",{}); kdata=k.get("data",{}) if isinstance(k,dict) else {}
    errors=[e for e in kdata.get("events",[]) if e.get("severity") in ("EMERGENCY","ALERT","CRITICAL","ERROR")]
    if errors: findings.append({"severity":"WARNING","area":"Kernel","title":f"{len(errors)} recent kernel error/critical event(s)","detail":"Open Kernel for individual timestamps, sources and messages."})
    logs=d(s.get("logs",{}),"events",[]) or []
    log_errors=[e for e in logs if e.get("severity") in ("EMERGENCY","ALERT","CRITICAL","ERROR")]
    if log_errors: findings.append({"severity":"INFO","area":"Logs","title":f"{len(log_errors)} recent system error/critical event(s)","detail":"Open Logs to inspect each event."})
    if not findings: findings.append({"severity":"INFO","area":"System","title":"No threshold-based problems detected","detail":"Continue monitoring live tabs and diagnostics."})
    counts={x:sum(1 for f in findings if f["severity"]==x) for x in ("CRITICAL","WARNING","INFO")}
    return {"findings":findings,"counts":counts,"overall":"CRITICAL" if counts["CRITICAL"] else "WARNING" if counts["WARNING"] else "HEALTHY"}
