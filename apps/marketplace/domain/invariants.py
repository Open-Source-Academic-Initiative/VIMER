INV_05_ONLY_DEMAND_SIDE_CAN_PUBLISH_CHALLENGES = "INV-05"
INV_06_ONLY_SUPPLY_SIDE_CAN_SUBMIT_APPLICATIONS = "INV-06"
INV_07_ONE_APPLICATION_PER_CHALLENGE_AND_APPLICANT = "INV-07"
INV_11_CHALLENGE_MUST_BE_OPEN_FOR_APPLICATIONS = "INV-11"
INV_12_CHALLENGE_HAS_EXPLICIT_LIFECYCLE_STATE = "INV-12"
INV_13_APPLICATION_REQUIRES_ALL_COMPONENTS = "INV-13"
INV_14_SUBMITTED_APPLICATION_IS_IMMUTABLE = "INV-14"
INV_40_APPLICATION_HAS_EXPLICIT_LIFECYCLE_STATE = "INV-40"
INV_41_DRAFT_APPLICATIONS_EXIST_ONLY_WHILE_CHALLENGE_IS_OPEN = "INV-41"

INVARIANT_CATALOG = {
    INV_05_ONLY_DEMAND_SIDE_CAN_PUBLISH_CHALLENGES: (
        "Only demand-side organizations can publish challenges."
    ),
    INV_06_ONLY_SUPPLY_SIDE_CAN_SUBMIT_APPLICATIONS: (
        "Only supply-side organizations can submit applications."
    ),
    INV_07_ONE_APPLICATION_PER_CHALLENGE_AND_APPLICANT: (
        "An applicant can submit at most one application per challenge."
    ),
    INV_11_CHALLENGE_MUST_BE_OPEN_FOR_APPLICATIONS: (
        "A challenge only accepts applications while it is open for submission."
    ),
    INV_12_CHALLENGE_HAS_EXPLICIT_LIFECYCLE_STATE: (
        "A challenge has an explicit lifecycle state."
    ),
    INV_13_APPLICATION_REQUIRES_ALL_COMPONENTS: (
        "An application must include all required proposal components."
    ),
    INV_14_SUBMITTED_APPLICATION_IS_IMMUTABLE: (
        "A submitted application cannot be edited after submission."
    ),
    INV_40_APPLICATION_HAS_EXPLICIT_LIFECYCLE_STATE: (
        "An application has an explicit draft or submitted lifecycle state."
    ),
    INV_41_DRAFT_APPLICATIONS_EXIST_ONLY_WHILE_CHALLENGE_IS_OPEN: (
        "Draft applications can only be created or edited while the challenge is open."
    ),
}
