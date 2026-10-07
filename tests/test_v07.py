from pathlib import Path
import re
from fastapi.testclient import TestClient
from app.main import app

HTML = Path(__file__).resolve().parents[1] / 'static' / 'index.html'


def test_frontend_dom_references_resolve():
    text = HTML.read_text()
    ids = set(re.findall(r'id=["\']([^"\']+)', text))
    refs = set(re.findall(r"\$\(['\"]([^'\"]+)", text))
    refs.discard('finding-')  # dynamic detail IDs are generated at runtime
    missing = refs - ids
    assert not missing, f'Missing DOM ids referenced by render code: {sorted(missing)}'


def test_favicon_is_declared_and_served():
    text = HTML.read_text()
    assert '/static/assets/logo.svg' in text
    assert (HTML.parent / 'assets' / 'logo.svg').exists()
    with TestClient(app) as client:
        response = client.get('/static/assets/logo.svg')
        assert response.status_code == 200
        assert 'svg' in response.headers.get('content-type', '').lower()


def test_health_api_contract_and_all_sections():
    with TestClient(app) as client:
        response = client.get('/api/health')
        assert response.status_code == 200
        body = response.json()
        assert body['ok'] is True
        sections = body['snapshot']['sections']
        expected = {'system','cpu','memory','processes','threads','network','storage','services','apt','logs','kernel_events','security','hardware','boot','gpu','users'}
        assert expected <= set(sections)
        assert body['snapshot']['analysis']['overall'] in {'HEALTHY','WARNING','CRITICAL'}


def test_health_and_static_routes_are_not_missing():
    with TestClient(app) as client:
        assert client.get('/').status_code == 200
        assert client.get('/api/health').status_code == 200
        assert client.get('/api/history').status_code == 200
        assert client.get('/api/logs').status_code == 200
        assert client.get('/api/kernel').status_code == 200
