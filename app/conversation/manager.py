print("🔥 LOADING ConversationManager")

import json
import re
from app.llm.openai_client import OpenAIClient
from app.rag.retriever import retrieve_properties
from app.response.response_builder import format_property_cards

MAX_HISTORY_TURNS = 4  # Reduced for speed

# Location mappings (includes misspellings)
KNOWN_LOCATIONS = {
    "bangalore": "Bangalore", "bengaluru": "Bangalore", "banglore": "Bangalore",
    "bangalor": "Bangalore", "bengalor": "Bangalore", "blr": "Bangalore",
    "thane": "Thane", "thana": "Thane",
    "mumbai": "Mumbai", "bombay": "Mumbai",
    "whitefield": "Whitefield", "electronic city": "Electronic City",
    "sarjapur": "Sarjapur Road", "yelahanka": "Yelahanka",
    "devanahalli": "Devanahalli", "koramangala": "Koramangala",
    "indiranagar": "Indiranagar", "hebbal": "Hebbal",
}


class ConversationManager:
    def __init__(self):
        self.llm = OpenAIClient()
        self.lead_data = {}
        self.lead_created = False
        self.history = []
        self.properties_discussed = False

    def handle_user_input(self, user_text: str):
        """Main entry - handle user message and return response."""

        # Extract entities from user text FIRST
        self._extract_entities_from_text(user_text)

        user_lower = user_text.lower().strip()

        # Check for end conversation
        if self._is_ending(user_lower):
            return self._end_conversation()

        # Check if asking about properties - DON'T use LLM for this!
        if self._is_property_query(user_lower):
            self.properties_discussed = True
            return self._respond_to_property_query()

        # For other cases, use LLM but keep it minimal
        llm_response = self._get_llm_response(user_text)

        # Check if user provided info
        if self._user_providing_info(user_text):
            return self._respond_to_info()

        # Use LLM response but ensure we ask for missing info
        result = {"text": llm_response}
        return self._add_lead_question(result)

    def _is_ending(self, text: str) -> bool:
        """Check if user wants to end conversation."""
        end_words = ["bye", "goodbye", "thanks", "thank you", "that's all",
                     "thats all", "done", "end", "see you", "talk later"]
        return any(word in text for word in end_words)

    def _is_property_query(self, text: str) -> bool:
        """Check if user is asking about properties."""
        property_words = ["property", "properties", "flat", "flats", "apartment",
                         "house", "home", "show me", "looking for", "interested",
                         "available", "options", "listings"]
        return any(word in text for word in property_words)

    def _user_providing_info(self, text: str) -> bool:
        """Check if user is providing personal info."""
        patterns = [
            r'\b[6-9]\d{9}\b',  # Phone
            r'@.*\.',  # Email
            r"(?:i am|i'm|my name is|call me)",  # Name
        ]
        return any(re.search(p, text.lower()) for p in patterns)

    def _respond_to_property_query(self):
        """Respond to property query with ACTUAL data - NO LLM hallucination."""
        location = self.lead_data.get("city")
        budget = self._parse_budget(self.lead_data.get("budget"))
        bhk = self.lead_data.get("configuration")

        # Get real properties from database
        properties = retrieve_properties(location=location, max_price=budget, bhk=bhk)

        print(f"🏠 Query: loc={location}, budget={budget}, bhk={bhk} → Found {len(properties)}")

        # Generate response from REAL data
        if properties:
            p = properties[0]
            price = self._format_price(p['price'])
            if location:
                text = f"Yes! We have {len(properties)} properties in {location}. Like {p['name']}, {p.get('bhk','')} at {price}."
            else:
                text = f"We have {len(properties)} great options. Like {p['name']}, {p.get('bhk','')} at {price}."
        else:
            # Still positive - we have properties nearby
            text = "We have excellent properties in that area. Let me find the best options for you."

        # NO PROPERTY CARDS HERE - only text
        result = {"text": text}
        return self._add_lead_question(result)

    def _respond_to_info(self):
        """Respond when user provides their info."""
        name = self.lead_data.get("fullName")
        phone = self.lead_data.get("mobileNumber")
        email = self.lead_data.get("emailAddress")

        if name and phone and email:
            text = f"Perfect {name}! Got all your details."
        elif name and phone:
            text = f"Thanks {name}! What's your email?"
        elif name:
            text = f"Hi {name}! What's your phone number?"
        elif phone:
            text = "Got it! What's your name?"
        else:
            text = "Thanks! What's your name?"

        result = {"text": text}

        # Auto-save when we have name + phone
        if name and phone:
            self._auto_save_lead()

        return result

    def _add_lead_question(self, result):
        """Add question for missing lead info."""
        if result.get("conversation_ended") or result.get("properties"):
            return result

        name = self.lead_data.get("fullName")
        phone = self.lead_data.get("mobileNumber")
        email = self.lead_data.get("emailAddress")

        # Only ask if we've discussed properties
        if self.properties_discussed or self.lead_data.get("city"):
            text = result.get("text", "")

            if not name:
                result["text"] = text + " What's your name?"
            elif not phone:
                result["text"] = text + f" {name.split()[0]}, your phone number?"
            elif not email:
                result["text"] = text + " And your email?"

        self._add_to_history(result["text"])
        return result

    def _end_conversation(self):
        """End conversation - show property cards NOW."""
        self._auto_save_lead()

        location = self.lead_data.get("city")
        budget = self._parse_budget(self.lead_data.get("budget"))
        bhk = self.lead_data.get("configuration")

        properties = retrieve_properties(location=location, max_price=budget, bhk=bhk)
        name = self.lead_data.get("fullName", "").split()[0] if self.lead_data.get("fullName") else ""

        if properties:
            cards = format_property_cards(properties, location, budget, bhk)
            text = f"Thanks{' '+name if name else ''}! Here are {len(cards)} properties for you. We'll call soon!"
            return {"text": text, "properties": cards, "conversation_ended": True}
        else:
            # Fallback to all properties
            all_props = retrieve_properties()
            if all_props:
                cards = format_property_cards(all_props[:5])
                text = f"Thanks{' '+name if name else ''}! Here are some great properties. We'll call soon!"
                return {"text": text, "properties": cards, "conversation_ended": True}

            return {"text": f"Thanks{' '+name if name else ''}! We'll call you soon!", "conversation_ended": True}

    def _get_llm_response(self, user_text: str) -> str:
        """Get LLM response - keep it minimal."""
        # Extract entities from LLM too
        raw = self.llm.generate(
            system_prompt=self._short_prompt(),
            user_text=user_text,
            history=self.history[-4:]  # Only last 2 turns
        )

        data = self._safe_json(raw)
        self._extract_llm_entities(data.get("arguments", {}))

        return data.get("response", "How can I help you today?")

    def _short_prompt(self):
        """Minimal system prompt for speed."""
        missing = []
        if not self.lead_data.get("fullName"): missing.append("name")
        if not self.lead_data.get("mobileNumber"): missing.append("phone")
        if not self.lead_data.get("emailAddress"): missing.append("email")

        return f"""You are Priya, real estate agent. Be brief (under 15 words).
Need from user: {', '.join(missing) if missing else 'nothing'}

Extract any info shared. Output JSON only:
{{"arguments":{{"name":null,"phone":null,"email":null,"city":null,"budget":null,"bhk":null}},"response":"brief reply"}}"""

    # ========== ENTITY EXTRACTION ========== #

    def _extract_entities_from_text(self, text: str):
        """Extract entities directly from text."""
        text_lower = text.lower()

        # Location
        if not self.lead_data.get("city"):
            for key, loc in KNOWN_LOCATIONS.items():
                if key in text_lower:
                    self.lead_data["city"] = loc
                    print(f"📍 Location: {loc}")
                    break

        # Phone
        if not self.lead_data.get("mobileNumber"):
            m = re.search(r'\b[6-9]\d{9}\b', text)
            if m:
                self.lead_data["mobileNumber"] = m.group()
                print(f"📞 Phone: {m.group()}")

        # Email
        if not self.lead_data.get("emailAddress"):
            m = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text)
            if m:
                self.lead_data["emailAddress"] = m.group()
                print(f"📧 Email: {m.group()}")

        # Name
        if not self.lead_data.get("fullName"):
            m = re.search(r"(?:i am|i'm|my name is|this is|call me)\s+([A-Za-z]+)", text, re.I)
            if m:
                name = m.group(1).title()
                if name.lower() not in ["looking", "interested", "fine", "good", "ok"]:
                    self.lead_data["fullName"] = name
                    print(f"👤 Name: {name}")

        # BHK
        if not self.lead_data.get("configuration"):
            m = re.search(r'([1-4])\s*(?:bhk|bedroom)', text_lower)
            if m:
                self.lead_data["configuration"] = f"{m.group(1)} BHK"
                print(f"🏠 BHK: {m.group(1)} BHK")

        # Budget
        if not self.lead_data.get("budget"):
            m = re.search(r'(\d+(?:\.\d+)?)\s*(cr|crore|lakh|lac)', text_lower)
            if m:
                self.lead_data["budget"] = f"{m.group(1)} {m.group(2)}"
                print(f"💰 Budget: {m.group(1)} {m.group(2)}")

    def _extract_llm_entities(self, args):
        """Extract entities from LLM response."""
        mapping = {
            "fullName": ["name"], "emailAddress": ["email"],
            "mobileNumber": ["phone"], "city": ["city", "location"],
            "budget": ["budget"], "configuration": ["bhk"]
        }
        for field, keys in mapping.items():
            for k in keys:
                if args.get(k) and not self.lead_data.get(field):
                    self.lead_data[field] = args[k]

    # ========== HELPERS ========== #

    def _format_price(self, price):
        if price >= 10000000:
            return f"{price/10000000:.1f} Cr"
        return f"{int(price/100000)} L"

    def _parse_budget(self, value):
        if not value: return None
        try:
            v = str(value).lower()
            if "cr" in v:
                return int(float(re.sub(r'[^\d.]', '', v.split('cr')[0])) * 10000000)
            if "la" in v:
                return int(float(re.sub(r'[^\d.]', '', v.split('la')[0])) * 100000)
            return int(float(re.sub(r'[^\d.]', '', v)) * 100000)
        except:
            return None

    def _safe_json(self, text):
        try:
            return json.loads(text)
        except:
            return {"response": text}

    def _add_to_history(self, text):
        self.history.append({"role": "assistant", "content": text})
        if len(self.history) > MAX_HISTORY_TURNS * 2:
            self.history = self.history[-MAX_HISTORY_TURNS * 2:]

    def _auto_save_lead(self):
        if self.lead_created: return
        if not (self.lead_data.get("fullName") and self.lead_data.get("mobileNumber")): return

        try:
            from app.crm.salesforce_auth import get_access_token
            from app.crm.create_lead import create_salesforce_lead

            token = get_access_token()
            payload = {"wl": {
                "fullName": self.lead_data.get("fullName", ""),
                "emailAddress": self.lead_data.get("emailAddress", ""),
                "mobileNumber": self.lead_data.get("mobileNumber", ""),
                "city": self.lead_data.get("city", "Bangalore"),
                "budget": str(self.lead_data.get("budget", "")),
                "configuration": self.lead_data.get("configuration", ""),
                "source": "AI_VOICE_BOT"
            }}
            create_salesforce_lead(payload, token["access_token"], token["instance_url"])
            self.lead_created = True
            print(f"✅ Lead saved: {self.lead_data.get('fullName')}")
        except Exception as e:
            print(f"❌ Lead save error: {e}")
