class LeadState:
    def __init__(self):
        self.data = {
            "full_name": None,
            "mobile_number": None,
            "email": None,
            "city": None
        }
        self.awaiting_confirmation = False
        self.completed = False

    def update(self, extracted: dict):
        for k, v in extracted.items():
            if v and not self.data.get(k):
                self.data[k] = v

    def missing_fields(self):
        return [k for k, v in self.data.items() if not v]

    def is_complete(self):
        return len(self.missing_fields()) == 0
