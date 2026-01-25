class ConversationManager:
    def __init__(self):
        self.llm = OpenAIClient()
        self.lead_state = LeadState()
        self.collecting_lead = False   # ✅ REQUIRED
        self.lead_data = {}            # ✅ REQUIRED
