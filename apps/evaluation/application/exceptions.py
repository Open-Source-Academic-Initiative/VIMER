class EvaluationApplicationError(Exception):
    pass


class ChallengeEvaluationValidationError(EvaluationApplicationError):
    def __init__(self, messages):
        self.messages = list(messages)
        super().__init__(" ".join(self.messages))
