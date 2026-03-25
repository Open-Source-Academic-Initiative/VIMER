INV_18_CHALLENGE_REQUIRES_EVALUATION_TEAM_BEFORE_EVALUATION = "INV-18"
INV_19_EVALUATION_ROLES_ARE_LIMITED_TO_PUBLISHER_ORGANIZATION_MEMBERS = "INV-19"
INV_20_ONLY_PUBLISHER_ORGANIZATION_CAN_GOVERN_EVALUATION = "INV-20"
INV_21_ONLY_DESIGNATED_EVALUATORS_CAN_SCORE_PROPOSALS = "INV-21"
INV_22_ONLY_DESIGNATED_ADJUDICATOR_CAN_ADJUDICATE = "INV-22"
INV_23_CHALLENGE_CAN_HAVE_AT_MOST_ONE_DESIGNATED_ADJUDICATOR = "INV-23"
INV_24_AWARD_DECISION_PRESERVES_EVALUATION_SNAPSHOT = "INV-24"
INV_25_EVALUATION_MILESTONES_REMAIN_AUDITABLE = "INV-25"
INV_26_APPLICANT_IDENTITY_REMAINS_BLIND_UNTIL_AWARD = "INV-26"
INV_27_ONE_CURRENT_ASSESSMENT_PER_EVALUATOR_AND_CRITERION = "INV-27"
INV_28_AWARD_REQUIRES_CRITERION_COVERAGE = "INV-28"

INVARIANT_CATALOG = {
    INV_18_CHALLENGE_REQUIRES_EVALUATION_TEAM_BEFORE_EVALUATION: (
        "A challenge requires at least one designated evaluator and one designated adjudicator before it can enter evaluation."
    ),
    INV_19_EVALUATION_ROLES_ARE_LIMITED_TO_PUBLISHER_ORGANIZATION_MEMBERS: (
        "Evaluation roles can only be assigned to members of the publisher organization."
    ),
    INV_20_ONLY_PUBLISHER_ORGANIZATION_CAN_GOVERN_EVALUATION: (
        "Only the publisher organization can manage and execute evaluation operations for a challenge."
    ),
    INV_21_ONLY_DESIGNATED_EVALUATORS_CAN_SCORE_PROPOSALS: (
        "Only designated evaluators can register criterion-by-criterion proposal assessments."
    ),
    INV_22_ONLY_DESIGNATED_ADJUDICATOR_CAN_ADJUDICATE: (
        "Only the designated adjudicator can register the final award decision."
    ),
    INV_23_CHALLENGE_CAN_HAVE_AT_MOST_ONE_DESIGNATED_ADJUDICATOR: (
        "A challenge can have at most one designated adjudicator."
    ),
    INV_24_AWARD_DECISION_PRESERVES_EVALUATION_SNAPSHOT: (
        "An award decision preserves the winning proposal's evaluation context for traceability."
    ),
    INV_25_EVALUATION_MILESTONES_REMAIN_AUDITABLE: (
        "Major evaluation milestones remain auditable through emitted events and persisted projections."
    ),
    INV_26_APPLICANT_IDENTITY_REMAINS_BLIND_UNTIL_AWARD: (
        "Applicant identity remains hidden in evaluation and adjudication flows until award."
    ),
    INV_27_ONE_CURRENT_ASSESSMENT_PER_EVALUATOR_AND_CRITERION: (
        "Each evaluator can have at most one current persisted assessment per proposal and criterion."
    ),
    INV_28_AWARD_REQUIRES_CRITERION_COVERAGE: (
        "A proposal can only be awarded after every challenge criterion has at least one registered assessment."
    ),
}
