def format_property_response(results, location=None, max_price=None):
    if not results:
        return "Sorry, I couldn't find any properties matching your criteria."

    count = len(results)

    price_text = ""
    if max_price:
        price_text = f" under ₹{_format_price(max_price)}"

    location_text = f" in {location}" if location else ""

    response = [
        f"I found {count} properties{location_text}{price_text}."
    ]

    for prop in results:
        response.append(
            f"{prop['name']} is a {prop['type']} located in {prop['location']}, priced at ₹{_format_price(prop['price'])}."
        )

    return " ".join(response)


def _format_price(price):
    if price >= 10_000_000:
        return f"{price / 10_000_000:.1f} Cr"
    elif price >= 100_000:
        return f"{price / 100_000:.1f} Lakh"
    return str(price)
