from pathlib import Path
import re
from fastapi.testclient import TestClient
from app.main import app

HTML = Path(__file__).resolve().parents[1] / "static" / "index.html"

def test_v08_overview_uses_history_chart_and_no_old_core_chart():
    text = HTML.read_text()
    assert 'overviewCpuHistoryChart' in text
    assert 'CPU utilization by cores' not in text.split('<section id="overview"',1)[1].split('</section>',1)[0]
    assert 'overviewCoreChart' not in text
    assert 'slice(-60)' in text
    assert '0–100%' in text or '0-100%' in text

def test_v08_system_summary_is_single_group():
    text = HTML.read_text()
    overview = text.split('<section id="overview"',1)[1].split('</section>',1)[0]
    assert overview.count('class="summary-lines"') == 1
    assert overview.count('class="summary-lines">') == 1
    for item in ['OS','Kernel','CPU','Memory','Storage','Processes','Network','Load']:
        assert f'<span>{item}</span>' in overview

def test_v08_frequency_exposes_supported_and_current():
    text = HTML.read_text()
    assert 'Supported:' in text
    assert 'Current:' in text
    assert 'max_mhz' in text
    assert 'frequency_mhz' in text

def test_v08_health_api_reports_frequency_fields():
    with TestClient(app) as client:
        body = client.get('/api/health').json()
        cpu = body['snapshot']['sections']['cpu']['data']
        assert 'frequency_mhz' in cpu
        assert 'max_mhz' in cpu

def test_v08_favicon_still_served():
    with TestClient(app) as client:
        r = client.get('/static/assets/logo.svg')
        assert r.status_code == 200
