from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from apps.visits.services import detect_spoof


def _mock_log(lng, lat, dt):
    return SimpleNamespace(
        location=SimpleNamespace(x=lng, y=lat),
        recorded_at=dt,
    )


class TestDetectSpoof:
    def test_normal_walking_speed_returns_false(self):
        t0 = datetime.now(timezone.utc)
        t1 = t0 + timedelta(seconds=30)
        # ~50m apart in 30s ≈ 6 km/h (walking pace)
        before = _mock_log(126.97000, 37.56000, t0)
        after = _mock_log(126.97050, 37.56050, t1)
        assert detect_spoof(before, after) is False

    def test_continental_jump_returns_true(self):
        t0 = datetime.now(timezone.utc)
        t1 = t0 + timedelta(seconds=30)
        seoul = _mock_log(126.97, 37.56, t0)
        paris = _mock_log(2.3522, 48.8566, t1)
        assert detect_spoof(seoul, paris) is True

    def test_zero_seconds_apart_returns_false(self):
        t0 = datetime.now(timezone.utc)
        a = _mock_log(126.97, 37.56, t0)
        b = _mock_log(127.97, 38.56, t0)
        assert detect_spoof(a, b) is False

    def test_same_location_returns_false(self):
        t0 = datetime.now(timezone.utc)
        t1 = t0 + timedelta(seconds=30)
        a = _mock_log(126.97, 37.56, t0)
        b = _mock_log(126.97, 37.56, t1)
        assert detect_spoof(a, b) is False

    def test_just_under_threshold_returns_false(self):
        t0 = datetime.now(timezone.utc)
        t1 = t0 + timedelta(hours=1)
        # exactly ~190 km/h: 190km in 1h
        a = _mock_log(126.97, 37.56, t0)
        # ~190km east of Seoul
        b = _mock_log(129.122, 37.56, t1)
        assert detect_spoof(a, b) is False
