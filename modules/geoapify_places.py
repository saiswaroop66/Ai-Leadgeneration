
import os
import requests

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEOAPIFY_API_KEY")

GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
PLACES_URL = "https://api.geoapify.com/v2/places"
DETAILS_URL = "https://api.geoapify.com/v2/place-details"


# ONLY PROPER HOTELS AND RESTAURANTS

RESTAURANT_CATEGORIES = [
    "catering.restaurant"
]

HOTEL_CATEGORIES = [
    "accommodation.hotel"
]


def get_city_coordinates(city):

    response = requests.get(
        GEOCODE_URL,
        params={
            "text": f"{city}, Andhra Pradesh, India",
            "format": "json",
            "limit": 1,
            "apiKey": API_KEY
        },
        timeout=30
    )

    response.raise_for_status()

    results = response.json().get("results", [])

    if not results:
        raise ValueError(f"City not found: {city}")

    return (
        float(results[0]["lon"]),
        float(results[0]["lat"])
    )


def get_categories(business_type):

    if business_type == "Restaurants":
        return RESTAURANT_CATEGORIES

    elif business_type == "Hotels":
        return HOTEL_CATEGORIES

    elif business_type == "Both":
        return RESTAURANT_CATEGORIES + HOTEL_CATEGORIES

    raise ValueError("Invalid business type")


def clean_contact(value):

    if not value:
        return ""

    values = value if isinstance(value, list) else [value]

    cleaned = []

    for item in values:

        if isinstance(item, str):

            item = item.strip()

            if item and item not in cleaned:
                cleaned.append(item)

    return " | ".join(cleaned)


def get_place_details(place_id):

    if not place_id:
        return {}

    response = requests.get(
        DETAILS_URL,
        params={
            "id": place_id,
            "apiKey": API_KEY
        },
        timeout=30
    )

    response.raise_for_status()

    features = response.json().get("features", [])

    for feature in features:

        properties = feature.get("properties", {})

        if properties.get("feature_type") == "details":
            return properties

    if features:
        return features[0].get("properties", {})

    return {}


def extract_contact_details(base_properties, details):

    base_source = base_properties.get("datasource") or {}
    base_raw = base_source.get("raw") or {}

    detail_source = details.get("datasource") or {}
    detail_raw = detail_source.get("raw") or {}

    contact = details.get("contact") or {}

    # PHONE

    phone_values = [
        contact.get("phone"),
        details.get("phone"),
        base_properties.get("phone"),
        base_raw.get("phone"),
        base_raw.get("contact:phone"),
        detail_raw.get("phone"),
        detail_raw.get("contact:phone")
    ]

    phone_other = (
        contact.get("phone_other")
        or details.get("phone_other")
        or []
    )

    if isinstance(phone_other, list):
        phone_values.extend(phone_other)

    phone = clean_contact(phone_values)

    # EMAIL

    email_values = [
        contact.get("email"),
        details.get("email"),
        base_properties.get("email"),
        base_raw.get("email"),
        base_raw.get("contact:email"),
        detail_raw.get("email"),
        detail_raw.get("contact:email")
    ]

    email_other = (
        contact.get("email_other")
        or details.get("email_other")
        or []
    )

    if isinstance(email_other, list):
        email_values.extend(email_other)

    email = clean_contact(email_values)

    # WEBSITE

    website_values = [
        details.get("website"),
        base_properties.get("website"),
        base_raw.get("website"),
        base_raw.get("contact:website"),
        detail_raw.get("website"),
        detail_raw.get("contact:website")
    ]

    website = clean_contact(website_values)

    return {
        "phone": phone,
        "email": email,
        "website": website,

        "phone_source": (
            "Geoapify Place Details"
            if phone else "Not publicly listed in Geoapify"
        ),

        "email_source": (
            "Geoapify Place Details"
            if email else "Not publicly listed in Geoapify"
        ),

        "website_source": (
            "Geoapify Place Details"
            if website else "No website listed in Geoapify"
        )
    }


def discover_businesses(
    city="Visakhapatnam",
    max_results=10,
    business_type="Both"
):

    if not API_KEY:
        raise ValueError(
            "GEOAPIFY_API_KEY is missing from your .env file."
        )

    if not city or not city.strip():
        raise ValueError("Please enter a city.")

    longitude, latitude = get_city_coordinates(city)

    categories = get_categories(business_type)

    params = {
        "categories": ",".join(categories),

        "filter": (
            f"circle:{longitude},{latitude},20000"
        ),

        "bias": (
            f"proximity:{longitude},{latitude}"
        ),

        "limit": min(max(int(max_results), 1), 100),

        "lang": "en",

        "apiKey": API_KEY
    }

    response = requests.get(
        PLACES_URL,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    features = response.json().get("features", [])

    leads = []
    seen = set()

    for feature in features:

        properties = feature.get("properties", {})

        datasource = properties.get("datasource") or {}
        raw = datasource.get("raw") or {}

        name = (
            properties.get("name")
            or raw.get("name")
            or ""
        ).strip()

        if not name:
            continue

        all_categories = properties.get("categories", [])

        # STRICT CATEGORY FILTER

        is_restaurant = any(
            category == "catering.restaurant"
            or category.startswith("catering.restaurant.")
            for category in all_categories
        )

        is_hotel = any(
            category == "accommodation.hotel"
            or category.startswith("accommodation.hotel.")
            for category in all_categories
        )

        if business_type == "Restaurants" and not is_restaurant:
            continue

        if business_type == "Hotels" and not is_hotel:
            continue

        if business_type == "Both" and not (
            is_restaurant or is_hotel
        ):
            continue

        category = (
            "Hotels" if is_hotel else "Restaurants"
        )

        place_id = properties.get("place_id")

        unique_key = (
            str(place_id)
            if place_id
            else name.lower() + str(properties.get("formatted", ""))
        )

        if unique_key in seen:
            continue

        seen.add(unique_key)

        # GET ADDITIONAL BUSINESS DETAILS

        details = {}

        if place_id:

            try:
                details = get_place_details(place_id)

            except requests.RequestException as error:
                print(
                    f"Contact lookup failed for {name}: {error}"
                )

        contacts = extract_contact_details(
            properties,
            details
        )

        address = properties.get("formatted", "")

        longitude_value = properties.get("lon")
        latitude_value = properties.get("lat")

        source_url = ""

        if (
            longitude_value is not None
            and latitude_value is not None
        ):

            source_url = (
                "https://www.openstreetmap.org/"
                f"?mlat={latitude_value}&mlon={longitude_value}"
            )

        website = contacts["website"]

        lead = {

            "business_name": name,

            "category": category,

            "website": website,

            "official_website": website,

            "domain": "",

            "description": (
                details.get("description")
                or f"{category} discovered using Geoapify."
            ),

            "search_score": 0.5,

            "source_url": source_url,

            "website_status": (
                "Website listed - needs verification"
                if website
                else "No website listed - needs verification"
            ),

            "verification_evidence": "",

            "verification_source": "",

            "phone": contacts["phone"],

            "email": contacts["email"],

            "phone_source": contacts["phone_source"],

            "email_source": contacts["email_source"],

            "website_source": contacts["website_source"],

            "address": address,

            "latitude": latitude_value,

            "longitude": longitude_value,

            "place_id": place_id,

            "data_source": "Geoapify"

        }

        leads.append(lead)

    return leads
