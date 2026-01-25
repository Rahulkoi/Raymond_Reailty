class SalesforceAuthError(Exception):
    """Raised when Salesforce OAuth fails"""
    pass


class SalesforceLeadError(Exception):
    """Raised when Lead creation fails"""
    pass
