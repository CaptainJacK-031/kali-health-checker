from pathlib import Path
import re
from fastapi.testclient import TestClient
from app.main import app

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / 'static' / 'index.html'


def test_v09_has_real_svg_cpu_history_chart_and_render_functions():
    text = HTML.read_text()
    assert '<svg class="cpu-history-chart" id="overviewCpuHistoryChart"' in text
    assert 'function drawCpuHistory(' in text
    assert 'function drawSpark(' in text
    assert 'drawSpark(cpuHistory)' in text
    assert 'Waiting for CPU samples' in text


def test_v09_favicon_route_and_asset():
    with TestClient(app) as client:
        r = client.get('/favicon.ico')
        assert r.status_code == 200
        assert r.headers.get('content-type', '').startswith('image/x-icon')
    assert (ROOT / 'static/assets/favicon.ico').exists()


def test_v09_health_sections_and_runtime_values():
    with TestClient(app) as client:
        body = client.get('/api/health').json()
        assert body['ok'] is True
        sections = body['snapshot']['sections']
        assert {'cpu','memory','processes','threads','network','storage','users','security'} <= set(sections)
        cpu = sections['cpu']['data']
        assert isinstance(cpu.get('percent'), (int,float))
        assert isinstance(cpu.get('frequency_mhz'), (int,float)) or cpu.get('frequency_mhz') is None
        assert len(cpu.get('load1_5_15', [])) == 3
        th = sections['threads']['data']
        assert th['total'] >= 0
        assert th['running'] >= 0
        assert th['sleeping'] >= 0
        assert th['blocked'] >= 0


def test_v09_runtime_rates_have_stable_schema():
    with TestClient(app) as client:
        first = client.get('/api/refresh').json()['snapshot']
        second = client.get('/api/refresh').json()['snapshot']
        for snap in (first, second):
            assert 'current_speed' in snap['sections']['network']['data']
            assert 'current_speed' in snap['sections']['storage']['data']['io']
            assert {'download_bps','upload_bps','interval_seconds'} <= set(snap['sections']['network']['data']['current_speed'])
            assert {'read_bps','write_bps','interval_seconds'} <= set(snap['sections']['storage']['data']['io']['current_speed'])


def test_v09_no_frontend_dom_reference_is_missing():
    text = HTML.read_text()
    ids = set(re.findall(r'id=["\']([^"\']+)', text))
    js = text.split('<script>', 1)[1].split('</script>', 1)[0]
    refs = set(re.findall(r"\$\(['\"]([^'\"]+)", js))
    refs.discard('finding-')
    assert not (refs - ids), sorted(refs - ids)


def test_v09_all_navigation_targets_exist():
    text = HTML.read_text()
    nav_targets = set(re.findall(r'data-tab="([^"]+)"', text))
    section_ids = set(re.findall(r'<section id="([^"]+)"', text))
    assert nav_targets <= section_ids
    assert len(nav_targets) == 11
