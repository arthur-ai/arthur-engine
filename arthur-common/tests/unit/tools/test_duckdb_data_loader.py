from arthur_common.tools.duckdb_data_loader import escape_identifier, escape_str_literal


def test_escape_identifier():
    assert escape_identifier('foo"bar') == '"foo""bar"'


def test_escape_str_literal():
    assert escape_str_literal("foo'bar") == "'foo''bar'"
