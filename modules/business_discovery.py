
import requests
from urllib.parse import quote


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

HEADERS = {
    "User-Agent": "VizagLeadFinder/1.0 (local business discovery project)"
}


def find_city_area(city):
    """Find the OpenStreetMap area for a city."""

    response = requests.get(
        NOMINATIM_URL,
        params={
            "q": f"{city}, Andhra Pradesh, India",
            "format": "jsonv2",
            "limit": 1
        },
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    results = response.json()

    if not results:
        raise ValueError(
            f"Could not find the city: {city}"
        )

    place = results[0]

    osm_type = place.get("osm_type")
    osm_id = int(place.get("osm_id"))

    if osm_type == "relation":
        return f"area({3600000000 + osm_id})"

    if osm_type == "way":
        return f"area({2400000000 + osm_id})"

    # Fallback: use the city's bounding box
    bounds = place.get("boundingbox")

    if not bounds:
        raise ValueError("City boundary was not available.")

    south, north, west, east = map(float, bounds)

    return (
        f"bbox:{south},{west},{north},{east}"
    )


def build_query(area, business_type):
    """Build an Overpass query for hotels and restaurants."""

    selectors = []

    if business_type in ["Both", "Restaurants"]:
        restaurant_tags = [
            ("amenity", "restaurant"),
            ("amenity", "fast_food"),
            ("amenity", "cafe")
        ]

        for key, value in restaurant_tags:
            selectors.extend([
                f'node["{key}"="{value}"]({area});',
                f'way["{key}"="{value}"]({area});',
                f'relation["{key}"="{value}"]({area});'
            ])

    if business_type in ["Both", "Hotels"]:
        hotel_tags = [
            ("tourism", "hotel"),
            ("tourism", "hostel"),
            ("tourism", "guest_house"),
            ("tourism", "motel")
        ]

        for key, value in hotel_tags:
            selectors.extend([
                f'node["{key}"="{value}"]({area});',
                f'way["{key}"="{value}"]({area});',
                f'relation["{key}"="{value}"]({area});'
            ])

    if area.startswith("bbox:"):
        bbox = area.replace("bbox:", "")

        selectors = [
            item.replace(f"({area})", f"({bbox})")
            for item in selectors
        ]

    return (
        "[out:json][timeout:60];\n"
        "(\n"
        + "\n".join(selectors)
        + "\n);\n"
        "out center tags;"
    )


def get_tag(tags, *keys):
    """Get the first available value from business tags."""

    for key in keys:
        value = tags.get(key)

        if value:
            return value.strip()

    return ""


def format_address(tags, city):
    """Create an address from available OpenStreetMap tags."""

    parts = [
        get_tag(tags, "addr:housenumber"),
        get_tag(tags, "addr:street"),
        get_tag(tags, "addr:suburb", "addr:neighbourhood"),
        get_tag(tags, "addr:city") or city,
        get_tag(tags, "addr:postcode")
    ]

    return ", ".join(
        part for part in parts if part
    )


def discover_businesses(
    city,
    max_results=10,
    business_type="Both"
):
    """Discover actual mapped business locations."""

    if business_type not in [
        "Both", "Restaurants", "Hotels"
    ]:
        raise ValueError("Invalid business type.")

    # Step 1: Find city boundary
    area = find_city_area(city)

    # Step 2: Build business search query
    query = build_query(area, business_type)

    # Step 3: Search OpenStreetMap
    response = requests.post(
        OVERPASS_URL,
        data={"data": query},
        headers=HEADERS,
        timeout=90
    )

    response.raise_for_status()

    elements = response.json().get("elements", [])

    leads = []
    seen = set()

    for item in elements:

        tags = item.get("tags", {})

        name = get_tag(tags, "name")

        # Ignore unnamed locations
        if not name:
            continue

        osm_type = item.get("type")
        osm_id = item.get("id")

        unique_id = f"{osm_type}/{osm_id}"

        if unique_id in seen:
            continue

        seen.add(unique_id)

        # Identify the business category
        if tags.get("tourism") in [
            "hotel", "hostel", "guest_house", "motel"
        ]:
            category = "hotel"
        else:
            category = "restaurant"

        # Get coordinates
        lat = item.get("lat")
        lon = item.get("lon")

        if "center" in item:
            lat = item["center"].get("lat", lat)
            lon = item["center"].get("lon", lon)

        # Get contact information
        phone = get_tag(
            tags,
            "phone",
            "contact:phone"
        )

        email = get_tag(
            tags,
            "email",
            "contact:email"
        )

        website = get_tag(
            tags,
            "website",
            "contact:website"
        )

        source_url = (
            f"https://www.openstreetmap.org/"
            f"{osm_type}/{osm_id}"
        )

        lead = {
            "business_name": name,
            "category": category,
            "website": website,
            "domain": "",
            "description": (
                f"Business location found in OpenStreetMap. "
                f"Type: {category}"
            ),
            "search_score": 0.5,
            "source_url": source_url,
            "website_status": "Not verified",
            "official_website": website,
            "phone": phone,
            "email": email,
            "address": format_address(tags, city),
            "latitude": lat,
            "longitude": lon,
            "data_source": "OpenStreetMap"
        }

        leads.append(lead)

    # Remove duplicates and apply requested limit
    return leads[:int(max_results)]
