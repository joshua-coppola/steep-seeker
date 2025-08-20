from core.datamodels.state import State
from core.datamodels.region import Region


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
