# VIMER Project Diagrams

This document illustrates the current implemented state of VIMER with:

- a functional flow diagram
- an architecture diagram

The diagrams are written in Mermaid so they can evolve together with the codebase.

## Functional Flow

```mermaid
flowchart TD
    A[Public visitor] --> B[Landing page /]
    B --> C[Signup /signup]
    B --> D[Login /login]

    C --> E[Representative + Organization created]
    D --> F{Organization market role}
    E --> F

    F -->|Solicitante / DEMAND_SIDE| G[Challenge list and challenge creation]
    F -->|Proveedor tecnologico / SUPPLY_SIDE| H[Challenge list and challenge detail]

    G --> I[Publish challenge]
    I --> J[Challenge status: PUBLISHED]
    J --> K[Define structured evaluation criteria]

    H --> L[Submit structured proposal]
    L --> M[Application persisted once per organization and challenge]

    K --> N[Publisher assigns evaluation team]
    M --> O[Challenge has proposals]
    N --> P[Start evaluation]
    O --> P
    P --> Q[Challenge status: UNDER_EVALUATION]

    Q --> R[Blind evaluation by designated evaluators]
    R --> S[One current assessment per proposal, criterion, evaluator]
    S --> T[Aggregated evaluation summaries and ranking]
    T --> U{Each criterion covered at least once?}

    U -->|No| R
    U -->|Yes| V[Blind adjudication by designated adjudicator]
    V --> W[Award decision + snapshot persisted]
    W --> X[Challenge status: AWARDED]

    P --> Y[ChallengeEvaluationStarted event]
    R --> Z[ApplicationEvaluationRecorded event]
    W --> AA[ChallengeAwarded event]

    Y --> AB[Timeline entries]
    Z --> AB
    AA --> AB

    Y --> AC[Applicant notifications]
    Z --> AC
    Z --> AD[Evaluation-team notifications]
    AA --> AC

    X --> AE[Applicant identity becomes visible in publisher-facing views]
    AC --> AF[Notifications inbox]
    AD --> AF
```

## Architecture Diagram

```mermaid
flowchart LR
    subgraph Client["Client / Browser"]
        UI[HTML templates]
    end

    subgraph Django["Django Web Layer"]
        URLS[config/urls.py + app urls]
        VIEWS[Views]
        FORMS[Forms]
        ADMIN[Django Admin]
    end

    subgraph Apps["Application Contexts"]
        subgraph Identity["apps/identity"]
            ID_APP[application services]
            ID_MODELS[User]
        end

        subgraph Corporate["apps/corporate"]
            CORP_MODELS[Organization + branding]
        end

        subgraph Marketplace["apps/marketplace"]
            MP_APP[publication and submission services]
            MP_DOMAIN[domain rules and invariants]
            MP_MODELS[Challenge + Application + ChallengeEvaluationCriterion]
        end

        subgraph Evaluation["apps/evaluation"]
            EV_APP[evaluation services and query models]
            EV_DOMAIN[domain rules, invariants, blind references, events, handlers]
            EV_MODELS[AwardDecision + ApplicationCriterionEvaluation + Timeline + RoleAssignment]
        end

        subgraph Notifications["apps/notifications"]
            NOTIF_APP[notification read-state service]
            NOTIF_DOMAIN[event consumers]
            NOTIF_MODELS[Notification]
        end
    end

    subgraph Infra["Infrastructure"]
        DB[(SQLite by default)]
        SETTINGS[config/settings.py]
        GUNICORN[Gunicorn in Dockerfile and docker-compose]
    end

    UI --> URLS
    URLS --> VIEWS
    VIEWS --> FORMS
    VIEWS --> ADMIN

    VIEWS --> ID_APP
    VIEWS --> MP_APP
    VIEWS --> EV_APP
    VIEWS --> NOTIF_APP

    ID_APP --> ID_MODELS
    ID_MODELS --> CORP_MODELS

    MP_APP --> MP_DOMAIN
    MP_APP --> MP_MODELS
    MP_MODELS --> CORP_MODELS

    EV_APP --> EV_DOMAIN
    EV_APP --> EV_MODELS
    EV_APP --> MP_MODELS
    EV_DOMAIN --> EV_MODELS
    EV_DOMAIN -. emits domain events .-> NOTIF_DOMAIN
    EV_DOMAIN -. persists timeline projections .-> EV_MODELS

    NOTIF_APP --> NOTIF_MODELS
    NOTIF_DOMAIN --> NOTIF_MODELS
    NOTIF_DOMAIN --> MP_MODELS
    NOTIF_DOMAIN --> EV_MODELS

    ID_MODELS --> DB
    CORP_MODELS --> DB
    MP_MODELS --> DB
    EV_MODELS --> DB
    NOTIF_MODELS --> DB

    SETTINGS --> VIEWS
    SETTINGS --> ID_APP
    SETTINGS --> MP_APP
    SETTINGS --> EV_APP
    SETTINGS --> NOTIF_APP
    GUNICORN --> URLS
```

## Notes

- `Marketplace` remains the physical Django app for both challenge and proposal concerns, but its internals are now separated explicitly across domain modules, application services, forms, views, and tests.
- `Evaluation` is the most event-driven context today: it emits the milestones consumed by challenge timeline projections and in-app notifications.
- The current scoring model supports multiple evaluators per criterion, with one current persisted assessment per `(proposal, criterion, evaluator)`.
- Blind evaluation is enforced in publisher-facing evaluation and adjudication flows until the challenge is awarded.
