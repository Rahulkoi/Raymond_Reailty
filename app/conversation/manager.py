print("ConversationManager v5.2 - Fixed email validation + responsive property display")

import json
import re
from difflib import get_close_matches
from app.llm.openai_client import OpenAIClient
from app.rag.retriever import retrieve_properties
from app.response.response_builder import format_property_cards

# Known cities for fuzzy matching
KNOWN_CITIES = ["Bangalore", "Mumbai", "Thane", "Whitefield", "Electronic City",
                "Sarjapur", "Yelahanka", "Hebbal", "Bandra", "Andheri", "Powai"]

SYSTEM_PROMPT = """You are Priya, a friendly real estate assistant for Raymond Realty.

RULES:
1. Keep responses SHORT (1-2 sentences max)
2. Be warm and conversational like a real person
3. Collect: name, phone, email - naturally in conversation
4. Remember context throughout the conversation

CURRENT STATUS:
{status}

CONVERSATION SO FAR:
{context}

RESPOND NATURALLY based on what's missing or what user is asking."""


class ConversationManager:
    """Intelligent human-like conversation manager."""

    def __init__(self):
        print("New ConversationManager session started")
        self.llm = OpenAIClient()
        self.lead = {}
        self.lead_saved = False
        self.history = []
        self.pending_validation = None  # Track if we're waiting for correction

    def handle_user_input(self, user_text: str) -> dict:
        """Process user message intelligently."""
        print(f"\n{'='*60}")
        print(f"User: '{user_text}'")

        # Step 1: Smart extraction with validation
        validation_issue = self._smart_extract(user_text)
        print(f"Lead data: {self.lead}")

        # Step 2: Add to history
        self.history.append({"role": "user", "content": user_text})

        # Step 3: If there's a validation issue, ask for correction
        if validation_issue:
            print(f"Validation issue: {validation_issue}")
            self.history.append({"role": "assistant", "content": validation_issue})
            return {"text": validation_issue}

        # Step 4: Check if user wants to end
        if self._wants_to_end(user_text):
            return self._farewell_with_properties()

        # Step 5: Check if user explicitly wants properties NOW
        if self._wants_properties_now(user_text):
            # If we have at least name and phone, show properties
            if self.lead.get("name") and self.lead.get("phone"):
                return self._farewell_with_properties()
            # If we have name but no phone, still show but ask for contact
            elif self.lead.get("name"):
                return self._farewell_with_properties()

        # Step 6: If all info collected, auto-show properties
        if self._has_all_info():
            response = self._generate_response(user_text)
            # Auto-show properties if LLM mentions showing
            if "show" in response.lower() or "here" in response.lower():
                return self._farewell_with_properties()

        # Step 7: Generate intelligent response
        response = self._generate_response(user_text)
        print(f"Bot: {response}")

        self.history.append({"role": "assistant", "content": response})
        self._try_save_lead()

        return {"text": response}

    def _smart_extract(self, text: str) -> str:
        """Smart extraction with validation. Returns error message if validation fails."""
        t = text.lower().strip()

        # --- CITY DETECTION (Fuzzy matching) ---
        detected_city = self._detect_city(t)
        if detected_city:
            self.lead["city"] = detected_city
            print(f"  City detected: {detected_city}")

        # --- PHONE DETECTION with validation ---
        # Look for any sequence of digits (skip if we already have valid phone)
        if not self.lead.get("phone"):
            digits = re.sub(r'\D', '', text)
            if len(digits) >= 7:  # Looks like a phone attempt
                if len(digits) == 10 and digits[0] in '6789':
                    self.lead["phone"] = digits
                    print(f"  Phone: {digits}")
                else:
                    # Invalid phone - ask for correction with friendly message
                    if len(digits) < 10:
                        return f"That seems incomplete - just {len(digits)} digits. Could you share your full 10-digit mobile number?"
                    elif len(digits) > 10:
                        return f"That's a few extra digits. Could you share just your 10-digit mobile number?"
                    elif digits[0] not in '6789':
                        return "Indian mobile numbers usually start with 6, 7, 8, or 9. Could you please check?"

        # --- EMAIL DETECTION with validation ---
        # Look for anything with @ symbol (skip if we already have valid email)
        if '@' in text and not self.lead.get("email"):
            # Clean the text - remove trailing punctuation
            clean_text = text.rstrip('.,!?;:')
            email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', clean_text)
            if email_match:
                email = email_match.group().lower().rstrip('.')  # Remove any trailing dots

                # Extract domain part for validation
                domain = email.split('@')[1] if '@' in email else ''

                # Check for common TLD typos (only at the END of email)
                tld_typos = {
                    '.cm': '.com',
                    '.con': '.com',
                    '.cpm': '.com',
                    '.vom': '.com',
                    '.ocm': '.com',
                    '.comm': '.com',
                    '.coм': '.com',
                    '.iin': '.in',
                    '.orgg': '.org',
                }

                for typo, correction in tld_typos.items():
                    if email.endswith(typo):
                        suggested = email[:-len(typo)] + correction
                        return f"Did you mean {suggested}? Just want to make sure I have it right."

                # Check for common domain typos (exact domain match only)
                domain_typos = {
                    'gmial.com': 'gmail.com',
                    'gmal.com': 'gmail.com',
                    'gamil.com': 'gmail.com',
                    'gnail.com': 'gmail.com',
                    'gmaill.com': 'gmail.com',
                    'gmali.com': 'gmail.com',
                    'yaho.com': 'yahoo.com',
                    'yahooo.com': 'yahoo.com',
                    'yaoo.com': 'yahoo.com',
                    'hotmal.com': 'hotmail.com',
                    'hotmial.com': 'hotmail.com',
                    'outloo.com': 'outlook.com',
                    'outlok.com': 'outlook.com',
                }

                if domain in domain_typos:
                    suggested = email.replace(domain, domain_typos[domain])
                    return f"Did you mean {suggested}? Just want to make sure I have it right."

                # Validate domain has proper TLD
                valid_tlds = ['com', 'in', 'org', 'net', 'co', 'io', 'edu', 'gov', 'info', 'biz', 'co.in', 'org.in', 'ac.in', 'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
                has_valid_tld = any(email.endswith('.' + tld) or email.endswith('@' + tld) for tld in valid_tlds)

                if not has_valid_tld:
                    return f"That email doesn't look quite right. Could you please check and share it again?"
                else:
                    self.lead["email"] = email
                    print(f"  Email: {email}")
            else:
                return "That email doesn't look quite right. Could you please share it again?"

        # --- NAME DETECTION ---
        if not self.lead.get("name"):
            # Check for name patterns
            name_patterns = [
                r"(?:my name is|i am|i'm|this is|call me|it's|its)\s+([a-zA-Z]+)",
                r"^([A-Z][a-z]{2,15})$"  # Single capitalized word (2-15 chars)
            ]
            excluded = ["looking", "interested", "fine", "good", "ok", "yes", "no",
                       "bye", "goodbye", "thanks", "thank", "hi", "hello", "hey",
                       "show", "property", "apartment", "flat", "house", "home",
                       "schedule", "site", "visit", "want", "need", "please",
                       "great", "awesome", "sure", "okay", "yeah", "yup", "nope"]

            for p in name_patterns:
                m = re.search(p, text, re.I)
                if m:
                    name = m.group(1).title()
                    if name.lower() not in excluded and 2 <= len(name) <= 20:
                        self.lead["name"] = name
                        print(f"  Name: {name}")
                        break

        # --- BHK DETECTION ---
        bhk_match = re.search(r'([1-4])\s*(?:bhk|bedroom|bed)', t)
        if bhk_match:
            self.lead["bhk"] = f"{bhk_match.group(1)} BHK"
            print(f"  BHK: {self.lead['bhk']}")

        # --- BUDGET DETECTION ---
        budget_match = re.search(r'(\d+(?:\.\d+)?)\s*(cr|crore|lakh|lac|l)\b', t)
        if budget_match:
            num = budget_match.group(1)
            unit = budget_match.group(2)
            if unit in ['cr', 'crore']:
                self.lead["budget"] = f"{num} crore"
            else:
                self.lead["budget"] = f"{num} lakh"
            print(f"  Budget: {self.lead['budget']}")

        return None  # No validation issues

    def _detect_city(self, text: str) -> str:
        """Fuzzy match city names from user text."""
        text = text.lower()

        # Direct mappings (including common variations)
        direct_map = {
            "bangalore": "Bangalore", "bengaluru": "Bangalore", "blr": "Bangalore",
            "mumbai": "Mumbai", "bombay": "Mumbai",
            "thane": "Thane",
            "whitefield": "Whitefield",
            "electronic city": "Electronic City", "ec": "Electronic City",
        }

        for key, city in direct_map.items():
            if key in text:
                return city

        # Fuzzy matching for typos
        words = text.split()
        for word in words:
            if len(word) >= 4:  # Only check words with 4+ chars
                matches = get_close_matches(word, [c.lower() for c in KNOWN_CITIES], n=1, cutoff=0.7)
                if matches:
                    # Find the original city name
                    for city in KNOWN_CITIES:
                        if city.lower() == matches[0]:
                            return city
        return None

    def _wants_to_end(self, text: str) -> bool:
        """Check if user wants to end conversation."""
        t = text.lower()
        endings = ["bye", "goodbye", "that's all", "done", "end", "later", "no thanks", "exit", "quit"]
        return any(e in t for e in endings)

    def _wants_properties_now(self, text: str) -> bool:
        """Check if user wants to see properties."""
        t = text.lower()
        triggers = ["show", "display", "list", "see", "view", "get", "find", "search", "property", "properties"]
        return any(trigger in t for trigger in triggers)

    def _has_all_info(self) -> bool:
        """Check if we have all required info."""
        return bool(self.lead.get("name") and self.lead.get("phone") and self.lead.get("email"))

    def _generate_response(self, user_text: str) -> str:
        """Generate intelligent response using LLM."""
        # Build status
        status_parts = []
        if self.lead.get("name"):
            status_parts.append(f"Name: {self.lead['name']}")
        else:
            status_parts.append("Name: NOT YET COLLECTED - ask for it")

        if self.lead.get("phone"):
            status_parts.append(f"Phone: {self.lead['phone']}")
        else:
            status_parts.append("Phone: NOT YET COLLECTED - ask for it after name")

        if self.lead.get("email"):
            status_parts.append(f"Email: {self.lead['email']}")
        else:
            status_parts.append("Email: NOT YET COLLECTED - ask for it after phone")

        if self.lead.get("city"):
            status_parts.append(f"City interested: {self.lead['city']}")
        if self.lead.get("bhk"):
            status_parts.append(f"BHK preference: {self.lead['bhk']}")
        if self.lead.get("budget"):
            status_parts.append(f"Budget: {self.lead['budget']}")

        status = "\n".join(status_parts)

        # Build context
        context_lines = []
        for msg in self.history[-8:]:
            role = "User" if msg["role"] == "user" else "Priya"
            context_lines.append(f"{role}: {msg['content']}")
        context = "\n".join(context_lines) if context_lines else "Start of conversation"

        prompt = SYSTEM_PROMPT.format(status=status, context=context)

        try:
            response = self.llm.generate(prompt, user_text, self.history[-4:])
            return response.strip()
        except Exception as e:
            print(f"LLM error: {e}")
            return self._fallback_response()

    def _fallback_response(self) -> str:
        """Fallback when LLM fails."""
        if not self.lead.get("name"):
            return "Hi! I'm Priya from Raymond Realty. May I know your name?"
        elif not self.lead.get("phone"):
            return f"Nice to meet you, {self.lead['name']}! What's your phone number?"
        elif not self.lead.get("email"):
            return "And your email address please?"
        else:
            return "Would you like me to show you some properties?"

    def _farewell_with_properties(self) -> dict:
        """Show properties and end conversation."""
        self._try_save_lead()

        city = self.lead.get("city")
        bhk = self.lead.get("bhk")
        budget = self._parse_budget(self.lead.get("budget"))
        name = self.lead.get("name", "").split()[0] if self.lead.get("name") else ""

        print(f"Searching: city={city}, bhk={bhk}, budget={budget}")

        props = retrieve_properties(location=city, max_price=budget, bhk=bhk)

        if not props and city:
            print(f"No properties in {city}, showing all...")
            props = retrieve_properties(max_price=budget, bhk=bhk)

        if props:
            cards = format_property_cards(props, city, budget, bhk)
            if city:
                text = f"Here are {len(cards)} properties in {city} for you{', ' + name if name else ''}! Our team will call you shortly."
            else:
                text = f"Here are {len(cards)} great properties for you{', ' + name if name else ''}! Our team will call you shortly."

            self.history.append({"role": "assistant", "content": text})
            return {"text": text, "properties": cards, "conversation_ended": True}

        # Fallback
        all_props = retrieve_properties()
        if all_props:
            cards = format_property_cards(all_props[:5])
            text = f"Here are some excellent properties{' for you, ' + name if name else ''}!"
            return {"text": text, "properties": cards, "conversation_ended": True}

        return {"text": f"Thanks{', ' + name if name else ''}! Our team will contact you soon!", "conversation_ended": True}

    def _parse_budget(self, val):
        if not val:
            return None
        try:
            v = str(val).lower()
            if "cr" in v:
                return int(float(re.sub(r'[^\d.]', '', v.split('cr')[0])) * 10000000)
            if "la" in v:
                return int(float(re.sub(r'[^\d.]', '', v.split('la')[0])) * 100000)
        except:
            pass
        return None

    def _try_save_lead(self):
        """Save lead to Salesforce."""
        if self.lead_saved or not (self.lead.get("name") and self.lead.get("phone")):
            return

        try:
            from app.crm.salesforce_auth import get_access_token
            from app.crm.create_lead import create_salesforce_lead

            token = get_access_token()
            payload = {"wl": {
                "fullName": self.lead.get("name", ""),
                "emailAddress": self.lead.get("email", ""),
                "mobileNumber": self.lead.get("phone", ""),
                "city": self.lead.get("city", "Bangalore"),
                "budget": str(self.lead.get("budget", "")),
                "configuration": self.lead.get("bhk", ""),
                "source": "Website"
            }}
            create_salesforce_lead(payload, token["access_token"], token["instance_url"])
            self.lead_saved = True
            print(f"Lead saved: {self.lead.get('name')} - {self.lead.get('phone')}")
        except Exception as e:
            print(f"Lead save error: {e}")
