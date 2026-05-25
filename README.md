# tool-result-validator-py

Validate tool output before returning it to the LLM. Raise clear errors or collect all violations for structured handling.

## Install

```bash
pip install tool-result-validator-py
```

## Usage

```python
from tool_result_validator import ToolResultValidator, ValidationError

validator = ToolResultValidator()
validator.require_type(dict)
validator.require_keys(["status", "data"])
validator.require_value("status", allowed=["ok", "error"])
validator.require_not_empty()
validator.require_length(min_len=1, max_len=100)  # for strings/lists

# Raise on first violation
result = validator.check({"status": "ok", "data": [1, 2, 3]})

# Collect all violations
report = validator.run({"status": "unknown"})
if not report.valid:
    for err in report.errors:
        print(err)

# Custom rule
def no_nulls(output):
    if any(v is None for v in output.values()):
        raise ValidationError("no_nulls", "Dict must not have None values")
validator.add("no_nulls", no_nulls)

# Wrap a tool function
@validator.wrap
def my_tool() -> dict:
    return {"status": "ok", "data": []}
```

## License

MIT
