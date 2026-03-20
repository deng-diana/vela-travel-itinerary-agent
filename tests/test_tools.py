from src.tools.live_daily_structure import get_daily_structure as get_live_daily_structure
from src.tools.mock_data import get_daily_structure, get_experiences, get_hotels, get_restaurants, get_weather
from src.tools.schemas import (
    DailyStructureInput,
    ExperienceSearchInput,
    HotelSearchInput,
    RestaurantSearchInput,
    WeatherInput,
)


def test_get_weather_tokyo_august():
    weather = get_weather(WeatherInput(destination="Tokyo", month="August"))
    assert weather.destination == "Tokyo"
    assert weather.avg_temp_c is not None


def test_get_hotels_returns_ranked_results():
    hotels = get_hotels(
        HotelSearchInput(
            destination="Tokyo",
            budget="mid",
            preferred_neighborhood="Aoyama",
        )
    )
    assert hotels
    assert hotels[0].neighborhood == "Aoyama"


def test_get_restaurants_returns_structured_results():
    restaurants = get_restaurants(
        RestaurantSearchInput(
            destination="Tokyo",
            interests=["food", "hidden gem"],
            neighborhoods=["Yanaka"],
            dietary_preferences=[],
        )
    )
    assert restaurants
    assert restaurants[0].reservation_link


def test_get_experiences_returns_structured_results():
    experiences = get_experiences(
        ExperienceSearchInput(
            destination="Tokyo",
            interests=["food", "hidden gem"],
            pace="balanced",
        )
    )
    assert experiences
    assert experiences[0].booking_link


def test_get_daily_structure_builds_days():
    days = get_daily_structure(
        DailyStructureInput(
            destination="Tokyo",
            month="August",
            trip_length_days=3,
            travel_party="couple",
            budget="mid",
            interests=["food", "hidden gems"],
            hotel_name="Aoyama Terrace Hotel",
            restaurant_names=["Aoyama Ember Counter", "Yanaka Lantern Izakaya"],
            experience_names=["Tsukiji Side-Street Food Crawl", "Yanaka Hidden Lanes Walk"],
            pace="balanced",
        )
    )
    assert len(days) == 3
    assert days[0].items


def test_get_daily_structure_balanced_days_have_full_skeleton():
    days = get_live_daily_structure(
        DailyStructureInput(
            destination="Tokyo",
            month="August",
            trip_length_days=3,
            travel_party="couple",
            budget="mid",
            interests=["food", "hidden gems"],
            hotel_name="Aoyama Terrace Hotel",
            restaurant_names=["Aoyama Ember Counter", "Yanaka Lantern Izakaya", "Nakameguro River Soba"],
            experience_names=[
                "Tsukiji Side-Street Food Crawl",
                "Yanaka Hidden Lanes Walk",
                "Kiyosumi Coffee and Gallery Circuit",
                "Meiji Shrine",
                "Shinjuku Gyoen Park",
                "Shibuya Crossing",
            ],
            pace="balanced",
        )
    )

    assert [item.kind for item in days[0].items][:2] == ["hotel", "restaurant"]
    # Balanced pace: multiple experiences per slot for a richer day
    day2 = days[1]
    morning_exp = [i for i in day2.items if i.time_label == "Morning" and i.kind == "experience"]
    afternoon_exp = [i for i in day2.items if i.time_label == "Afternoon" and i.kind == "experience"]
    assert len(morning_exp) >= 1, "Should have at least 1 morning experience"
    assert len(afternoon_exp) >= 1, "Should have at least 1 afternoon experience"
    assert any(i.time_label == "Lunch" and i.kind == "restaurant" for i in day2.items)
    assert any(i.time_label == "Dinner" and i.kind == "restaurant" for i in day2.items)


def test_get_daily_structure_packed_days_include_evening_anchor():
    days = get_live_daily_structure(
        DailyStructureInput(
            destination="Tokyo",
            month="August",
            trip_length_days=2,
            travel_party="solo",
            budget="mid",
            interests=["food", "culture"],
            hotel_name="Aoyama Terrace Hotel",
            restaurant_names=["Aoyama Ember Counter", "Yanaka Lantern Izakaya", "Nakameguro River Soba"],
            experience_names=[
                "Tsukiji Side-Street Food Crawl",
                "Yanaka Hidden Lanes Walk",
                "Kiyosumi Coffee and Gallery Circuit",
                "Meiji Shrine Evening Reset",
            ],
            pace="packed",
        )
    )

    assert any(item.time_label == "Evening" and item.kind == "experience" for item in days[0].items + days[1].items)
