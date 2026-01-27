print("🔥 LOADING ConversationManager")

import json
import re
from app.llm.openai_client import OpenAIClient
from app.rag.retriever import retrieve_properties
from app.response.response_builder import format_property_cards

MAX_HISTORY_TURNS = 4

# Location mappings
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
        self.turn_count = 0

    def handle_user_input(self, user_text: str):
        """Main entry point."""
        self.turn_count += 1
        print(f"\n{'='*50}")
        print(f"📥 Turn {self.turn_count}: {user_text}")

        # Extract entities FIRST
        self._extract_entities_from_text(user_text)
        print(f"📋 Lead data after extraction: {self.lead_data}")

        user_lower = user_text.lower().strip()

        # Check for end conversation
        if self._is_ending(user_lower):
            print("🔚 User ending conversation")
            return self._end_conversation()

        # Generate response based on context
        response_text = self._generate_response(user_text, user_lower)

        # ALWAYS ask for missing info after first turn
        final_text = self._append_lead_question(response_text)

        print(f"📤 Final response: {final_text}")

        # Save to history
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": final_text})
        if len(self.history) > MAX_HISTORY_TURNS * 2:
            self.history = self.history[-MAX_HISTORY_TURNS * 2:]

        # Auto-save lead
        self._auto_save_lead()

        return {"text": final_text}

    def _generate_response(self, user_text: str, user_lower: str) -> str:
        """Generate appropriate response based on user input."""

        # If user is asking about properties
        if self._is_property_query(user_lower):
            return self._property_response()

        # If user is providing info (name, phone, email)
        if self._is_providing_info(user_text):
            return self._info_acknowledgment()

        # General conversation - use minimal LLM
        return self._llm_response(user_text)

    def _is_ending(self, text: str) -> bool:
        end_words = ["bye", "goodbye", "thanks", "thank you", "that's all",
                     "thats all", "done", "end", "see you", "later"]
        return any(word in text for word in end_words)

    def _is_property_query(self, text: str) -> bool:
        words = ["property", "properties", "flat", "flats", "apartment",
                 "house", "home", "show me", "looking for", "interested",
                 "available", "options", "listing"]
        return any(word in text for word in words)

    def _is_providing_info(self, text: str) -> bool:
        # Phone number
        if re.search(r'\b[6-9]\d{9}\b', text):
            return True
        # Email
        if re.search(r'@.*\.', text):
            return True
        # Name patterns
        if re.search(r"(?:i am|i'm|my name is|call me|this is)\s+\w+", text.lower()):
            return True
        return False

    def _property_response(self) -> str:
        """Generate response for property query using REAL data."""
        location = self.lead_data.get("city")
        budget = self._parse_budget(self.lead_data.get("budget"))
        bhk = self.lead_data.get("configuration")

        properties = retrieve_properties(location=location, max_price=budget, bhk=bhk)
        print(f"🏠 Search: loc={location}, budget={budget}, bhk={bhk} → {len(properties)} found")

        if properties:
            p = properties[0]
            price = self._format_price(p['price'])
            if location:
                return f"Yes! We have {len(properties)} properties in {location}. Like {p['name']}, {p.get('bhk','')} at {price}."
            else:
                return f"We have {len(properties)} great options! Like {p['name']}, {p.get('bhk','')} at {price}."
        else:
            return "We have excellent properties available. Which area interests you?"

    def _info_acknowledgment(self) -> str:
        """Acknowledge info provided by user."""
        name = self.lead_data.get("fullName")
        phone = self.lead_data.get("mobileNumber")
        email = self.lead_data.get("emailAddress")

        if name and phone and email:
            return f"Perfect {name}! Got all your details."
        elif name and phone:
            return f"Thanks {name}! Got your number."
        elif name:
            return f"Hi {name}! Nice to meet you."
        elif phone:
            return "Got your number!"
        elif email:
            return "Got your email!"
        else:
            return "Thanks!"

    def _llm_response(self, user_text: str) -> str:
        """Get minimal LLM response."""
        try:
            raw = self.llm.generate(
                system_prompt=self._minimal_prompt(),
                user_text=user_text,
                history=self.history[-4:]
            )
            data = self._safe_json(raw)
            self._extract_llm_entities(data.get("arguments", {}))
            return data.get("response", "How can I help you?")
        except Exception as e:
            print(f"❌ LLM error: {e}")
            return "How can I help you with properties today?"

    def _append_lead_question(self, response_text: str) -> str:
        """ALWAYS append question for missing lead info."""
        name = self.lead_data.get("fullName")
        phone = self.lead_data.get("mobileNumber")
        email = self.lead_data.get("emailAddress")

        print(f"🔍 Checking lead: name={name}, phone={phone}, email={email}")

        # After first turn, always ask for missing critical info
        if self.turn_count >= 1:
            if not name:
                print("➕ Adding name question")
                return response_text + " What's your name?"
            elif not phone:
                print("➕ Adding phone question")
                first_name = name.split()[0] if name else ""
                return response_text + f" {first_name}, what's your phone number?"
            elif not email:
                print("➕ Adding email question")
                return response_text + " And your email address?"

        return response_text

    def _end_conversation(self):
        """End conversation and show property cards."""
        self._auto_save_lead()

        location = self.lead_data.get("city")
        budget = self._parse_budget(self.lead_data.get("budget"))
        bhk = self.lead_data.get("configuration")

        properties = retrieve_properties(location=location, max_price=budget, bhk=bhk)
        name = self.lead_data.get("fullName", "").split()[0] if self.lead_data.get("fullName") else ""

        if properties:
            cards = format_property_cards(properties, location, budget, bhk)
            text = f"Thanks{' ' + name if name else ''}! Here are {len(cards)} properties. We'll call you soon!"
            print(f"📤 Ending with {len(cards)} property cards")
            return {"text": text, "properties": cards, "conversation_ended": True}
        else:
            all_props = retrieve_properties()
            if all_props:
                cards = format_property_cards(all_props[:5])
                text = f"Thanks{' ' + name if name else ''}! Here are some properties. We'll call soon!"
                return {"text": text, "properties": cards, "conversation_ended": True}

        return {"text": f"Thanks{' ' + name if name else ''}! We'll call you soon!", "conversation_ended": True}

    # ========== ENTITY EXTRACTION ========== #

    def _extract_entities_from_text(self, text: str):
        """Extract all entities from user text."""
        text_lower = text.lower()

        # Location
        if not self.lead_data.get("city"):
            for key, loc in KNOWN_LOCATIONS.items():
                if key in text_lower:
                    self.lead_data["city"] = loc
                    print(f"📍 Extracted location: {loc}")
                    break

        # Phone (Indian 10-digit)
        if not self.lead_data.get("mobileNumber"):
            m = re.search(r'\b[6-9]\d{9}\b', text)
            if m:
                self.lead_data["mobileNumber"] = m.group()
                print(f"📞 Extracted phone: {m.group()}")

        # Email
        if not self.lead_data.get("emailAddress"):
            m = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text)
            if m:
                self.lead_data["emailAddress"] = m.group()
                print(f"📧 Extracted email: {m.group()}")

        # Name - multiple patterns
        if not self.lead_data.get("fullName"):
            patterns = [
                r"(?:i am|i'm|my name is|this is|call me|it's|its)\s+([A-Za-z]+)",
                r"^([A-Z][a-z]{2,})$",  # Single capitalized word
            ]
            for pattern in patterns:
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    name = m.group(1).strip().title()
                    skip = ["looking", "interested", "fine", "good", "ok", "yes", "no", "hi", "hello"]
                    if name.lower() not in skip and len(name) > 1:
                        self.lead_data["fullName"] = name
                        print(f"👤 Extracted name: {name}")
                        break

        # BHK
        if not self.lead_data.get("configuration"):
            m = re.search(r'([1-4])\s*(?:bhk|bedroom|bed)', text_lower)
            if m:
                self.lead_data["configuration"] = f"{m.group(1)} BHK"
                print(f"🏠 Extracted BHK: {m.group(1)} BHK")

        # Budget
        if not self.lead_data.get("budget"):
            m = re.search(r'(\d+(?:\.\d+)?)\s*(cr|crore|lakh|lac)', text_lower)
            if m:
                self.lead_data["budget"] = f"{m.group(1)} {m.group(2)}"
                print(f"💰 Extracted budget: {m.group(1)} {m.group(2)}")

    def _extract_llm_entities(self, args):
        """Extract entities from LLM response."""
        if not args:
            return
        mapping = {
            "fullName": ["name"],
            "emailAddress": ["email"],
            "mobileNumber": ["phone"],
            "city": ["city", "location"],
            "budget": ["budget"],
            "configuration": ["bhk"]
        }
        for field, keys in mapping.items():
            for k in keys:
                val = args.get(k)
                if val and val != "null" and not self.lead_data.get(field):
                    self.lead_data[field] = val
                    print(f"🔍 LLM extracted {field}: {val}")

    # ========== HELPERS ========== #

    def _minimal_prompt(self):
        missing = []
        if not self.lead_data.get("fullName"): missing.append("name")
        if not self.lead_data.get("mobileNumber"): missing.append("phone")
        if not self.lead_data.get("emailAddress"): missing.append("email")

        return f"""Real estate agent. Brief reply (under 15 words).
Extract info shared. Need: {', '.join(missing) if missing else 'all collected'}
JSON only: {{"arguments":{{"name":null,"phone":null,"email":null}},"response":"reply"}}"""

    def _format_price(self, price):
        if price >= 10000000:
            return f"{price/10000000:.1f} Cr"
        return f"{int(price/100000)} L"

    def _parse_budget(self, value):
        if not value:
            return None
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

    def _auto_save_lead(self):
        if self.lead_created:
            return
        if not (self.lead_data.get("fullName") and self.lead_data.get("mobileNumber")):
            return

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
            print(f"✅ Lead saved: {self.lead_data.get('fullName')} - {self.lead_data.get('mobileNumber')}")
        except Exception as e:
            print(f"❌ Lead save error: {e}")
