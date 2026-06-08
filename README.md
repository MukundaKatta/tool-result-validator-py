# tool-result-validator-py

[![CI](https://github.com/MukundaKatta/tool-result-validator-py/actions/workflows/ci.yml/badge.svg)](https://github.com/MukundaKatta/tool-result-validator-py/actions/workflows/ci.yml)

Validate tool output **before** returning it to an LLM. When an agent calls a
tool, the raw result is often passed straight back into the model's context. If
that result is malformed — wrong type, missing keys, an unexpected status, an
empty payload — the model can hallucinate around it or break downstream parsing.

`tool-result-validator-py` lets you declare what a valid result looks like and
either **raise a clear error on the first violation** (`check`) or **collect all
violations** for structured handling (`run`). It has zero runtime dependencies.

## Install

```bash
pip install tool-result-validator-py
```

## Quick start

```python
from tool_result_validator import ToolResultValidator, ValidationError

validator = (
    ToolResultValidator()
    .require_type(dict)
    .require_keys(["status", "data"])
    .require_value("status", allowed=["ok", "error"])
    .require_not_empty()
)

# Raise on the first violation (good for failing fast inside a tool):
result = validator.check({"status": "ok", "data": [1, 2, 3]})
# result == {"status": "ok", "data": [1, 2, 3]}

# Collect every violation without raising (good for reporting back to the model):
report = validator.run({"status": "unknown", "data": []})
if not report.valid:
    for err in report.errors:
        print(err)
    # [value] 'status' must be one of ['ok', 'error'], got 'unknown'
```

Builder methods return the validator, so rules can be chained as shown above or
added one per line.

### Custom rules

Any callable that takes the output and raises `ValidationError` on failure can
be registered with `add`:

```python
def no_nulls(output):
    if isinstance(output, dict) and any(v is None for v in output.values()):
        raise ValidationError("no_nulls", "Dict must not contain None values")

validator.add("no_nulls", no_nulls)
```

### Wrapping a tool function

Use `@validator.wrap` to validate the return value of a tool automatically. The
wrapper calls `check`, so an invalid result raises `ValidationError`:

```python
@validator.wrap
def my_tool() -> dict:
    return {"status": "ok", "data": []}
```

## Two execution modes

| Method  | Behaviour                                              | Returns                                  |
| ------- | ----------------------------------------------------- | ---------------------------------------- |
| `check` | Stops at the **first** failing rule and raises.       | The validated output (unchanged).        |
| `run`   | Runs **every** rule and collects all failures.        | A `ValidationResult`.                    |

`check` re-raises any unexpected exception from a custom rule, while `run`
captures it as an error string so a single buggy rule never crashes the report.

## API reference

### `ToolResultValidator()`

Construct an empty validator with no rules. Methods that add rules return
`self` for chaining.

| Method | Description |
| ------ | ----------- |
| `add(name, fn)` | Register a custom rule `fn(output)` that raises `ValidationError` on failure. |
| `require_type(*types, name="type")` | Require the output to be an instance of one of `types`. |
| `require_keys(keys, name="required_keys")` | Require a dict output to contain all of `keys`. |
| `require_value(key, allowed=None, disallowed=None, name="value")` | Constrain the value at `key` to be in `allowed` and/or not in `disallowed`. |
| `require_not_empty(name="not_empty")` | Reject `None` and empty `str`/`list`/`tuple`/`set`/`frozenset`/`dict`. Non-sized scalars (e.g. `int`) pass. |
| `require_length(min_len=None, max_len=None, name="length")` | Require an object with `__len__` whose length is within `[min_len, max_len]`. |
| `check(output)` | Run all rules, raising `ValidationError` on the first failure. Returns `output`. |
| `run(output)` | Run all rules, collecting failures. Returns a `ValidationResult`. |
| `wrap(fn)` | Decorator that validates the return value of `fn` via `check`. |

### `ValidationResult`

Dataclass returned by `run`.

| Attribute | Type | Description |
| --------- | ---- | ----------- |
| `valid` | `bool` | `True` when no rule failed. |
| `value` | `Any` | The output that was validated. |
| `errors` | `list[str]` | One formatted message per failed rule. |
| `ok` | `bool` | Alias for `valid`. |

### `ValidationError`

Exception raised by failing rules and by `check`.

| Attribute | Type | Description |
| --------- | ---- | ----------- |
| `rule` | `str` | Name of the rule that failed. |
| `reason` | `str` | Human-readable explanation. |

Its string form is `"[<rule>] <reason>"`.

## Development

The package is fully typed (it ships a `py.typed` marker) and the test suite
uses only the Python standard library:

```bash
python -m unittest discover -s tests
```

## License

MIT
