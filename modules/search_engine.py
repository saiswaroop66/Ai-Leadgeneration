
from modules.geoapify_places import discover_businesses


def search_businesses(
    city,
    max_results=10,
    business_type="Both"
):
    """
    Search for actual hotels and restaurants using Geoapify Places API.
    Does not use general web article search results.
    """

    if not city or not city.strip():
        raise ValueError("Please enter a city.")

    if business_type not in ["Hotels", "Restaurants", "Both"]:
        raise ValueError("Invalid business category.")

    leads = discover_businesses(
        city=city.strip(),
        max_results=max_results,
        business_type=business_type
    )

    return leads
