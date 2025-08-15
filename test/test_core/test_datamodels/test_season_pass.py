import pytest

from core.datamodels.season_pass import Season_Pass


def test_season_pass():
    assert Season_Pass("Epic") == Season_Pass.EPIC

    with pytest.raises(Exception) as exc_info:
        Season_Pass("Invalid")

    assert "ValueError" in str(exc_info)
