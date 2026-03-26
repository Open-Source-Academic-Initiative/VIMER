class MarketplaceDomainError(Exception):
    def __init__(self, message: str, *, invariant_id: str | None = None):
        self.messages = [message]
        self.invariant_id = invariant_id
        super().__init__(message)


class ChallengePublicationNotAllowed(MarketplaceDomainError):
    pass


class ChallengeApplicationNotAllowed(MarketplaceDomainError):
    pass


class DuplicateChallengeApplication(MarketplaceDomainError):
    pass


class ChallengeNotOpenForApplications(MarketplaceDomainError):
    pass


class IncompleteChallengeApplication(MarketplaceDomainError):
    pass


class SubmittedApplicationImmutable(MarketplaceDomainError):
    pass


class ExistingSubmittedApplication(MarketplaceDomainError):
    pass
