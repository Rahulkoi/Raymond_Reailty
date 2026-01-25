import json
import os


class PropertyIndex:
    def __init__(self):
        # app/rag/index.py → go up to app/
        app_dir = os.path.dirname(os.path.dirname(__file__))

        data_path = os.path.join(
            app_dir,
            "data",
            "properties.json"
        )

        with open(data_path, "r", encoding="utf-8") as f:
            self.properties = json.load(f)

    def search(self, location=None, max_price=None, bhk=None, property_type=None):
        """Search properties with multiple filters."""
        results = self.properties

        # Filter by location (matches location field or nearby landmarks)
        if location:
            location_lower = location.lower()
            results = [
                p for p in results
                if location_lower in p.get("location", "").lower()
                or location_lower in p.get("city", "").lower()
                or any(location_lower in landmark.lower() for landmark in p.get("nearby_landmarks", []))
                or location_lower in p.get("nearby_metro", "").lower()
            ]

        # Filter by max price
        if max_price:
            results = [
                p for p in results
                if p["price"] <= max_price
            ]

        # Filter by BHK
        if bhk:
            bhk_str = str(bhk).upper()
            if "BHK" not in bhk_str:
                bhk_str = f"{bhk} BHK"
            results = [
                p for p in results
                if bhk_str in p.get("bhk", "").upper()
            ]

        # Filter by property type (Apartment, Villa, Plot)
        if property_type:
            type_lower = property_type.lower()
            results = [
                p for p in results
                if type_lower in p.get("type", "").lower()
            ]

        # Sort by price (ascending)
        results.sort(key=lambda x: x["price"])

        return results[:5]

    def get_by_id(self, property_id):
        """Get a single property by ID."""
        for prop in self.properties:
            if prop["id"] == property_id:
                return prop
        return None

    def get_locations(self):
        """Get list of unique locations."""
        locations = set()
        for prop in self.properties:
            # Extract area name from location
            loc = prop.get("location", "").split(",")[0].strip()
            if loc:
                locations.add(loc)
        return sorted(locations)
