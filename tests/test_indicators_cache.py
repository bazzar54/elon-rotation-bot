import json
import os
from datetime import datetime, timezone
from indicators.loader import load_indicators


def test_load_indicators_no_network_returns_numeric_keys():
    now = datetime.now(timezone.utc)
    ind = load_indicators(now, no_network=True)
    for k in ['btc_dom','eth_dom','fear_greed','cbbi','btc_dom_delta_7d']:
        assert k in ind
        assert isinstance(ind[k], (int,float))


def test_load_indicators_uses_fresh_cache(tmp_path, monkeypatch):
    # create a fake project root
    project = tmp_path / 'proj'
    project.mkdir()
    state = project / 'state'
    state.mkdir()
    cached = {
        'cached_at': datetime.now(timezone.utc).isoformat(),
        'indicators': {
            'btc_dom': 42.0,
            'eth_dom': 18.0,
            'fear_greed': 50,
            'cbbi': 60,
            'btc_dom_delta_7d': 0.0
        }
    }
    (state / 'indicators_cache.json').write_text(json.dumps(cached))
    monkeypatch.chdir(project)
    now = datetime.now(timezone.utc)
    ind = load_indicators(now, no_network=True)
    assert ind.get('btc_dom') == 42.0
    assert ind.get('_cached_at') is not None
