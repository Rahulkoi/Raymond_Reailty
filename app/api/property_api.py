"""
Simple Property Search API for voice bot
"""

from fastapi import APIRouter
from typing import Optional
from app.rag.retriever import retrieve_properties

router = APIRouter()


@router.get("/search")
def search_properties(
    location: Optional[str] = None,
    bhk: Optional[str] = None,
    budget: Optional[str] = None
):
    """Search properties based on filters."""

    # Parse budget to number
    max_price = None
    if budget:
        budget_lower = budget.lower()
        try:
            if "cr" in budget_lower:
                num = float(''.join(c for c in budget_lower.split('cr')[0] if c.isdigit() or c == '.'))
                max_price = int(num * 10000000)
            elif "lakh" in budget_lower or "lac" in budget_lower:
                num = float(''.join(c for c in budget_lower.split('la')[0] if c.isdigit() or c == '.'))
                max_price = int(num * 100000)
        except:
            pass

    # Get properties from retriever
    properties = retrieve_properties(
        location=location,
        max_price=max_price,
        bhk=bhk
    )

    print(f"🏠 Property search: location={location}, bhk={bhk}, budget={budget} → {len(properties)} found")

    # If no properties found, return Raymond Realty as fallback
    is_fallback = False
    if not properties:
        is_fallback = True
        all_props = retrieve_properties()
        properties = [p for p in all_props if 'raymond' in p.get('builder', '').lower()][:5]

        if not properties:
            properties = all_props[:5]

    # Format response
    cards = []
    for p in properties[:5]:
        cards.append({
            "name": p.get("name", ""),
            "price": p.get("price", 0),
            "bhk": p.get("bhk", ""),
            "type": p.get("type", "Apartment"),
            "location": p.get("location", ""),
            "area_sqft": p.get("area_sqft", 0),
            "possession": p.get("possession", ""),
            "builder": p.get("builder", ""),
            "property_url": p.get("property_url", ""),
            "virtual_tour_url": p.get("virtual_tour_url", ""),
            "contact_number": p.get("contact_number", "")
        })

    return {
        "success": True,
        "count": len(cards),
        "is_fallback": is_fallback,
        "properties": cards
    }
