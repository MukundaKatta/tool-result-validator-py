"""tool-result-validator-py — validate tool output against a schema before returning to LLM."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

__version__ = "0.1.0"


class ValidationError(Exception):
    """Raised when tool output fails validation."""

    def __init__(self, rule: str, reason: str) -> None:
        self.rule = rule
        self.reason = reason
        super().__init__(f"[{rule}] {reason}")


@dataclass
class ValidationResult:
    """Result of validating tool output."""

    valid: bool
    value: Any
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.valid


class ToolResultValidator:
    """
    Validate tool output before returning it to an LLM.

    Validators are chained functions that receive the output and raise
    ValidationError on failure. Use built-in helpers or add custom validators.

    Example::

        validator = ToolResultValidator()
        validator.require_type(dict)
        validator.require_keys(["status", "data"])
        validator.require_value("status", allowed=["ok", "error"])

        result = validator.run({"status": "ok", "data": [1, 2, 3]})
        assert result.valid

        # Raise on invalid:
        validator.check({"status": "unknown"})   # raises ValidationError
    """

    def __init__(self) -> None:
        self._validators: list[tuple[str, Callable[[Any], None]]] = []

    def add(self, name: str, fn: Callable[[Any], None]) -> "ToolResultValidator":
        """Add a custom validator. Raise ValidationError to fail."""
        self._validators.append((name, fn))
        return self

    def require_type(self, *types: type, name: str = "type") -> "ToolResultValidator":
        """Require output to be an instance of one of the given types."""

        def v(output: Any) -> None:
            if not isinstance(output, types):
                expected = " | ".join(t.__name__ for t in types)
                raise ValidationError(
                    name, f"Expected {expected}, got {type(output).__name__}"
                )

        return self.add(name, v)

    def require_keys(
        self, keys: list[str], name: str = "required_keys"
    ) -> "ToolResultValidator":
        """Require a dict output to contain all listed keys."""

        def v(output: Any) -> None:
            if not isinstance(output, dict):
                raise ValidationError(name, "Output must be a dict to check keys")
            missing = [k for k in keys if k not in output]
            if missing:
                raise ValidationError(name, f"Missing required keys: {missing}")

        return self.add(name, v)

    def require_value(
        self,
        key: str,
        allowed: list[Any] | None = None,
        disallowed: list[Any] | None = None,
        name: str = "value",
    ) -> "ToolResultValidator":
        """Validate the value of a specific dict key."""

        def v(output: Any) -> None:
            if not isinstance(output, dict):
                raise ValidationError(name, "Output must be a dict to check values")
            if key not in output:
                raise ValidationError(name, f"Key '{key}' not found in output")
            val = output[key]
            if allowed is not None and val not in allowed:
                raise ValidationError(
                    name, f"'{key}' must be one of {allowed}, got {val!r}"
                )
            if disallowed is not None and val in disallowed:
                raise ValidationError(
                    name, f"'{key}' must not be one of {disallowed}, got {val!r}"
                )

        return self.add(name, v)

    def require_not_empty(self, name: str = "not_empty") -> "ToolResultValidator":
        """Require output to be non-empty (string, list, tuple, set, or dict)."""

        def v(output: Any) -> None:
            if output is None:
                raise ValidationError(name, "Output must not be None")
            if (
                isinstance(output, (str, list, tuple, set, frozenset, dict))
                and not output
            ):
                raise ValidationError(
                    name, f"{type(output).__name__} must not be empty"
                )

        return self.add(name, v)

    def require_length(
        self,
        min_len: int | None = None,
        max_len: int | None = None,
        name: str = "length",
    ) -> "ToolResultValidator":
        """Require a string or list to have a length within the given range."""

        def v(output: Any) -> None:
            if not hasattr(output, "__len__"):
                raise ValidationError(name, f"{type(output).__name__} has no length")
            n = len(output)
            if min_len is not None and n < min_len:
                raise ValidationError(name, f"Length {n} is below minimum {min_len}")
            if max_len is not None and n > max_len:
                raise ValidationError(name, f"Length {n} exceeds maximum {max_len}")

        return self.add(name, v)

    def check(self, output: Any) -> Any:
        """Run all validators; raise ValidationError on the first failure."""
        for _, fn in self._validators:
            fn(output)
        return output

    def run(self, output: Any) -> ValidationResult:
        """Run all validators, collecting all errors without raising."""
        errors: list[str] = []
        for _, fn in self._validators:
            try:
                fn(output)
            except ValidationError as exc:
                errors.append(str(exc))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Unexpected error: {exc}")
        return ValidationResult(valid=len(errors) == 0, value=output, errors=errors)

    def wrap(self, fn: Callable) -> Callable:
        """Decorator that validates the return value of a tool function."""
        import functools

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = fn(*args, **kwargs)
            return self.check(result)

        return wrapper


__all__ = [
    "ToolResultValidator",
    "ValidationError",
    "ValidationResult",
    "__version__",
]
