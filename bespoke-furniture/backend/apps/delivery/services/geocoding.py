"""
Geocoding: resolve a DeliveryAddress to (latitude, longitude) via the Google
Geocoding API, and cache the result permanently on the address so repeat
orders to the same address never re-hit the API.

The real HTTP client is hidden behind GeocodingClient so tests can inject
FakeGeocodingClient and never spend API quota.
"""

import abc

import requests
from django.conf import settings
from django.utils import timezone


class GeocodingError(Exception):
    pass


class GeocodingClient(abc.ABC):
    @abc.abstractmethod
    def geocode(self, address_text: str) -> tuple[float, float]:
        """Return (latitude, longitude) for a free-text address, or raise GeocodingError."""


class GoogleGeocodingClient(GeocodingClient):
    ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.GOOGLE_MAPS_API_KEY
        if not self.api_key:
            raise GeocodingError(
                "GOOGLE_MAPS_API_KEY is not set. Add it to backend/.env (see .env.example)."
            )

    def geocode(self, address_text: str) -> tuple[float, float]:
        response = requests.get(self.ENDPOINT, params={"address": address_text, "key": self.api_key}, timeout=10)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "OK" or not payload.get("results"):
            raise GeocodingError(f"Geocoding failed for '{address_text}': {payload.get('status')}")
        location = payload["results"][0]["geometry"]["location"]
        return location["lat"], location["lng"]


class FakeGeocodingClient(GeocodingClient):
    """Deterministic fake for tests/local dev without a Google Maps API key."""

    def __init__(self, fixed_coordinates: dict[str, tuple[float, float]] | None = None):
        self.fixed_coordinates = fixed_coordinates or {}

    def geocode(self, address_text: str) -> tuple[float, float]:
        if address_text in self.fixed_coordinates:
            return self.fixed_coordinates[address_text]
        # Deterministic pseudo-coordinates around Sheffield, UK, derived from
        # a hash of the address text, so repeated calls are stable.
        seed = sum(ord(c) for c in address_text)
        lat = 53.38 + (seed % 100) / 1000
        lng = -1.47 + (seed % 77) / 1000
        return lat, lng


def address_to_text(address) -> str:
    parts = [address.line1, address.line2, address.city, address.county, address.postcode, address.country]
    return ", ".join(p for p in parts if p)


def geocode_address(address, client: GeocodingClient | None = None) -> None:
    """Geocode a DeliveryAddress in place and persist lat/lng if not already cached."""
    if address.is_geocoded:
        return
    client = client or GoogleGeocodingClient()
    lat, lng = client.geocode(address_to_text(address))
    address.latitude = lat
    address.longitude = lng
    address.geocoded_at = timezone.now()
    address.save(update_fields=["latitude", "longitude", "geocoded_at"])
