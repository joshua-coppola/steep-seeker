from core.support.blacklist import add_to_blacklist, is_blacklisted


def test_add_to_blacklist_marks_item_blacklisted(mountain_factory, db_path):
    mountain_factory(mountain_id="1").to_db(db_path)

    assert is_blacklisted("1", "w1000", db_path) is False

    add_to_blacklist("1", "w1000", db_path)

    assert is_blacklisted("1", "w1000", db_path) is True


def test_is_blacklisted_false_for_unknown_item(mountain_factory, db_path):
    mountain_factory(mountain_id="1").to_db(db_path)

    assert is_blacklisted("1", "nonexistent", db_path) is False


def test_add_to_blacklist_is_idempotent(mountain_factory, db_path):
    mountain_factory(mountain_id="1").to_db(db_path)

    add_to_blacklist("1", "w1000", db_path)
    add_to_blacklist("1", "w1000", db_path)

    assert is_blacklisted("1", "w1000", db_path) is True
