"""Tests for tool-result-validator-py.

These tests use only the Python standard library ``unittest`` so they run
with no third-party dependencies::

    python3 -m unittest discover -s tests
"""

import unittest

from tool_result_validator import (
    ToolResultValidator,
    ValidationError,
    ValidationResult,
    __version__,
)


class VersionTests(unittest.TestCase):
    def test_version_exposed(self):
        self.assertIsInstance(__version__, str)
        self.assertTrue(__version__)


class ValidationErrorTests(unittest.TestCase):
    def test_attributes_and_message(self):
        err = ValidationError("my_rule", "something is wrong")
        self.assertEqual(err.rule, "my_rule")
        self.assertEqual(err.reason, "something is wrong")
        self.assertEqual(str(err), "[my_rule] something is wrong")
        self.assertIsInstance(err, Exception)


class ValidationResultTests(unittest.TestCase):
    def test_ok_mirrors_valid(self):
        result = ValidationResult(valid=True, value="x")
        self.assertTrue(result.ok)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.value, "x")

        invalid = ValidationResult(valid=False, value="y", errors=["[r] boom"])
        self.assertFalse(invalid.ok)
        self.assertEqual(invalid.errors, ["[r] boom"])


class EmptyValidatorTests(unittest.TestCase):
    def test_empty_validator_passes(self):
        v = ToolResultValidator()
        self.assertEqual(v.check("anything"), "anything")

    def test_run_returns_result(self):
        v = ToolResultValidator()
        result = v.run("hello")
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.valid)
        self.assertTrue(result.ok)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.value, "hello")


class ChainingTests(unittest.TestCase):
    def test_builders_return_self_for_chaining(self):
        v = ToolResultValidator()
        chained = (
            v.require_type(dict)
            .require_keys(["a"])
            .require_value("a", allowed=[1])
            .require_not_empty()
            .require_length(max_len=5)
            .add("noop", lambda o: None)
        )
        self.assertIs(chained, v)


class RequireTypeTests(unittest.TestCase):
    def test_passes(self):
        v = ToolResultValidator().require_type(dict)
        v.check({"x": 1})

    def test_fails(self):
        v = ToolResultValidator().require_type(dict)
        with self.assertRaises(ValidationError) as ctx:
            v.check("not a dict")
        self.assertIn("dict", str(ctx.exception))
        self.assertEqual(ctx.exception.rule, "type")

    def test_multiple_types(self):
        v = ToolResultValidator().require_type(dict, list)
        v.check({"x": 1})
        v.check([1, 2, 3])
        with self.assertRaises(ValidationError):
            v.check("string")

    def test_custom_rule_name(self):
        v = ToolResultValidator().require_type(int, name="must_be_int")
        with self.assertRaises(ValidationError) as ctx:
            v.check("nope")
        self.assertEqual(ctx.exception.rule, "must_be_int")


class RequireKeysTests(unittest.TestCase):
    def test_passes(self):
        v = ToolResultValidator().require_keys(["status", "data"])
        v.check({"status": "ok", "data": []})

    def test_missing_key_fails(self):
        v = ToolResultValidator().require_keys(["status", "data"])
        with self.assertRaises(ValidationError) as ctx:
            v.check({"status": "ok"})
        self.assertIn("data", str(ctx.exception))

    def test_non_dict_fails(self):
        v = ToolResultValidator().require_keys(["x"])
        with self.assertRaises(ValidationError):
            v.check("not a dict")


class RequireValueTests(unittest.TestCase):
    def test_allowed_passes(self):
        v = ToolResultValidator().require_value("status", allowed=["ok", "error"])
        v.check({"status": "ok"})

    def test_allowed_fails(self):
        v = ToolResultValidator().require_value("status", allowed=["ok", "error"])
        with self.assertRaises(ValidationError) as ctx:
            v.check({"status": "unknown"})
        self.assertIn("unknown", str(ctx.exception))

    def test_disallowed_passes(self):
        v = ToolResultValidator().require_value("status", disallowed=["fail", "error"])
        v.check({"status": "ok"})

    def test_disallowed_fails(self):
        v = ToolResultValidator().require_value("status", disallowed=["fail"])
        with self.assertRaises(ValidationError):
            v.check({"status": "fail"})

    def test_missing_key_fails(self):
        v = ToolResultValidator().require_value("status", allowed=["ok"])
        with self.assertRaises(ValidationError) as ctx:
            v.check({"other": "x"})
        self.assertIn("status", str(ctx.exception))

    def test_non_dict_fails(self):
        v = ToolResultValidator().require_value("status", allowed=["ok"])
        with self.assertRaises(ValidationError):
            v.check("not a dict")

    def test_allowed_and_disallowed_together(self):
        v = ToolResultValidator().require_value(
            "status", allowed=["ok", "error"], disallowed=["error"]
        )
        v.check({"status": "ok"})
        with self.assertRaises(ValidationError):
            v.check({"status": "error"})


