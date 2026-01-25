from app.rag.index import PropertyIndex

property_index = PropertyIndex()


def retrieve_properties(location: str = None, max_price: int = None, bhk: str = None, property_type: str = None):
    """Retrieve properties matching the given criteria."""
    return property_index.search(
        location=location,
        max_price=max_price,
        bhk=bhk,
        property_type=property_type
    )


def get_property_by_id(property_id: str):
    """Get a specific property by ID."""
    return property_index.get_by_id(property_id)


def get_available_locations():
    """Get list of available locations."""
    return property_index.get_locations()
