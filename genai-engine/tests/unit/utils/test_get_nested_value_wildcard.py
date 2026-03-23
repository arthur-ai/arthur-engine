import pytest

from utils.trace import get_nested_value_wildcard


@pytest.mark.unit_tests
class TestGetNestedValueWildcard:
    def test_single_wildcard_on_list(self):
        obj = {"results": [{"name": "John"}, {"name": "Jane"}]}
        assert get_nested_value_wildcard(obj, "results.*.name") == ["John", "Jane"]

    def test_single_wildcard_on_dict(self):
        obj = {"metrics": {"accuracy": 0.9, "recall": 0.8}}
        result = get_nested_value_wildcard(obj, "metrics.*")
        assert sorted(result) == [0.8, 0.9]

    def test_nested_wildcards(self):
        obj = {
            "groups": [
                {"items": [{"val": 1}, {"val": 2}]},
                {"items": [{"val": 3}]},
            ],
        }
        assert get_nested_value_wildcard(obj, "groups.*.items.*.val") == [1, 2, 3]

    def test_wildcard_on_empty_list(self):
        obj = {"results": []}
        assert get_nested_value_wildcard(obj, "results.*.name") is None

    def test_wildcard_on_missing_path(self):
        obj = {"a": {"b": 1}}
        assert get_nested_value_wildcard(obj, "a.*.c") is None

    def test_wildcard_with_default(self):
        obj = {"results": []}
        assert get_nested_value_wildcard(obj, "results.*.name", default=[]) == []

    def test_no_wildcard_delegates_to_get_nested_value(self):
        obj = {"a": {"b": {"c": 42}}}
        assert get_nested_value_wildcard(obj, "a.b.c") == 42

    def test_wildcard_mixed_with_index(self):
        obj = {
            "data": [
                {"tags": ["x", "y"]},
                {"tags": ["z"]},
            ],
        }
        assert get_nested_value_wildcard(obj, "data.*.tags.0") == ["x", "z"]

    def test_wildcard_on_non_dict_root(self):
        assert get_nested_value_wildcard(None, "a.*.b") is None
        assert get_nested_value_wildcard("string", "a.*.b") is None

    def test_wildcard_on_primitive_values(self):
        obj = {"items": [1, 2, 3]}
        assert get_nested_value_wildcard(obj, "items.*") == [1, 2, 3]

    def test_wildcard_skips_none_values(self):
        obj = {"items": [{"a": 1}, {"a": None}, {"a": 3}]}
        assert get_nested_value_wildcard(obj, "items.*.a") == [1, 3]

    def test_wildcard_with_missing_key_in_some_items(self):
        obj = {"items": [{"a": 1}, {"b": 2}, {"a": 3}]}
        assert get_nested_value_wildcard(obj, "items.*.a") == [1, 3]

    def test_deeply_nested_path_with_wildcard(self):
        obj = {
            "attributes": {
                "output": {
                    "value": {
                        "results": [
                            {"id": 1, "name": "John"},
                            {"id": 2, "name": "Jane"},
                        ],
                    },
                },
            },
        }
        assert get_nested_value_wildcard(
            obj, "attributes.output.value.results.*.name"
        ) == ["John", "Jane"]

    def test_wildcard_on_scalar_returns_empty(self):
        obj = {"a": "not_a_list"}
        assert get_nested_value_wildcard(obj, "a.*.b") is None

    def test_wildcard_extracts_objects(self):
        obj = {"items": [{"nested": {"x": 1}}, {"nested": {"x": 2}}]}
        result = get_nested_value_wildcard(obj, "items.*.nested")
        assert result == [{"x": 1}, {"x": 2}]

    def test_wildcard_extracts_lists(self):
        obj = {"items": [{"tags": ["a", "b"]}, {"tags": ["c"]}]}
        result = get_nested_value_wildcard(obj, "items.*.tags")
        assert result == [["a", "b"], ["c"]]