class RequireNotEmptyTests(unittest.TestCase):
    def test_string(self):
        v = ToolResultValidator().require_not_empty()
        v.check("hello")
        with self.assertRaises(ValidationError):
            v.check("")

    def test_list(self):
        v = ToolResultValidator().require_not_empty()
        v.check([1, 2])
        with self.assertRaises(ValidationError):
            v.check([])

    def test_none(self):
        v = ToolResultValidator().require_not_empty()
        with self.assertRaises(ValidationError):
            v.check(None)

    def test_tuple(self):
        v = ToolResultValidator().require_not_empty()
        v.check((1, 2))
        with self.assertRaises(ValidationError):
            v.check(())

    def test_set(self):
        v = ToolResultValidator().require_not_empty()
        v.check({1, 2})
        with self.assertRaises(ValidationError):
            v.check(set())

    def test_empty_dict(self):
        v = ToolResultValidator().require_not_empty()
        v.check({"a": 1})
        with self.assertRaises(ValidationError):
            v.check({})

    def test_non_sized_scalar_passes(self):
        # An int has no concept of emptiness and is not None, so it passes.
        v = ToolResultValidator().require_not_empty()
        self.assertEqual(v.check(0), 0)
        self.assertEqual(v.check(42), 42)


class RequireLengthTests(unittest.TestCase):
    def test_passes(self):
        v = ToolResultValidator().require_length(min_len=2, max_len=5)
        v.check("abc")
        v.check([1, 2, 3])

    def test_min_fails(self):
        v = ToolResultValidator().require_length(min_len=3)
        with self.assertRaises(ValidationError):
            v.check("ab")

    def test_max_fails(self):
        v = ToolResultValidator().require_length(max_len=3)
        with self.assertRaises(ValidationError):
            v.check("toolong")

    def test_no_length_object_fails(self):
        v = ToolResultValidator().require_length(min_len=1)
        with self.assertRaises(ValidationError) as ctx:
            v.check(5)
        self.assertIn("no length", str(ctx.exception))


class RunCollectsErrorsTests(unittest.TestCase):
    def test_run_collects_multiple_errors(self):
        v = ToolResultValidator()
        v.require_type(dict)
        v.require_keys(["x", "y"])
        result = v.run("not a dict")
        self.assertFalse(result.valid)
        # Both the type rule and the keys rule should report failures.
        self.assertEqual(len(result.errors), 2)

    def test_run_captures_unexpected_exceptions(self):
        def boom(_output):
            raise RuntimeError("kaboom")

        v = ToolResultValidator().add("boom", boom)
        result = v.run("x")
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("kaboom", result.errors[0])

    def test_check_raises_unexpected_exceptions(self):
        def boom(_output):
            raise RuntimeError("kaboom")

        v = ToolResultValidator().add("boom", boom)
        with self.assertRaises(RuntimeError):
            v.check("x")


class CustomValidatorTests(unittest.TestCase):
    def test_custom_validator(self):
        v = ToolResultValidator()

        def no_none_values(output):
            if isinstance(output, dict) and any(
                val is None for val in output.values()
            ):
                raise ValidationError("no_nulls", "Dict must not have None values")

        v.add("no_nulls", no_none_values)
        v.check({"x": 1, "y": 2})
        with self.assertRaises(ValidationError):
            v.check({"x": None})


class WrapTests(unittest.TestCase):
    def test_wrap_passes_through_valid_result(self):
        v = ToolResultValidator().require_type(dict)

        @v.wrap
        def get_data():
            return {"key": "val"}

        self.assertEqual(get_data(), {"key": "val"})

    def test_wrap_raises_on_invalid(self):
        v = ToolResultValidator().require_type(dict)

        @v.wrap
        def bad_tool():
            return "string"

        with self.assertRaises(ValidationError):
            bad_tool()

    def test_wrap_preserves_metadata_and_arguments(self):
        v = ToolResultValidator().require_type(dict)

        @v.wrap
        def tool(a, b=2):
            """Return a dict combining the arguments."""
            return {"a": a, "b": b}

        self.assertEqual(tool.__name__, "tool")
        self.assertEqual(tool.__doc__, "Return a dict combining the arguments.")
        self.assertEqual(tool(1, b=5), {"a": 1, "b": 5})


class CheckReturnsValueTests(unittest.TestCase):
    def test_check_returns_value(self):
        v = ToolResultValidator().require_type(str)
        self.assertEqual(v.check("hello"), "hello")


if __name__ == "__main__":
    unittest.main()
