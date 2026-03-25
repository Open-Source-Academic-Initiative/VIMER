class EvaluationDomainError(Exception):
    def __init__(self, message: str, *, invariant_id: str | None = None):
        self.messages = [message]
        self.invariant_id = invariant_id
        super().__init__(message)


class EvaluationDomainRuleViolation(EvaluationDomainError):
    pass
