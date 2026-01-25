def format_price(price):
    """Format price in lakhs or crores for voice."""
    if price >= 10000000:  # 1 crore+
        crores = price / 10000000
        if crores == int(crores):
            return f"{int(crores)} crore"
        return f"{crores:.1f} crores"
    else:
        lakhs = price / 100000
        if lakhs == int(lakhs):
            return f"{int(lakhs)} lakhs"
        return f"{lakhs:.0f} lakhs"


def format_property_response(results, location=None, max_price=None, bhk=None):
    """Format property results for natural voice conversation."""
    if not results:
        return "I couldn't find any properties matching what you're looking for. Would you like to try a different location or budget range?"

    filtered = results

    if max_price:
        filtered = [p for p in filtered if p["price"] <= max_price]

    if bhk:
        bhk_str = str(bhk).upper()
        if "BHK" not in bhk_str:
            bhk_str = f"{bhk} BHK"
        filtered = [p for p in filtered if bhk_str in p.get("bhk", "").upper()]

    if not filtered:
        return "I found some properties, but none quite fit your criteria. Would you like me to show you options in a nearby area or a slightly different budget?"

    # Build natural response
    count = len(filtered)
    response = f"Great news! I found {count} {'property' if count == 1 else 'properties'} that might be perfect for you. "

    # Show top 2 for voice (keep it short)
    for i, prop in enumerate(filtered[:2]):
        price_str = format_price(prop["price"])
        area = prop.get("area_sqft", "")
        bhk_info = prop.get("bhk", "")
        metro = prop.get("nearby_metro", "")
        possession = prop.get("possession", "")

        if i == 0:
            response += f"First up is {prop['name']}, a {bhk_info} in {prop['location']}. "
            response += f"It's {area} square feet, priced at {price_str}. "
            if metro:
                response += f"The {metro.split('(')[0].strip()} is nearby. "
        else:
            response += f"Another great option is {prop['name']}, also a {bhk_info}, at {price_str}. "

        if possession and possession != "Ready to Move":
            response += f"Possession is expected by {possession}. "
        elif possession == "Ready to Move":
            response += "And it's ready to move in! "

    if count > 2:
        response += f"I have {count - 2} more options too. "

    response += "Would you like more details on any of these, or should I tell you about the amenities?"

    return response


def format_property_response_with_links(results, location=None, max_price=None, bhk=None):
    """Format property results with links for the final response after lead capture."""
    if not results:
        return "I couldn't find any properties matching what you're looking for right now, but our team will share some great options with you soon!"

    filtered = results

    if max_price:
        filtered = [p for p in filtered if p["price"] <= max_price]

    if bhk:
        bhk_str = str(bhk).upper()
        if "BHK" not in bhk_str:
            bhk_str = f"{bhk} BHK"
        filtered = [p for p in filtered if bhk_str in p.get("bhk", "").upper()]

    if not filtered:
        filtered = results[:3]  # Show top 3 anyway

    # Build voice-friendly response
    voice_response = f"Here are {min(len(filtered), 3)} properties I'd recommend. "

    for i, prop in enumerate(filtered[:3]):
        price_str = format_price(prop["price"])
        bhk_info = prop.get("bhk", "")

        voice_response += f"{prop['name']}, a {bhk_info} in {prop['location']} at {price_str}. "

        if prop.get("possession") == "Ready to Move":
            voice_response += "Ready to move. "

    voice_response += "I've shared the links with photos and virtual tours right here in our chat. "
    voice_response += "Our property expert will call you within 30 minutes to schedule site visits. "
    voice_response += "Would you like to know more about any of these?"

    return voice_response


def format_property_cards(results, location=None, max_price=None, bhk=None):
    """Format property results as cards with links for chat display."""
    if not results:
        return []

    filtered = results

    if max_price:
        filtered = [p for p in filtered if p["price"] <= max_price]

    if bhk:
        bhk_str = str(bhk).upper()
        if "BHK" not in bhk_str:
            bhk_str = f"{bhk} BHK"
        filtered = [p for p in filtered if bhk_str in p.get("bhk", "").upper()]

    if not filtered:
        filtered = results[:3]

    cards = []
    for prop in filtered[:3]:
        cards.append({
            "id": prop.get("id"),
            "name": prop.get("name"),
            "location": prop.get("location"),
            "price": format_price(prop.get("price", 0)),
            "price_raw": prop.get("price"),
            "bhk": prop.get("bhk"),
            "area_sqft": prop.get("area_sqft"),
            "type": prop.get("type"),
            "possession": prop.get("possession"),
            "builder": prop.get("builder"),
            "amenities": prop.get("amenities", [])[:4],
            "nearby_metro": prop.get("nearby_metro"),
            "nearby_mall": prop.get("nearby_mall"),
            "property_url": prop.get("property_url"),
            "virtual_tour_url": prop.get("virtual_tour_url"),
            "brochure_url": prop.get("brochure_url"),
            "images": prop.get("images", []),
            "contact_number": prop.get("contact_number")
        })

    return cards


def format_single_property(prop):
    """Format a single property with full details for voice."""
    price_str = format_price(prop["price"])

    response = f"{prop['name']} is a beautiful {prop.get('bhk', '')} {prop.get('type', 'property')} "
    response += f"in {prop['location']}. "
    response += f"It spans {prop.get('area_sqft', '')} square feet and is priced at {price_str}. "

    if prop.get('nearby_metro'):
        response += f"For connectivity, {prop['nearby_metro']}. "

    if prop.get('nearby_mall'):
        response += f"Shopping is easy with {prop['nearby_mall']}. "

    amenities = prop.get('amenities', [])
    if amenities:
        top_amenities = amenities[:3]
        response += f"The property features {', '.join(top_amenities)}. "

    response += f"It's by {prop.get('builder', 'a reputed builder')}. "

    if prop.get('property_url'):
        response += f"You can check out more details and photos on their website. "

    if prop.get('contact_number'):
        response += f"Or call {prop['contact_number']} to schedule a visit. "

    return response


def get_property_links(results, max_count=3):
    """Get property links for sending via email/SMS."""
    links = []
    for prop in results[:max_count]:
        links.append({
            "name": prop.get("name"),
            "url": prop.get("property_url"),
            "brochure": prop.get("brochure_url"),
            "virtual_tour": prop.get("virtual_tour_url"),
            "images": prop.get("images", []),
            "contact": prop.get("contact_number")
        })
    return links
