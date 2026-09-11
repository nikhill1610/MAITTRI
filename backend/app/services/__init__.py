"""
app.services package
Combines legacy crop planning / recommendation services with the new
intelligent evidence-based fertilizer & pest decision engine.
"""

from .legacy_services import (
    CROP_ALIASES,
    SEASON_ALIASES,
    SOIL_ALIASES,
    normalize_crop_name,
    normalize_season,
    normalize_soil,
    nutrient_status,
    analyze_nutrients,
    score_crop,
    recommend,
    make_plan,
)

from .fertilizer_recommendation_service import (
    generate_comprehensive_recommendation,
    analyze_crop,
    analyze_previous_crop,
    analyze_soil,
    analyze_nutrients_status,
    generate_organic_fertilizer_options,
    generate_chemical_fertilizer_options,
    generate_comparison_card,
    analyze_pest_and_disease,
    evaluate_weather_risks,
    calculate_recommendation_confidence,
    build_human_readable_explanation,
    generate_step_by_step_roadmap,
    get_authoritative_sources,
)
