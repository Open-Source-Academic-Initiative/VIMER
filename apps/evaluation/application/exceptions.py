class EvaluationApplicationError(Exception):
    pass


class ChallengeEvaluationValidationError(EvaluationApplicationError):
    def __init__(self, messages, *, invariant_ids=None):
        self.messages = list(messages)
        self.invariant_ids = tuple(dict.fromkeys(invariant_ids or ()))
        super().__init__(" ".join(self.messages))
