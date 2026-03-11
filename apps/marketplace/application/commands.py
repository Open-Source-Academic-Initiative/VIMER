from dataclasses import dataclass


@dataclass(frozen=True)
class PublishChallengeCommand:
    title: str
    description: str


@dataclass(frozen=True)
class SubmitApplicationCommand:
    proposal_text: str
