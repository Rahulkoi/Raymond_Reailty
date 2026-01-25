"""
Property Search API - Lightweight endpoint for real-time property display
"""

import json
import re
from pathlib import Path
from fastapi import APIRouter, Query
from typing import Optional, List

router = APIRouter()

# Load properties data
PROPERTIES_FILE = Path(__file__).parent.parent / "data" / "properties.json"

def load_properties():
    try:
        with open(PROPERTIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

@router.get("/search")
async def search_properties(
    q: Optional[str] = Query(None, description="Search query text"),
    bhk: Optional[str] = Query(None, description="BHK filter (1, 2, 3, etc.)"),
    location: Optional[str] = Query(None, description="Location filter"),
    max_budget: Optional[float] = Query(None, description="Maximum budget in Cr")
) -> dict:
    """Search properties based on filters extracted from voice/text query."""

    properties = load_properties()
    results = []

    # Extract BHK from query if not provided
    if not bhk and q:
        bhk_match = re.search(r'(\d)\s*bhk', q.lower())
        if bhk_match:
            bhk = bhk_match.group(1)

    # Extract location keywords from query
    location_keywords = []

    # Location aliases to handle typos and variations
    location_aliases = {
        'banglore': 'bangalore',
        'bengaluru': 'bangalore',
        'blr': 'bangalore',
        'mumbai': 'mumbai',
        'bombay': 'mumbai',
        'thane': 'thane',
        'thaney': 'thane',
        'pune': 'pune',
        'poona': 'pune',
    }

    if location:
        loc_lower = location.lower()
        # Check for alias first
        if loc_lower in location_aliases:
            location_keywords.append(location_aliases[loc_lower])
        else:
            location_keywords.append(loc_lower)

    if q:
        q_lower = q.lower()

        # Check for aliases first (handles typos)
        for typo, correct in location_aliases.items():
            if typo in q_lower:
                location_keywords.append(correct)
                break

        # Common locations
        locations = ['thane', 'mumbai', 'bangalore', 'bengaluru', 'pune', 'navi mumbai',
                     'whitefield', 'electronic city', 'hsr', 'koramangala', 'indiranagar',
                     'bandra', 'andheri', 'powai', 'worli', 'goregaon']
        for loc in locations:
            if loc in q_lower and loc not in location_keywords:
                location_keywords.append(loc)

    # Extract budget from query
    if not max_budget and q:
        # Match patterns like "1 crore", "1.5 cr", "50 lakh", "2cr"
        cr_match = re.search(r'(\d+\.?\d*)\s*(?:crore|cr)', q.lower())
        lakh_match = re.search(r'(\d+\.?\d*)\s*(?:lakh|lac|l)', q.lower())
        if cr_match:
            max_budget = float(cr_match.group(1))
        elif lakh_match:
            max_budget = float(lakh_match.group(1)) / 100  # Convert to Cr

    for prop in properties:
        # BHK filter
        if bhk:
            prop_bhk = str(prop.get('bhk', '')).lower()
            if bhk not in prop_bhk and f"{bhk} bhk" not in prop_bhk:
                continue

        # Location filter
        if location_keywords:
            prop_location = prop.get('location', '').lower()
            prop_name = prop.get('name', '').lower()
            if not any(loc in prop_location or loc in prop_name for loc in location_keywords):
                continue

        # Budget filter (max_budget is in Cr)
        if max_budget:
            try:
                price = prop.get('price', 0)
                # Handle both numeric and string prices
                if isinstance(price, (int, float)):
                    price_in_cr = price / 10000000  # Convert to Cr
                else:
                    price_str = str(price).lower().replace(',', '')
                    price_num = re.search(r'([\d.]+)', price_str)
                    if price_num:
                        price_in_cr = float(price_num.group(1))
                        if 'lakh' in price_str or 'lac' in price_str:
                            price_in_cr = price_in_cr / 100
                    else:
                        price_in_cr = 0

                if price_in_cr > max_budget:
                    continue
            except:
                pass

        results.append(prop)

    # Limit results
    return {
        "properties": results[:5],
        "total": len(results)
    }
