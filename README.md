# Unibasic / Pick PoC in Flask

Comprehensive documentation for the Unibasic / Pick proof-of-concept implemented with Flask and Python.

This repository demonstrates how legacy Pick-style dynamic arrays can be parsed, transformed, exposed as JSON, and updated via a modern Flask API. It is intended as a small but complete PoC illustrating the required adapter logic and translation semantics.

---

## Project structure

- `app.py` — Flask API exposing MongoDB-backed endpoints (students, student_tasks) and the legacy adapter endpoints for `PickRecord`.
- `legacy_parser.py` — `PickRecord` class that implements Pick semantics (READ/EXTRACT), parsing (`to_json`) and writeback (`update`).
- `LEGACY_CLIENTS.dat` — example legacy data file (format: `ID^Name^Balances(VM)]^Dates(VM)`).
- `tests/test_legacy_parser.py` — pytest suite for `PickRecord` behaviors.
- `requirements.txt` — project Python dependencies.

---

## Features summary

- Full simulation of Pick dynamic array semantics using the classic delimiters:
  - `AM='^'` (Attribute mark)
  - `VM=']'` (Value mark)
  - `SM='\'` (Subvalue mark)
- 1-based indexing in `extract()` mirroring Unibasic semantics.
- Typed `to_json()` output with options to parse numbers and dates.
- Transaction pairing (balance/date pairing) into a `transactions` array.
- `update()` method supporting write-back to the flat file (makes a `.bak` backup).
- Flask endpoints to read and update legacy records and to run standard student API operations.

---

## PickRecord API / Class Reference

This describes the principal functions available for programmers integrating with the legacy adapter.

- `PickRecord.read(record_key)`
  - Reads an entry from `DATA_FILE`, returning a `PickRecord` instance with `raw_data` set or `None` if not found.

- `PickRecord.extract(attribute_pos, value_pos=None, subvalue_pos=None)`
  - Mirrors Unibasic `EXTRACT` semantics (all indexes are 1-based):
    - `extract(1)` returns the content of the first attribute.
    - `extract(2,1)` returns the first VM value of the second attribute.
    - `extract(2,1,1)` returns the first subvalue of that VM value.
  - Returns empty string `""` when requested attribute/value/subvalue isn't present.

- `PickRecord.to_json(parse_numbers=True, parse_dates=True, latest_balance='last')`
  - Converts Pick fields into JSON with typed fields and paired transactions.
  - `parse_numbers` — Default True. Numeric strings are tried as `Decimal` internally (JSON returns strings).
  - `parse_dates` — Default True. `YYYY-MM-DD` strings are parsed into `date` objects then serialized in JSON.
  - `latest_balance` — `'first'` or `'last'` to select which VM value should represent `current_balance`.

- `PickRecord.update(attribute_map)`
  - `attribute_map` keys are 1-based attribute positions; values are either a string or a list (which will be joined using `VM`).
  - Creates a `DATA_FILE.bak` copy before modifying.
  - Rewrites the file by replacing the matching `record_key^...` line.
  - Updates the in-memory `raw_data` to the new value.

---

## Flask API Endpoints — Full Reference

Legacy adapter endpoints

- GET /get_legacy_client/<client_id>
  - Query params:
    - `parse_numbers=true|false` (default: true)
    - `parse_dates=true|false` (default: true)
    - `latest=first|last` (default: last)
  - Response: JSON representation of the legacy record as `to_json()` output.

- POST /update_legacy_client/<client_id>
  - Request body: JSON map of attribute index -> value (string or list)
  - Example: `{ "1": "New Name", "2": ["30.00","10.00"] }`
  - Response 200 on success or appropriate error codes for validation failures.

MongoDB endpoints (students and student_tasks) — brief summary

- POST /add_student, POST /add_students — Create student(s)
- GET /get_student/<student_id>, GET /get_students — Read student(s)
- PUT /update_student/<student_id> — Update a student
- DELETE /soft_delete_student/<student_id>, DELETE /hard_delete_student/<student_id> — Soft/hard delete
- Student task equivalents mirror these endpoints for `student_tasks` collection.

Notes: MongoDB endpoints use `flask_pymongo`. The app requires env configuration for `MONGO_URI` in production.

---

## Examples & Usage

Start the server (local dev):

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Query a legacy client (with default parsing):

```bash
curl "http://127.0.0.1:5000/get_legacy_client/101?parse_numbers=true&parse_dates=true&latest=last"
```

Update a legacy client (write-back example):

```bash
curl -X POST -H "Content-Type: application/json" \
  -d "{ \"1\": \"John Updated\", \"2\": [\"1000.00\", \"25.00\"] }" \
  http://127.0.0.1:5000/update_legacy_client/101
```

---

## Tests

To run the unit tests for the parser and updates:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

Notes:

- Tests are built to be deterministic. They create a temporary copy of the legacy-data file and set `PickRecord.DATA_FILE` to the testing file.
- Tests cover extraction semantics (AM/VM/SM), JSON conversion, and update & readback behavior.

---

## Limitations & Production considerations

- Current `read()` performs a linear scan of the entire legacy file — unsuitable for large files. Consider building an index or migrating legacy data to an indexed store.
- `update()` rewrites the entire file — for production, add file locking, transactional journaling, or use an atomic file move.
- Add authentication and API input validation for real-world usage.
- Consider using OpenAPI/Swagger, and add endpoint tests for the full API surface.

---

## Notes and Credits

This repository was created as a demonstration of Pick/Unidata-style parsing and how to integrate with modern Python microservices. The code is intended for learning or as a migration strategy sample rather than as a production-ready adapter without the caveats outlined above.
