import enum

# FIXME -- To check again at a future date
class CatalystState(str, enum.Enum):
    """The state machine's vocabulary for a single catalyst.

    A catalyst is not a boolean — news contradicts itself ("contract confirmed"
    Tuesday, "contract delayed" Thursday) — so each one carries a state:

        unconfirmed ──▶ rumored ──▶ confirmed
             ▲             │            │
             └─────────────┴────────────┴──▶ invalidated
                                                 │ (credible re-confirmation)
                                                 └──▶ confirmed

    str-valued so it serializes straight to JSON / the DB `state` column.
    `pipeline.catalysts` owns the transition *rules*; this is only the vocabulary,
    shared so the backend never hardcodes these strings.
    """
    UNCONFIRMED = "unconfirmed"
    RUMORED = "rumored"
    CONFIRMED = "confirmed"
    INVALIDATED = "invalidated"


class CatalystProposal(str, enum.Enum):
    """What a Pass-2 verdict proposes doing to a catalyst.

    NOT the same vocabulary as `CatalystState`: `no_change` is not a state, and
    `unconfirmed` cannot be proposed. A proposal is only a request — whether it
    actually moves the catalyst is decided by the rules in `pipeline.catalysts`
    (a `confirmed` proposal from a speculative source is capped at `rumored`).
    """
    NO_CHANGE = "no_change"
    RUMORED = "rumored"
    CONFIRMED = "confirmed"
    INVALIDATED = "invalidated"
