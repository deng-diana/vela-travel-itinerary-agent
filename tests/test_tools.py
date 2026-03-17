from src.tools.mock_data import get_weather, search_hotels, search_restaurants


def test_get_weather_known_city():
    w = get_weather("Shanghai")
    assert w["city"] == "Shanghai"
    assert w["temp_c"] is not None


def test_search_hotels():
    hotels = search_hotels("Shanghai")
    assert isinstance(hotels, list)
    assert all(h["city"] == "Shanghai" for h in hotels)


def test_search_restaurants():
    rs = search_restaurants("Hangzhou")
    assert isinstance(rs, list)
    assert all(r["city"] == "Hangzhou" for r in rs)

