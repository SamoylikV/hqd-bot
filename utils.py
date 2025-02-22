import os
import certifi
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.extra.rate_limiter import RateLimiter
from config import MY_ADDRESS, DELIVERY_FEE

os.environ['SSL_CERT_FILE'] = certifi.where()


def format_address(address):
    replacements = {
        "г.": "",
        "Г.": "",
        "санкт-петербург": "Санкт-Петербург",
        "кузнцовская": "Кузнецовская"
    }
    for key, value in replacements.items():
        address = address.replace(key, value)
    return address.strip()


#
# my_address = format_address("г. Санкт-петербург, Кузнецовская 9")
# customer_address = format_address("Г. Санкт-петербург, Светлановский проспект 103")

geolocator = Nominatim(
    user_agent="delivery_app",
    timeout=10
)
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)


def get_location(address):
    try:
        location = geocode(address)
        if location:
            return (location.latitude, location.longitude)
        return None
    except Exception as e:
        return None


def get_delivery_price(customer_address):
    try:
        coords_1 = get_location(format_address(MY_ADDRESS))
        coords_2 = get_location(format_address(customer_address))

        if coords_1 and coords_2:
            distance_km = geodesic(coords_1, coords_2).km
            distance_km *= 1.7
            base_price = DELIVERY_FEE
            price_per_km = 40
            delivery_price = base_price + (distance_km * price_per_km)
            return delivery_price
        else:
            return "none"
    except Exception:
        return "cringe"
