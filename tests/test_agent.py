import src.agent.orchestrator as orchestrator_module
from src.agent.orchestrator import AgentOrchestrator
from src.agent.intake import apply_pace_default
from src.agent.research import build_tool_plan, payloads_from_previous
from src.agent.state import ConversationState
from src.tools.schemas import (
    DayItem,
    DayPlan,
    ExperienceOption,
    HotelOption,
    ItineraryDraft,
    PlanningBrief,
    PlanningBriefPatch,
    RestaurantOption,
    WeatherSummary,
)


class _SilentMessages:
    def create(self, **kwargs):
        raise AssertionError("Unexpected LLM call during this test")


class _SilentClient:
    def __init__(self):
        self.messages = _SilentMessages()


def _sample_itinerary() -> ItineraryDraft:
    hotel = HotelOption(
        id="hotel-1",
        name="Aoyama Terrace Hotel",
        neighborhood="Aoyama",
        category="mid",
        nightly_rate_usd=260,
        affiliate_link="https://example.com/hotel",
        key_highlights=["Quiet street", "Walkable base"],
        short_description="A polished boutique stay near cafes and galleries.",
    )
    restaurant = RestaurantOption(
        id="restaurant-1",
        name="Yanaka Ember Counter",
        cuisine="Izakaya",
        price_range="$$",
        neighborhood="Yanaka",
        must_order_dish="charcoal skewers",
        reservation_link="https://example.com/restaurant",
        why_it_fits="Great for a relaxed food-forward evening.",
    )
    experience = ExperienceOption(
        id="experience-1",
        name="Yanaka Hidden Lanes Walk",
        category="Walking tour",
        duration_hours=2.5,
        estimated_cost_usd=35,
        neighborhood="Yanaka",
        booking_link="https://example.com/experience",
        best_time="Morning",
        why_it_fits="Adds local texture without forcing a packed day.",
    )
    return ItineraryDraft(
        destination="Tokyo",
        month="August",
        trip_length_days=3,
        travel_party="solo",
        budget="mid",
        interests=["food", "culture"],
        weather=WeatherSummary(
            destination="Tokyo",
            month="August",
            avg_temp_c=30,
            rainfall_mm=140,
            conditions_summary="Hot and humid with a chance of showers.",
            packing_notes=["Light layers", "Umbrella"],
        ),
        selected_hotel=hotel,
        hotels=[hotel],
        restaurants=[restaurant],
        experiences=[experience],
        days=[
            DayPlan(
                day_number=1,
                theme="Old Tokyo",
                summary="A soft landing in Yanaka.",
                items=[
                    DayItem(
                        time_label="Morning",
                        kind="experience",
                        title="Yanaka Hidden Lanes Walk",
                        neighborhood="Yanaka",
                        description="Ease into the neighborhood on foot.",
                        booking_link="https://example.com/experience",
                    )
                ],
            )
        ],
        summary="A balanced first draft for Tokyo.",
    )


def test_orchestrator_asks_clarifying_questions_when_fields_missing(monkeypatch):
    orchestrator = AgentOrchestrator(client=_SilentClient(), model="fake-model")
    state = ConversationState(session_id="session-1")

    monkeypatch.setattr(
        orchestrator_module,
        "extract_brief_patch",
        lambda *args, **kwargs: PlanningBriefPatch(destination="Tokyo", trip_length_days=3),
    )

    result = orchestrator.run(state=state, user_message="3 days in Tokyo")

    assert result.workspace_ready is False
    assert state.last_itinerary is None
    # Should be missing several fields (budget, travel_party, etc.)
    assert len(result.missing_fields) > 0
    assert any(f in result.missing_fields for f in ["budget", "travel_party", "hotel_preference"])


def test_orchestrator_keeps_asking_until_all_8_fields_filled(monkeypatch):
    orchestrator = AgentOrchestrator(client=_SilentClient(), model="fake-model")
    state = ConversationState(session_id="session-2")

    # Even with destination and trip_length, still missing other required fields
    monkeypatch.setattr(
        orchestrator_module,
        "extract_brief_patch",
        lambda *args, **kwargs: PlanningBriefPatch(),
    )

    result = orchestrator.run(state=state, user_message="Still deciding")

    assert result.workspace_ready is False
    assert result.itinerary is None
    assert "destination" in result.missing_fields
    assert "trip_length_days" in result.missing_fields


def test_build_tool_plan_selectively_skips_weather_for_budget_change():
    plan = build_tool_plan({"budget"}, has_existing_plan=True)

    # Budget change triggers hotels, restaurants, and estimate_budget (downstream)
    assert "get_hotels" in plan["gather_tools"]
    assert "get_restaurants" in plan["gather_tools"]
    assert "estimate_budget" in plan["gather_tools"]
    assert "get_weather" not in plan["gather_tools"]
    assert "get_experiences" not in plan["gather_tools"]


def test_build_tool_plan_only_reruns_weather_for_date_change():
    plan = build_tool_plan({"dates_or_month"}, has_existing_plan=True)

    # Date change triggers weather and packing (downstream dependency)
    assert "get_weather" in plan["gather_tools"]
    assert "get_packing_suggestions" in plan["gather_tools"]
    assert "get_hotels" not in plan["gather_tools"]
    assert "get_restaurants" not in plan["gather_tools"]


def test_build_tool_plan_reruns_hotels_and_restaurants_for_neighborhood_change():
    plan = build_tool_plan({"neighborhood_preference"}, has_existing_plan=True)

    assert plan["gather_tools"] == ["get_hotels", "get_restaurants"]


def test_trip_length_change_can_reuse_existing_gather_payloads():
    plan = build_tool_plan({"trip_length_days"}, has_existing_plan=True)

    assert plan["gather_tools"] == []


def test_apply_pace_default_fills_balanced_when_pace_is_missing():
    brief = apply_pace_default(PlanningBrief(destination="Tokyo", trip_length_days=3))

    assert brief.pace == "balanced"


def test_payloads_from_previous_preserves_unaffected_tool_results():
    payloads = payloads_from_previous(_sample_itinerary())

    assert payloads["get_weather"]["destination"] == "Tokyo"
    assert payloads["get_hotels"][0]["name"] == "Aoyama Terrace Hotel"
    assert payloads["get_restaurants"][0]["name"] == "Yanaka Ember Counter"
    assert payloads["get_experiences"][0]["name"] == "Yanaka Hidden Lanes Walk"
    assert payloads["get_daily_structure"][0]["day_number"] == 1
