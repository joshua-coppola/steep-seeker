from support.states import State, Region


def test_state():
    name_string = "Vermont"
    abbreviation_string = "NM"
    invalid_name_string = "Not a State"
    invalid_abbreviation_string = "BY"

    # these should all succeed
    assert State.from_name(name_string) == State.VERMONT
    assert State[name_string.upper()] == State.VERMONT
    assert State(abbreviation_string) == State.NEW_MEXICO

    # these should fail
    try:
        State.from_name(invalid_name_string)
        assert False
    except ValueError:
        assert True

    try:
        State(invalid_abbreviation_string)
        assert False
    except ValueError:
        assert True


def test_region():
    state = State.VIRGINIA
    state_string = "Virginia"

    assert Region.get_region(state) == Region.SOUTHEAST

    # should fail
    try:
        Region.get_region(state_string)
        assert False
    except ValueError:
        assert True
