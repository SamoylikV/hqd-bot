import os
import re
import certifi
from geopy import Point
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.extra.rate_limiter import RateLimiter
from config import MY_ADDRESS, DELIVERY_FEE

os.environ['SSL_CERT_FILE'] = certifi.where()

class AddressProcessor:
    def __init__(self):
        self.city_keywords = {
            'спб', 'питер', 'санкт-петербург',
            'санктпетербург', 'saint-petersburg'
        }
        self.replace_patterns = {
            r'\bпр-т\b\.?': 'проспект',
            r'\bпр\b\.?': 'проспект',
            r'\bул\b\.?': 'улица',
            r'\bпер\b\.?': 'переулок',
            r'\bнаб\b\.?': 'набережная',
            r'\bш\b\.?': 'шоссе',
            r'\bд\b\.?': 'дом',
            r'\bк\b\.?': 'корпус',
            r'\bлит\b\.?': 'литера',
            r'\bстр\b\.?': 'строение',
            r'\bб-р\b': 'бульвар',
            r'\bпл\b\.?': 'площадь',
            r'\bг\.?\s?': '',
        }
        self.street_synonyms = {
            r'\bнвск\w+': 'невский',
            r'\bпосадск\w+': 'посадская',
            r'\bсветлановск\w+': 'светлановский',
            r'\bмайоров\w+': 'майорова'
        }
        self.duplicate_pattern = re.compile(
            r'\b(проспект|улица|переулок)\s+\1\b',
            re.IGNORECASE
        )

    def normalize_street_names(self, text):
        for typo, correct in self.street_synonyms.items():
            text = re.sub(typo, correct, text, flags=re.IGNORECASE)
        return text

    def remove_duplicates(self, text):
        return self.duplicate_pattern.sub(r'\1', text)

    def preprocess_address(self, address):
        address = address.lower().strip()
        address = re.sub(r'[^а-яё0-9\s-]', '', address)

        for pattern, replacement in self.replace_patterns.items():
            address = re.sub(pattern, replacement, address, flags=re.IGNORECASE)

        address = self.normalize_street_names(address)
        address = self.remove_duplicates(address)
        address = re.sub(r'\s+', ' ', address)
        return address

    def add_city_if_missing(self, address):
        if not any(keyword in address for keyword in self.city_keywords):
            return f'{address} санкт-петербург'
        return address

    def process_address(self, address):
        processed = self.preprocess_address(address)
        processed = self.add_city_if_missing(processed)
        return processed.title()

geolocator = Nominatim(
    user_agent="delivery_app_spb",
    timeout=10,
    domain='nominatim.openstreetmap.org'
)
geocode = RateLimiter(
    geolocator.geocode,
    min_delay_seconds=1,
    max_retries=2
)

VIEWBOX_SPB = [Point(59.8, 29.6), Point(60.1, 30.8)]

def get_location(address):
    try:
        processor = AddressProcessor()
        formatted_address = processor.process_address(address)

        location = geocode(
            formatted_address,
            viewbox=VIEWBOX_SPB,
            bounded=True,
            country_codes='ru',
            addressdetails=True,
            namedetails=True
        )

        if location and 'address' in location.raw:
            address_details = location.raw['address']
            city = address_details.get('city', '') or address_details.get('town', '')
            if not any(spb_keyword in city.lower() for spb_keyword in {'санкт-петербург', 'спб'}):
                return None

        return Point(location.latitude, location.longitude) if location else None
    except Exception:
        return None

def get_delivery_price(customer_address):
    try:
        processor = AddressProcessor()
        my_address = processor.process_address(MY_ADDRESS)
        customer_address_processed = processor.process_address(customer_address)

        point_1 = get_location(my_address)
        point_2 = get_location(customer_address_processed)

        if not point_1 or not point_2:
            return "none"

        distance_km = geodesic(point_1, point_2).km * 1.7
        delivery_price = DELIVERY_FEE + (distance_km * 40)
        return round(delivery_price, 2)

    except Exception:
        return "error"
