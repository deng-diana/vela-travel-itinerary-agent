from src.tools.mock_data import (
    get_daily_structure,
    get_experiences,
    get_hotels,
    get_restaurants,
    get_weather,
)
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
