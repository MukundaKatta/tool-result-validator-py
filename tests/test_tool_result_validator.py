"""Tests for tool-result-validator-py."""

import pytest
from tool_result_validator import (
    ToolResultValidator,
    ValidationError,
    ValidationResult,
    __version__,
)


def test_version_exposed():
    assert isinstance(__version__, str)
    assert __version__


def test_empty_validator_passes():
    v = ToolResultValidator()
    assert v.check("anything") == "anything"


def test_run_returns_result():
    v = ToolResultValidator()
    result = v.run("hello")
    assert isinstance(result, ValidationResult)
    assert result.valid is True
    assert result.ok is True
    assert result.errors == []


def test_require_type_passes():
    v = ToolResultValidator()
    v.require_type(dict)
    v.check({"x": 1})


def test_require_type_fails():
    v = ToolResultValidator()
    v.require_type(dict)
    with pytest.raises(ValidationError) as exc_info:
        v.check("not a dict")
    assert "dict" in str(exc_info.value)
    assert exc_info.value.rule == "type"


def test_require_type_multiple_types():
    v = ToolResultValidator()
    v.require_type(dict, list)
    v.check({"x": 1})
    v.check([1, 2, 3])
    with pytest.raises(ValidationError):
        v.check("string")


def test_require_keys_passes():
    v = ToolResultValidator()
    v.require_keys(["status", "data"])
    v.check({"status": "ok", "data": []})


def test_require_keys_fails():
    v = ToolResultValidator()
    v.require_keys(["status", "data"])
    with pytest.raises(ValidationError) as exc_info:
        v.check({"status": "ok"})
    assert "data" in str(exc_info.value)


def test_require_keys_non_dict_fails():
    v = ToolResultValidator()
    v.require_keys(["x"])
    with pytest.raises(ValidationError):
        v.check("not a dict")


def test_require_value_allowed_passes():
    v = ToolResultValidator()
    v.require_value("status", allowed=["ok", "error"])
    v.check({"status": "ok"})


def test_require_value_allowed_fails():
    v = ToolResultValidator()
    v.require_value("status", allowed=["ok", "error"])
    with pytest.raises(ValidationError) as exc_info:
        v.check({"status": "unknown"})
    assert "unknown" in str(exc_info.value)


def test_require_value_disallowed_passes():
    v = ToolResultValidator()
    v.require_value("status", disallowed=["fail", "error"])
    v.check({"status": "ok"})


def test_require_value_disallowed_fails():
    v = ToolResultValidator()
    v.require_value("status", disallowed=["fail"])
    with pytest.raises(ValidationError):
        v.check({"status": "fail"})


def test_require_value_missing_key_fails():
    v = ToolResultValidator()
    v.require_value("status", allowed=["ok"])
    with pytest.raises(ValidationError) as exc_info:
        v.check({"other": "x"})
    assert "status" in str(exc_info.value)


def test_require_not_empty_string():
    v = ToolResultValidator()
    v.require_not_empty()
    v.check("hello")
    with pytest.raises(ValidationError):
        v.check("")


def test_require_not_empty_list():
    v = ToolResultValidator()
    v.require_not_empty()
    v.check([1, 2])
    with pytest.raises(ValidationError):
        v.check([])


def test_require_not_empty_none():
    v = ToolResultValidator()
    v.require_not_empty()
    with pytest.raises(ValidationError):
        v.check(None)


def test_require_not_empty_tuple():
    v = ToolResultValidator()
    v.require_not_empty()
    v.check((1, 2))
    with pytest.raises(ValidationError):
        v.check(())


def test_require_not_empty_set():
    v = ToolResultValidator()
    v.require_not_empty()
    v.check({1, 2})
    with pytest.raises(ValidationError):
        v.check(set())


def test_require_length_passes():
    v = ToolResultValidator()
    v.require_length(min_len=2, max_len=5)
    v.check("abc")
    v.check([1, 2, 3])


def test_require_length_min_fails():
    v = ToolResultValidator()
    v.require_length(min_len=3)
    with pytest.raises(ValidationError):
        v.check("ab")


def test_require_length_max_fails():
    v = ToolResultValidator()
    v.require_length(max_len=3)
    with pytest.raises(ValidationError):
        v.check("toolong")


def test_run_collects_errors():
    v = ToolResultValidator()
    v.require_type(dict)
    v.require_keys(["x", "y"])
    result = v.run("not a dict")
    assert result.valid is False
    assert len(result.errors) >= 1


def test_custom_validator():
    v = ToolResultValidator()

    def no_none_values(output):
        if isinstance(output, dict) and any(val is None for val in output.values()):
            raise ValidationError("no_nulls", "Dict must not have None values")

    v.add("no_nulls", no_none_values)
    v.check({"x": 1, "y": 2})
    with pytest.raises(ValidationError):
        v.check({"x": None})


def test_wrap_decorator():
    v = ToolResultValidator()
    v.require_type(dict)

    @v.wrap
    def get_data():
        return {"key": "val"}

    assert get_data() == {"key": "val"}


def test_wrap_raises_on_invalid():
    v = ToolResultValidator()
    v.require_type(dict)

    @v.wrap
    def bad_tool():
        return "string"

    with pytest.raises(ValidationError):
        bad_tool()


def test_check_returns_value():
    v = ToolResultValidator()
    v.require_type(str)
    result = v.check("hello")
    assert result == "hello"
