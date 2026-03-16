class MarketplaceApplicationError(Exception):
    pass


class DuplicateChallengeApplicationError(MarketplaceApplicationError):
    pass


class ChallengeApplicationValidationError(MarketplaceApplicationError):
    def __init__(self, messages):
        self.messages = list(messages)
        super().__init__(" ".join(self.messages))
