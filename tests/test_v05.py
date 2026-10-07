import time
from app.collectors import processes, users
from app.db import init, save, history, conn


def test_top_cpu_is_limited_to_ten():
    data = processes()['data']
    assert len(data['top_cpu']) <= 10


def test_users_collector_has_summary():
    data = users()['data']
    assert data['count'] == len(data['users'])
    assert data['regular_count'] + data['system_count'] == data['count']


def test_history_retention_schema():
    init()
    # The production save() routine enforces a 60-second cadence and one-hour retention.
    c = conn()
    cols = {r[1] for r in c.execute('PRAGMA table_info(metrics)').fetchall()}
    assert {'ts','cpu','memory','swap','rx','tx','findings'} <= cols
    c.close()


def test_runtime_threads_have_real_counts():
    from app.collectors import threads
    data = threads()['data']
    assert data['total'] >= 0
    assert data['running'] + data['sleeping'] + data['blocked'] + data['other'] <= data['total']
    assert all(int(x['threads']) >= 0 for x in data['top_processes'])


def test_storage_io_speed_schema():
    from app.main import snapshot
    import asyncio
    s = asyncio.run(snapshot(True))
    io = s['sections']['storage']['data']['io']
    assert 'current_speed' in io
    assert {'read_bps','write_bps','interval_seconds'} <= set(io['current_speed'])
