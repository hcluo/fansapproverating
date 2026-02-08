from app.services.aggregation import _weight


def test_weight_is_capped():
    assert _weight(-4) == 1
    assert _weight(3) == 3
    assert _weight(999) == 20
