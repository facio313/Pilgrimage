from types import SimpleNamespace

from apps.routes.services import (
    THEME_WEIGHTS,
    _score_spot,
    estimate_route_metrics,
    haversine_km,
)


def _mock_spot(lng, lat, entrance_fee=0, avg_cost=0, avg_review_score=0):
    return SimpleNamespace(
        id=f"spot-{lng}-{lat}",
        location=SimpleNamespace(x=lng, y=lat),
        entrance_fee=entrance_fee,
        avg_cost=avg_cost,
        avg_review_score=avg_review_score,
    )


class TestHaversine:
    def test_seoul_to_busan_about_325km(self):
        seoul_lng, seoul_lat = 126.9783882, 37.5666103
        busan_lng, busan_lat = 129.0756416, 35.1795543
        d = haversine_km(seoul_lng, seoul_lat, busan_lng, busan_lat)
        assert 320 < d < 340

    def test_zero_distance(self):
        assert haversine_km(126.97, 37.56, 126.97, 37.56) == 0

    def test_symmetric(self):
        forward = haversine_km(126.97, 37.56, 127.10, 37.60)
        backward = haversine_km(127.10, 37.60, 126.97, 37.56)
        assert abs(forward - backward) < 1e-6


class TestEstimateRouteMetrics:
    def test_walking_returns_zero_travel_cost(self):
        spots = [_mock_spot(126.97, 37.56), _mock_spot(126.98, 37.57)]
        distance, cost, segments = estimate_route_metrics(spots, "walking")
        assert distance > 0
        assert cost == 0
        assert len(segments) == 2
        assert segments[0]["segment_distance_km"] == 0
        assert segments[0]["segment_cost"] == 0

    def test_car_includes_fuel_and_entrance(self):
        spots = [
            _mock_spot(126.97, 37.56, entrance_fee=10_000),
            _mock_spot(126.99, 37.58, entrance_fee=5_000),
        ]
        _distance, cost, _segments = estimate_route_metrics(spots, "car")
        # second spot's entrance fee is added to total cost
        assert cost >= 5_000

    def test_unknown_transport_falls_back_to_default(self):
        spots = [_mock_spot(126.97, 37.56), _mock_spot(126.98, 37.57)]
        distance, cost, segments = estimate_route_metrics(spots, "teleport")
        assert distance > 0
        assert cost >= 0
        assert len(segments) == 2

    def test_single_spot_yields_zero_distance(self):
        spots = [_mock_spot(126.97, 37.56, entrance_fee=8_000)]
        distance, cost, segments = estimate_route_metrics(spots, "car")
        assert distance == 0
        assert cost == 0  # first spot's entrance fee is not summed (no prior leg)
        assert len(segments) == 1


class TestScoreSpot:
    def test_higher_rating_wins_when_other_factors_equal(self):
        weights = THEME_WEIGHTS["nature"]
        a = _mock_spot(126.97, 37.56, avg_review_score=5.0, entrance_fee=10_000)
        b = _mock_spot(126.97, 37.56, avg_review_score=3.0, entrance_fee=10_000)
        assert _score_spot(a, 126.97, 37.56, weights) > _score_spot(b, 126.97, 37.56, weights)

    def test_closer_spot_scores_higher_when_other_factors_equal(self):
        weights = THEME_WEIGHTS["nature"]
        near = _mock_spot(126.97, 37.56, avg_review_score=4.0, entrance_fee=5_000)
        far = _mock_spot(127.20, 37.80, avg_review_score=4.0, entrance_fee=5_000)
        assert _score_spot(near, 126.97, 37.56, weights) > _score_spot(far, 126.97, 37.56, weights)

    def test_cheaper_spot_scores_higher_when_other_factors_equal(self):
        weights = THEME_WEIGHTS["nature"]
        cheap = _mock_spot(126.98, 37.57, avg_review_score=4.0, entrance_fee=1_000)
        pricey = _mock_spot(126.98, 37.57, avg_review_score=4.0, entrance_fee=50_000)
        assert _score_spot(cheap, 126.97, 37.56, weights) > _score_spot(pricey, 126.97, 37.56, weights)


class TestThemeWeights:
    def test_all_themes_present(self):
        expected = {
            "mixed", "nature", "heritage", "urban", "festival",
            "leisure", "shopping", "food", "camping", "medical", "family",
        }
        assert expected.issubset(THEME_WEIGHTS.keys())

    def test_weights_are_normalized_per_theme(self):
        for theme, w in THEME_WEIGHTS.items():
            total = w.review + w.cost + w.distance + w.congestion
            assert abs(total - 1.0) < 1e-6, f"{theme} weights do not sum to 1"
