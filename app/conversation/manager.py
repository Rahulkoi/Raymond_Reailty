print("🔥 LOADING ConversationManager")

import json
from app.llm.openai_client import OpenAIClient
from app.rag.retriever import retrieve_properties
from app.response.response_builder import format_property_response, format_property_response_with_links, format_property_cards

MAX_HISTORY_TURNS = 10  # Keep last N turns to avoid token overflow


class ConversationManager:
    def __init__(self):
        self.llm = OpenAIClient()
        self.lead_data = {}
        self.lead_created = False
        self.history = []  # Conversation history: [{role, content}, ...]

    # ================= MAIN ENTRY ================= #

    def handle_user_input(self, user_text: str):
        raw = self.llm.generate(
            system_prompt=self._system_prompt(),
            user_text=user_text,
            history=self.history
        )

        data = self._safe_json(raw)
        intent = data.get("intent")
        args = data.get("arguments", {})
        response_text = data.get("response", "")

        # 🧠 Always extract lead info silently
        self._extract_lead_entities(args)

        # Backup check for end conversation - if user says bye/thanks/end
        end_phrases = ["bye", "goodbye", "thanks", "thank you", "that's all", "thats all", "end conversation", "i'm done", "im done", "see you", "talk later"]
        user_lower = user_text.lower().strip()
        if any(phrase in user_lower for phrase in end_phrases):
            intent = "end_conversation"
            print(f"🔚 End conversation detected from user text: {user_text}")

        # Check if user is explicitly asking to see properties NOW
        show_now_phrases = ["show me", "show property", "show properties", "see property", "see properties",
                           "right now", "right here", "display", "list properties", "what properties"]
        user_wants_properties_now = any(phrase in user_text.lower() for phrase in show_now_phrases)

        # Determine final response based on intent
        if intent == "end_conversation":
            result = self._handle_end_conversation()
        elif intent == "show_properties" or user_wants_properties_now:
            # User explicitly asked to see properties - show them immediately
            result = self._handle_show_properties_now()
        elif intent == "property_search":
            result = self._handle_property_search()
        elif intent == "create_lead":
            result = self._handle_lead_flow()
        else:
            result = {"text": response_text}

        # Auto-save lead to Salesforce when we have enough info (MUST be before _maybe_add_properties)
        self._auto_save_lead()

        # Always try to add properties if we have any search criteria (and lead captured)
        self._maybe_add_properties(result)

        # Add this turn to conversation history
        self._add_to_history(user_text, result["text"])

        return result

    def _auto_save_lead(self):
        """Automatically save lead to Salesforce when we have name + phone."""
        if self.lead_created:
            return  # Already saved

        # Need at least name and phone
        has_name = self.lead_data.get("fullName")
        has_phone = self.lead_data.get("mobileNumber")

        if has_name and has_phone:
            self._save_to_salesforce()

    def _save_to_salesforce(self):
        """Save current lead data to Salesforce."""
        if self.lead_created:
            return  # Already saved

        from app.crm.salesforce_auth import get_access_token
        from app.crm.create_lead import create_salesforce_lead

        try:
            token = get_access_token()

            payload = {
                "wl": {
                    "fullName": self.lead_data.get("fullName", ""),
                    "emailAddress": self.lead_data.get("emailAddress", ""),
                    "mobileNumber": self.lead_data.get("mobileNumber", ""),
                    "city": self.lead_data.get("city", "Bangalore"),
                    "budget": str(self.lead_data.get("budget", "")),
                    "configuration": self.lead_data.get("configuration", ""),
                    "source": "AI_VOICE_BOT"
                }
            }

            create_salesforce_lead(
                payload,
                token["access_token"],
                token["instance_url"]
            )

            self.lead_created = True
            print(f"Lead saved to Salesforce: {self.lead_data.get('fullName')} - {self.lead_data.get('mobileNumber')}")

        except Exception as e:
            print(f"Error saving lead to Salesforce: {e}")

    def _handle_end_conversation(self):
        """Handle user wanting to end the conversation - save lead and show properties."""
        print(f"🔚 Handling end conversation. Lead data: {self.lead_data}")

        # Save lead if we have any data
        self._save_to_salesforce()

        # Get properties based on criteria
        location = self.lead_data.get("city")
        max_price = self._parse_budget(self.lead_data.get("budget"))
        bhk = self.lead_data.get("configuration")

        print(f"🏠 Searching properties: location={location}, max_price={max_price}, bhk={bhk}")

        properties = retrieve_properties(
            location=location,
            max_price=max_price,
            bhk=bhk
        )

        print(f"🏠 Found {len(properties)} properties")

        # Build farewell with summary
        name = self.lead_data.get("fullName", "").split()[0] if self.lead_data.get("fullName") else ""

        # Only show properties if we found matching ones - don't show random
        if properties:
            property_cards = format_property_cards(
                properties,
                location=location,
                max_price=max_price,
                bhk=bhk
            )
            print(f"🏠 Returning {len(property_cards)} property cards")
            farewell = f"Great chatting{', ' + name if name else ''}! Here are {len(property_cards)} properties matching your needs. Our team will call you soon!"

            return {
                "text": farewell,
                "properties": property_cards,
                "conversation_ended": True
            }
        else:
            # No matching properties - custom message
            print(f"🏠 No matching properties found")
            farewell = f"Thanks{' ' + name if name else ''}! We don't have exact matches for your criteria right now, but our team will reach out with personalized options soon!"

            return {
                "text": farewell,
                "conversation_ended": True
            }

    def _maybe_add_properties(self, result):
        """Add property suggestions only after we have lead info collected."""
        # Don't add if conversation is ending (already handled)
        if result.get("conversation_ended"):
            return

        # Don't add if properties already in result
        if result.get("properties"):
            return

        # Only show properties if we have captured the lead (name + phone)
        # This ensures we have a conversation first before showing results
        if not self.lead_created:
            return  # Don't show properties until lead is captured

        # If we have city or budget, show properties
        if self.lead_data.get("city") or self.lead_data.get("budget") or self.lead_data.get("configuration"):
            location = self.lead_data.get("city")
            max_price = self._parse_budget(self.lead_data.get("budget"))
            bhk = self.lead_data.get("configuration")

            properties = retrieve_properties(
                location=location,
                max_price=max_price,
                bhk=bhk
            )

            # Only show properties if we found matching ones - don't show random
            if properties:
                result["properties"] = format_property_cards(
                    properties,
                    location=location,
                    max_price=max_price,
                    bhk=bhk
                )
            else:
                print(f"🏠 No matching properties for: location={location}, budget={max_price}, bhk={bhk}")

    def _add_to_history(self, user_text: str, assistant_text: str):
        """Add a conversation turn to history, maintaining max size."""
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})

        # Trim to last N turns (each turn = 2 messages)
        max_messages = MAX_HISTORY_TURNS * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]

    # ================= PROPERTY ================= #

    def _handle_show_properties_now(self):
        """Show properties immediately when user explicitly asks - don't wait for lead capture."""
        location = self.lead_data.get("city")
        max_price = self._parse_budget(self.lead_data.get("budget"))
        bhk = self.lead_data.get("configuration")

        print(f"🏠 User requested properties NOW: location={location}, max_price={max_price}, bhk={bhk}")

        properties = retrieve_properties(
            location=location,
            max_price=max_price,
            bhk=bhk
        )

        # Build response based on what we know
        name = self.lead_data.get("fullName", "").split()[0] if self.lead_data.get("fullName") else ""

        # Only show properties if we found matching ones - don't show random
        if properties:
            property_cards = format_property_cards(
                properties,
                location=location,
                max_price=max_price,
                bhk=bhk
            )
            print(f"🏠 Showing {len(property_cards)} properties immediately")

            text = f"Here are {len(property_cards)} properties"
            if location:
                text += f" in {location}"
            text += "!"
            if not self.lead_data.get("mobileNumber"):
                text += " Share your number for a site visit."

            return {
                "text": text,
                "properties": property_cards
            }
        else:
            # No matching properties - show custom message
            print(f"🏠 No properties found for criteria")
            if location:
                text = f"Sorry, we don't have properties in {location} matching your criteria right now."
            else:
                text = "Sorry, we don't have properties matching your criteria right now."
            text += " Let me know a different location or budget and I'll help you find options!"

            return {"text": text}

    def _handle_property_search(self):
        location = self.lead_data.get("city")
        max_price = self._parse_budget(self.lead_data.get("budget"))
        bhk = self.lead_data.get("configuration")

        properties = retrieve_properties(
            location=location,
            max_price=max_price,
            bhk=bhk
        )

        text = format_property_response(
            properties,
            location=location,
            max_price=max_price,
            bhk=bhk
        )

        return {"text": text}

    # ================= LEAD FLOW ================= #

    def _handle_lead_flow(self):
        """Handle lead creation flow - collect info and submit."""
        missing = self._missing_lead_fields()

        # If we have the critical fields, submit even if some optional ones are missing
        critical_fields = ["fullName", "mobileNumber"]
        critical_missing = [f for f in critical_fields if f not in self.lead_data]

        if critical_missing:
            # Ask for critical info first
            return {"text": self._ask_for(critical_missing[0])}

        if missing and len(missing) <= 2:
            # We have most info, ask for remaining
            return {"text": self._ask_for(missing[0])}

        if not self.lead_created:
            return self._submit_lead()

        return {"text": "I've already got your details saved! How else can I help you today?"}

    def _submit_lead(self):
        """Submit lead to Salesforce and show matching properties."""
        # Save lead using shared method
        self._save_to_salesforce()

        # Show properties matching their criteria
        location = self.lead_data.get("city")
        max_price = self._parse_budget(self.lead_data.get("budget"))
        bhk = self.lead_data.get("configuration")

        properties = retrieve_properties(
            location=location,
            max_price=max_price,
            bhk=bhk
        )

        name = self.lead_data.get("fullName", "").split()[0] if self.lead_data.get("fullName") else ""

        # Only show properties if we found matching ones - don't show random
        if properties:
            property_cards = format_property_cards(
                properties,
                location=location,
                max_price=max_price,
                bhk=bhk
            )
            return {
                "text": f"Perfect{', ' + name if name else ''}! Got your details. Here are some great matches!",
                "properties": property_cards
            }
        else:
            # No matching properties - show custom message, no random properties
            print(f"🏠 No properties found for: location={location}, budget={max_price}, bhk={bhk}")
            return {
                "text": f"Thanks{', ' + name if name else ''}! Got your details. We don't have exact matches for your criteria right now, but our team will reach out with personalized options soon!"
            }

    # ================= HELPERS ================= #

    def _extract_lead_entities(self, args):
        mapping = {
            "fullName": ["name"],
            "emailAddress": ["email"],
            "mobileNumber": ["phone", "mobile"],
            "city": ["city", "location"],
            "budget": ["budget", "price"],
            "configuration": ["bhk", "configuration"]
        }

        for field, keys in mapping.items():
            for k in keys:
                if k in args and args[k]:
                    self.lead_data[field] = args[k]

    def _missing_lead_fields(self):
        required = [
            "fullName",
            "emailAddress",
            "mobileNumber",
            "city",
            "budget",
            "configuration"
        ]
        return [f for f in required if f not in self.lead_data]

    def _ask_for(self, field):
        """Get a conversational question for missing field."""
        questions = {
            "fullName": "By the way, I didn't catch your name. What should I call you?",
            "emailAddress": "I'd love to send you some property brochures. What's your email?",
            "mobileNumber": "And what's the best number to reach you on?",
            "city": "Which part of Bangalore are you looking at? Any preferred areas?",
            "budget": "What's your budget range? Just a ballpark is fine!",
            "configuration": "Are you looking for a 2 BHK, 3 BHK, or something bigger?"
        }
        return questions.get(field, f"Could you tell me your {field}?")

    def _parse_budget(self, value):
        """Parse budget string to integer value in rupees."""
        if not value:
            return None

        try:
            value_str = str(value).lower().strip()

            # Handle crore values
            if "cr" in value_str or "crore" in value_str:
                num = float(value_str.replace("cr", "").replace("crore", "").replace("₹", "").replace(",", "").strip())
                return int(num * 10000000)  # 1 crore = 10,000,000

            # Handle lakh values
            if "lakh" in value_str or "lac" in value_str:
                num = float(value_str.replace("lakh", "").replace("lac", "").replace("₹", "").replace(",", "").strip())
                return int(num * 100000)  # 1 lakh = 100,000

            # Handle plain numbers (assume lakhs if small, crores if has many zeros)
            num = float(value_str.replace("₹", "").replace(",", "").strip())
            if num < 1000:
                return int(num * 100000)  # Assume lakhs
            return int(num)

        except:
            return None

    def _safe_json(self, text):
        try:
            return json.loads(text)
        except:
            return {"response": text}

    def _system_prompt(self):
        # Build context about what we already know
        collected = []
        missing = []

        if self.lead_data.get("fullName"):
            collected.append(f"Name: {self.lead_data['fullName']}")
        else:
            missing.append("name")

        if self.lead_data.get("mobileNumber"):
            collected.append(f"Phone: {self.lead_data['mobileNumber']}")
        else:
            missing.append("phone")

        if self.lead_data.get("city"):
            collected.append(f"Location preference: {self.lead_data['city']}")
        else:
            missing.append("location/area preference")

        if self.lead_data.get("budget"):
            collected.append(f"Budget: {self.lead_data['budget']}")
        else:
            missing.append("budget")

        if self.lead_data.get("configuration"):
            collected.append(f"BHK: {self.lead_data['configuration']}")
        else:
            missing.append("BHK preference")

        if self.lead_data.get("emailAddress"):
            collected.append(f"Email: {self.lead_data['emailAddress']}")

        collected_str = ", ".join(collected) if collected else "Nothing yet"
        missing_str = ", ".join(missing) if missing else "All info collected!"

        return f"""You are Priya, a warm and friendly real estate consultant at Raymond Realty, Bangalore. You're having a natural phone conversation with a potential home buyer.

PERSONALITY:
- Talk like a helpful friend, not a salesperson or bot
- Be warm but BRIEF - this is voice chat, not text
- CRITICAL: Keep responses to 1-2 SHORT sentences (under 25 words)
- Use their name once you know it
- No filler phrases like "That's great!" unless truly needed

CONVERSATION FLOW (follow this naturally):
1. First, understand what they're looking for (area, budget, BHK)
2. Show genuine interest and share relevant info about areas/properties
3. If user asks to SEE PROPERTIES → show them immediately (intent: show_properties)
4. Collect name and phone naturally when the moment feels right, but NEVER block property viewing

CURRENT CONTEXT:
- Already collected: {collected_str}
- Still need: {missing_str}
- Lead saved: {"Yes" if self.lead_created else "No"}

CRITICAL RULE - SHOW PROPERTIES WHEN ASKED:
- If user says "show me properties", "show me now", "can you show me", "display properties", "see properties", "list properties", "what properties do you have" → intent: "show_properties"
- NEVER say "I'll send it to your phone" when user asks to see properties RIGHT NOW
- ALWAYS respect user's request to see properties immediately
- Properties will be displayed as cards - just say something like "Here are some great options!"

WHAT TO DO NEXT:
- If user asks to SEE/SHOW properties: intent = "show_properties", respond positively
- If missing location/budget/BHK: Ask about their preferences naturally
- If have preferences and user hasn't asked to see properties yet: You can ask for name/phone, but don't be pushy
- If user says goodbye/bye/end/thanks/that's all/I'm done → intent: "end_conversation"
- If have name AND phone AND user shared new info: intent = "create_lead"

ENDING CONVERSATION:
- When user wants to end (says "bye", "thanks", "that's all", "I'm done", "end conversation", "goodbye", etc.)
- Set intent to "end_conversation"
- Your response should be a brief, warm farewell (the system will handle showing properties)

EXTRACTION - Always extract any info they share:
- "I'm Rahul" or "My name is Rahul" → name: "Rahul"
- "9876543210" or "my number is..." → phone: that number
- "Whitefield", "Electronic City", "near metro", "Thane" → city: that location
- "1 crore", "80 lakhs", "around 1.5 cr" → budget: that amount
- "2BHK", "3 bedroom", "2 bhk" → bhk: that config

IMPORTANT RULES:
- BREVITY IS CRITICAL: Max 25 words per response. Voice needs short, punchy replies
- NEVER refuse to show properties when user asks
- NEVER say "I'll send to your phone" when user wants to see NOW
- NEVER ask multiple questions in one response
- ONE short sentence is often enough
- Sound natural, not scripted

Output ONLY valid JSON:
{{
  "intent": "show_properties | property_search | create_lead | end_conversation | general",
  "arguments": {{
    "name": "extracted name or null",
    "email": "extracted email or null",
    "phone": "extracted phone or null",
    "city": "extracted city/location or null",
    "budget": "extracted budget or null",
    "bhk": "extracted BHK preference or null"
  }},
  "response": "your short, natural response"
}}"""
