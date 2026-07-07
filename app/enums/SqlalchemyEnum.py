from enum import StrEnum
from typing import Literal


class ModelName(StrEnum):
    ALERT = "Alert"
    CATALYST = "Catalyst"
    CATALYST_PROPOSAL = "CatalystProposal"
    EVALUATION = "Evaluation"
    OUTCOME = "Outcome"
    QUANT_CONDITION = "QuantCondition"
    QUANT_PROPOSAL = "QuantProposal"
    STOCK = "Stock"
    THESES = "Theses"
    THESES_PROPOSAL = "ThesesProposal"
    USER = "User"


class RelationshipCascade(StrEnum):
    DELETE_ORPHAN = "all, delete-orphan"


LAZY_SELECTIN: Literal["selectin"] = "selectin"
LAZY_JOINED: Literal["joined"] = "joined"
LAZY_RAISE: Literal["raise"] = "raise"
