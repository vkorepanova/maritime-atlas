from fastapi.testclient import TestClient
from maritime_atlas.api import create_app


def test_health_and_geojson(tmp_path):
    docs = tmp_path / 'docs' / 'data'
    docs.mkdir(parents=True)
    (tmp_path / 'docs' / 'index.html').write_text('<title>Atlas</title>', encoding='utf-8')
    client = TestClient(create_app(tmp_path))
    assert client.get('/api/health').json()['mode'] == 'local'
    assert client.get('/api/vessels').json()['features'] == []
    assert client.get('/api/other').status_code == 404
