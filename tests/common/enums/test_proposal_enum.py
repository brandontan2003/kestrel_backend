import pytest

from common.enums.ProposalEnum import ProposalStatusEnum, ProposalTypeEnum


@pytest.mark.parametrize("proposal_enum_class, expected_values",
                         [(ProposalStatusEnum, {"PENDING", "APPROVED", "REJECTED", "SUPERSEDED"}),
                          (ProposalTypeEnum, {"ADD", "REMOVE", "UPDATE"})])
def test_enum_members(proposal_enum_class, expected_values):
    actual_values = {member for member in proposal_enum_class}
    assert actual_values == expected_values


@pytest.mark.parametrize("proposal_enum_class, expected_values",
                         [(ProposalStatusEnum, 4), (ProposalTypeEnum, 3)])
def test_enum_length(proposal_enum_class, expected_values):
    actual_values = {member.value for member in proposal_enum_class}
    assert len(actual_values) == expected_values


@pytest.mark.parametrize("proposal_enum_class", [ProposalStatusEnum, ProposalTypeEnum])
def test_enum_invalid_value_raises_error(proposal_enum_class):
    with pytest.raises(ValueError):
        proposal_enum_class("invalid")
