# Attendance Detection System — Module 1: Student Management

The first module of the **Attendance Detection System Using Python and PostgreSQL**.
It manages university student records based on a traditional attendance sheet:
register, search, filter, view, edit, deactivate, and import or export students as CSV.

> **Scope:** Student Management only. Attendance marking, face recognition, QR codes
> and reports are future modules. The schema and code are structured so they can be
> added without redesigning the student identity model (see [Extending](#extending-for-attendance-modules)).

| Layer      | Technology                                                       |
| ---------- | ---------------------------------------------------------------- |
| Backend    | Python 3.11+, FastAPI, SQLAlchemy 2 ORM, Pydantic v2, Alembic    |
| Database   | PostgreSQL 14+ (tested on 16)                                    |
| Frontend   | React 18, Vite 5, Tailwind CSS 4, Lucide React, React Router 6   |
| Tests      | Pytest + FastAPI TestClient against a real PostgreSQL test DB    |

---

## Architecture

```text
 Browser (React SPA, :5173)
     │  fetch /api/...   (JSON, X-API-Key header for writes)
     ▼
 Vite dev server ── proxy /api ──►  FastAPI (:8000)
                                     ├─ routers/   HTTP layer: parse + validate input, status codes
                                     ├─ services/  business rules: duplicates, soft delete, CSV, stats
                                     ├─ schemas/   Pydantic validation + normalization, response shapes
                                     ├─ models/    SQLAlchemy ORM model (students table)
                                     └─ db/        engine + session per request
                                            │  parameterized SQL (psycopg2)
                                            ▼
                                     PostgreSQL  attendance_db.students
                                     (schema owned by Alembic migrations)
```

Key design decisions:

- **Soft delete.** `DELETE /api/students/{id}` sets `status = Inactive`. Records are never
  physically removed, because future attendance history will reference them. Reactivate with `PUT`.
- **Two identifiers.** `id` (BIGINT identity) is the internal key that future tables reference.
  `student_id` (VARCHAR(20), unique) is the university ID. It is stored as text so leading zeros
  survive, and normalized to upper case so `e001` and `E001` count as duplicates.
- **Validation in three places.** The browser validates for fast feedback, Pydantic enforces the
  rules on the API, and PostgreSQL `CHECK` / `UNIQUE` constraints are the last guard.
- **Concurrent edits.** The edit form sends the `updated_at` value it loaded. If someone else saved
  in the meantime, the API returns `409 stale_update` instead of silently overwriting. Rows are
  locked (`SELECT … FOR UPDATE`) while they are updated.
- **Duplicate submissions.** Submit buttons are disabled while a request runs, and the unique
  constraint catches any race between two clients.
- **Consistent errors.** Every error has the shape
  `{"error": {"code", "message", "details"}}`. Database errors are logged on the server and
  returned as a generic message, never SQL, credentials or stack traces.

---

## Prerequisites (Windows)

- **Python 3.11+**: `python --version`
- **Node.js 18+** (20 LTS recommended): `node --version`
- **PostgreSQL 14+** installed locally, with `psql` on your PATH
  (default location: `C:\Program Files\PostgreSQL\16\bin`)

---

## Setup — Windows PowerShell

All commands assume you start in the project folder:

```powershell
cd D:\Beltie-IU\MyProject\Attendance_detection
```

### 1. Create the databases

```powershell
# You will be prompted for the postgres user's password.
psql -U postgres -h localhost -c "CREATE DATABASE attendance_db;"
psql -U postgres -h localhost -c "CREATE DATABASE attendance_test_db;"
```

If `psql` is not recognized, add PostgreSQL to the PATH for this session:

```powershell
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"
```

### 2. Configure environment variables

```powershell
Copy-Item .env.example .env
notepad .env
```

Set `DATABASE_URL` and `TEST_DATABASE_URL` with your PostgreSQL password. URL-encode special
characters: `@` becomes `%40` and `#` becomes `%23`.

To protect write operations, generate an admin key and put it in `ADMIN_API_KEY`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
python -m pip install --upgrade pip
pip install -r requirements.txt

alembic upgrade head                   # creates the students table
uvicorn app.main:app --reload --port 8000
```

- API: <http://localhost:8000/api/health> should return `{"status":"ok","database":"connected",...}`
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

### 4. Frontend (in a second PowerShell window)

```powershell
cd D:\Beltie-IU\MyProject\Attendance_detection\frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server forwards `/api` to `http://localhost:8000`.

If `ADMIN_API_KEY` is set, open **Settings** in the app and paste the key. Adding, editing,
deactivating, importing and exporting all require it; viewing does not.

### 5. Load sample data (optional)

In the app, go to **Students → Import CSV** and choose `samples\student_import_template.csv`.
You can also run:

```powershell
curl.exe -H "X-API-Key: YOUR_KEY" -F "file=@samples/student_import_template.csv" http://localhost:8000/api/students/import
```

### 6. Run the tests

The tests use `TEST_DATABASE_URL` from `.env` or the environment. They refuse to run unless the
database name contains `test`, so real data is never touched. The suite runs the Alembic migrations
on the test database and empties the table after each test.

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
# or point at a different test database for one run:
$env:TEST_DATABASE_URL = "postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/attendance_test_db"
pytest -v
```

### Production build of the frontend

```powershell
cd frontend
npm run build      # output in frontend\dist
npm run preview    # serve the build locally
```

When deploying, serve `dist/` and the API from the same origin, or set `VITE_API_BASE_URL` at build
time and add the frontend origin to `CORS_ORIGINS`. Set `ENVIRONMENT=production`; the API refuses
to start without an `ADMIN_API_KEY` in that mode.

---

## Database schema

Created by `backend/alembic/versions/20261023_0001_create_students_table.py`.

| Column            | Type          | Rules                                                     |
| ----------------- | ------------- | --------------------------------------------------------- |
| `id`              | BIGINT        | Primary key, `GENERATED BY DEFAULT AS IDENTITY`           |
| `student_id`      | VARCHAR(20)   | NOT NULL, UNIQUE (`uq_students_student_id`), not blank    |
| `full_name_khmer` | VARCHAR(150)  | nullable                                                  |
| `full_name_latin` | VARCHAR(150)  | NOT NULL, not blank                                       |
| `gender`          | VARCHAR(10)   | NOT NULL, `IN ('Male','Female','Other')`                  |
| `program`         | VARCHAR(100)  | nullable                                                  |
| `major`           | VARCHAR(150)  | nullable, indexed                                         |
| `academic_year`   | SMALLINT      | nullable, `> 0` (API accepts 1–10)                        |
| `semester`        | SMALLINT      | nullable, `IN (1, 2)`                                     |
| `status`          | VARCHAR(20)   | NOT NULL, default `'Active'`, `IN ('Active','Inactive')`, indexed |
| `created_at`      | TIMESTAMPTZ   | NOT NULL, default `now()`                                 |
| `updated_at`      | TIMESTAMPTZ   | NOT NULL, default `now()`, refreshed on every update      |

Useful migration commands (run inside `backend` with the venv active):

```powershell
alembic current                                   # show applied revision
alembic history                                   # list migrations
alembic revision --autogenerate -m "add subjects" # after changing models
alembic upgrade head
alembic downgrade -1
alembic check                                     # verify models and migrations match
```

The app never calls `create_all()`; Alembic owns the schema.

---

## API reference

Interactive documentation is generated by FastAPI at **<http://localhost:8000/docs>** (Swagger UI).
Click **Authorize** and enter the admin key to try the protected endpoints.
The raw OpenAPI schema is at `/openapi.json`.

| Method | Path                       | Auth | Description |
| ------ | -------------------------- | ---- | ----------- |
| GET    | `/api/students`            | —    | List with `page`, `page_size` (≤100), `search`, `gender`, `major`, `academic_year`, `semester`, `status`, `sort_by`, `sort_order` |
| GET    | `/api/students/{id}`       | —    | One student, `404` if missing |
| POST   | `/api/students`            | key  | Create, `201`. `409 duplicate_student_id`, `422 validation_error` |
| PUT    | `/api/students/{id}`       | key  | Full update. Optional `expected_updated_at` returns `409 stale_update` if the record changed |
| DELETE | `/api/students/{id}`       | key  | Deactivate (soft delete), returns the student |
| GET    | `/api/students/filters`    | —    | Distinct majors, programs and years for the filter dropdowns |
| POST   | `/api/students/import`     | key  | Multipart `file` (CSV). `?skip_invalid=true` saves only valid rows |
| GET    | `/api/students/export`     | key  | UTF-8 CSV download; accepts the same filters as the list |
| GET    | `/api/dashboard/stats`     | —    | Totals, active/inactive, counts by major and gender |
| GET    | `/api/health`              | —    | API and database connectivity |
| POST   | `/api/attendance/sheets`   | key  | Save a paper attendance sheet: tick → `true`/1, `P` → `false`/0, blank → not stored. All-or-nothing; re-sending updates marks |
| GET    | `/api/attendance/records`  | —    | Marks with `value` 0/1; filter by `student_id`, `subject_code`, `is_present` |

"key" means the `X-API-Key` header is required when `ADMIN_API_KEY` is configured.

Example (PowerShell):

```powershell
$headers = @{ "X-API-Key" = "YOUR_KEY" }
$body = @{ student_id = "0012024010"; full_name_latin = "Sok Dara"; gender = "Male"; semester = 1 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/students -Headers $headers -ContentType "application/json" -Body $body
Invoke-RestMethod "http://localhost:8000/api/students?search=dara&status=Active"
```

---

## CSV import and export

Template: [`samples/student_import_template.csv`](samples/student_import_template.csv). The app's
Import dialog also has a download link for it.

```csv
student_id,full_name_khmer,full_name_latin,gender,program,major,academic_year,semester,status
0012024001,សុខ សុភា,Sok Sophea,Female,Bachelor,Computer Science,1,Semester 1,Active
```

- Encoding must be **UTF-8**. In Excel, use *Save As → CSV UTF-8 (Comma delimited)*.
- Required columns: `student_id`, `full_name_latin`, `gender`. Unknown columns are ignored.
- `gender` and `status` are case-insensitive. `semester` accepts `1`, `2`, `Semester 1` or `S2`.
  An empty `status` means `Active`.
- Every row is validated: field rules, duplicates inside the file, and IDs already in the database.
- **Default (all-or-nothing):** if any row is invalid, **nothing is saved**, and the report lists
  each failing line and its problems.
- **"Import valid rows only"** (`skip_invalid=true`): valid rows are saved in one transaction, and
  the report lists exactly which lines were saved and which were skipped.
- Limits: 2 MB and 5,000 rows per file (configurable).

Export:

- Writes the students matching the current filters, with a UTF-8 BOM so Excel shows Khmer correctly.
- Requires the admin key.
- Cells starting with `= + - @` are prefixed with `'` to prevent spreadsheet formula injection.

---

## Project structure and how each file works

```text
Attendance_detection/
├── .env.example                 Template for secrets/config (copy to .env; .env is git-ignored)
├── .gitignore
├── README.md
├── samples/student_import_template.csv
├── backend/
│   ├── requirements.txt         Pinned Python dependencies
│   ├── alembic.ini              Alembic config (no DB URL inside; read from env)
│   ├── pytest.ini
│   ├── alembic/
│   │   ├── env.py               Loads DATABASE_URL + model metadata, runs migrations
│   │   ├── script.py.mako       Template for new migrations
│   │   └── versions/…0001_create_students_table.py   Creates table, constraints, indexes
│   ├── app/
│   │   ├── main.py              Builds the FastAPI app: CORS, error handlers, routers, /api/health
│   │   ├── core/config.py       Pydantic Settings: reads env vars / .env
│   │   ├── core/errors.py       AppError types + global handlers → uniform JSON errors, no leaks
│   │   ├── core/security.py     require_admin dependency (X-API-Key, constant-time compare)
│   │   ├── db/base.py           Declarative Base with constraint naming convention
│   │   ├── db/session.py        Engine, SessionLocal, get_db() per-request dependency
│   │   ├── models/student.py    Student ORM model + CHECK constraints + indexes
│   │   ├── schemas/student.py   Create/Update/Read models, normalization, list/filter params,
│   │   │                        import report models
│   │   ├── schemas/dashboard.py Dashboard response models
│   │   ├── routers/students.py  /api/students endpoints (thin; delegate to the service)
│   │   ├── routers/dashboard.py /api/dashboard/stats
│   │   └── services/student_service.py  Queries, filters, sorting, pagination, duplicate checks,
│   │                            optimistic locking, soft delete, stats, CSV import/export
│   └── tests/
│       ├── conftest.py          Test DB safety guard, Alembic migrate, truncate per test, clients
│       ├── test_students.py     CRUD, validation, search, filters, pagination, sorting, auth
│       ├── test_dashboard.py    Statistics
│       ├── test_csv.py          Import validation/duplicates/modes, export, round trip
│       └── test_errors.py       Hidden DB errors, error envelope, health, OpenAPI
└── frontend/
    ├── package.json, vite.config.js   Vite + React + Tailwind plugin; /api dev proxy
    ├── index.html               Loads Inter + Noto Sans Khmer fonts
    ├── .env.example             Optional VITE_* settings
    ├── public/                  favicon, CSV template (downloadable from the app)
    └── src/
        ├── main.jsx, App.jsx    Entry point; routes inside ToastProvider + AppLayout
        ├── index.css            Tailwind import, brand color tokens, button/input/card utilities
        ├── layouts/AppLayout.jsx     Sidebar (desktop), drawer (mobile), skip link, page outlet
        ├── pages/
        │   ├── DashboardPage.jsx     Summary cards + per-major cards (click to filter list)
        │   ├── StudentsPage.jsx      Filters, table, pagination, add/edit/import/export/deactivate
        │   ├── StudentDetailPage.jsx All fields + registered/updated timestamps, edit/deactivate
        │   ├── SettingsPage.jsx      Admin key entry, connection test, link to API docs
        │   └── NotFoundPage.jsx
        ├── components/
        │   ├── StudentTable.jsx      Sortable table (desktop) / cards (mobile), row actions
        │   ├── StudentFilters.jsx    Debounced search + gender/major/year/semester/status filters
        │   ├── StudentFormModal.jsx  Add/edit form, client validation, server error mapping
        │   ├── ImportModal.jsx       CSV upload, import mode choice, row-by-row report
        │   ├── Pagination.jsx, StatCard.jsx, StatusBadge.jsx, PageHeader.jsx (breadcrumbs)
        │   ├── Modal.jsx             Native <dialog>: focus trap, Esc to close
        │   ├── ConfirmDialog.jsx     Confirmation for destructive actions
        │   ├── ToastProvider.jsx     Success/error notifications (aria-live)
        │   └── States.jsx            Loading / empty / error states
        ├── hooks/
        │   ├── useApiQuery.js        Fetch + loading/error state, ignores stale responses
        │   ├── useStudentQuery.js    Keeps search/filter/sort/page in the URL
        │   ├── useStudentStatusToggle.js  Confirm-then-deactivate/reactivate flow
        │   ├── useDebounce.js, useToast.js
        ├── services/
        │   ├── api.js                fetch wrapper, ApiError, X-API-Key storage, file download
        │   └── studentService.js     One function per backend endpoint
        └── types/student.js          Constants, JSDoc types, form ↔ payload mapping, validation
```

---

## Security notes

- Credentials live only in `.env`, which is git-ignored. `.env.example` holds placeholders.
- All SQL goes through SQLAlchemy with bound parameters. Sort columns come from a whitelist, and
  `LIKE` wildcards in searches are escaped.
- CORS allows only the origins in `CORS_ORIGINS`, with only the needed methods and headers.
- Write operations and bulk export require `ADMIN_API_KEY` (checked in constant time). The key is
  kept in the browser's `sessionStorage`, or in `localStorage` if "Remember" is ticked.
- **Before production:** replace the shared key with real user accounts (hashed passwords with
  bcrypt/argon2, roles such as admin/lecturer, short-lived tokens) and serve over HTTPS.
  Routes depend only on `require_admin`, so this is a contained change in `core/security.py`.
- Unexpected and database errors are logged server-side. Clients receive only a generic message.

## Scanning attendance sheets (photo → database)

Open **Attendance** in the web app, choose a photo of the paper sheet and click **Scan & save**.
The sheet is read and **saved immediately** in one transaction:

1. The header is read: major, program, year, semester, week and room.
2. Each student row is read. Students not yet registered are created from the header values;
   existing students are left unchanged.
3. Each mark is stored in `attendance_records`: a tick becomes `is_present = true` (**1**), a `P`
   becomes `false` (**0**), and blank cells and shaded "no class" columns are not stored.
4. Cells that can't be read with confidence are skipped, and each one is listed under
   **"Check these on the paper sheet"**.

Scanning the same sheet again updates the marks instead of duplicating them. Subject codes are
matched without spaces, so OCR's `APPII` is the same subject as `APP II`.

### Readers (`SHEET_READER` in `.env`)

| Value | Cost | How it works |
|---|---|---|
| `offline` (default) | Free, no internet | RapidOCR reads the printed text (IDs, names, M/F, dates, subject codes, header). Marks are classified by ink colour: **red ink = P (0)**, dark/blue tick = **1**. Runs on your computer in about 30–60 s per sheet. |
| `claude` | Paid API, a few cents per sheet | Claude vision (`claude-opus-5-5`). Also reads Khmer names and handwriting. Needs `ANTHROPIC_API_KEY` from https://platform.claude.com. The photo is sent to Anthropic. |

Tips for the offline reader: take the photo straight on and in focus, with the whole grid visible.
P must be written in **red** ink, which is the sheet's convention. On the results, a tick shows **✓**
(present, 1) and a P or an empty cell shows **✗** (not present, 0).

Spaces in Latin names are recovered automatically; a name that still has none is flagged. Scanning
a sheet again also fixes saved names that only lacked their spaces.

Khmer names are read offline with [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) and its
Khmer model. Install Tesseract (default path `C:\Program Files\Tesseract-OCR`), then download
[`khm.traineddata`](https://github.com/tesseract-ocr/tessdata_best/raw/main/khm.traineddata) into
`%LOCALAPPDATA%\tessdata` (or set `TESSERACT_CMD` / `TESSDATA_DIR` in `.env`). Without it, Khmer names
are left blank. OCR can make small spelling slips, so check them on the Students page. A missing Khmer
name on an existing student is filled in on the next scan; one already saved is never overwritten.

The API endpoint is `POST /api/attendance/scan` (multipart field `file`, admin key required when
`ADMIN_API_KEY` is set).

## Attendance sheets (migration 0002)

Tables: `subjects` (code, name), `class_sessions` (subject, date, session 1–4, week, room) and
`attendance_records` (one row per student per session: `is_present` BOOLEAN, where 1 = tick and
0 = `P`, plus `raw_mark` as written on paper). Each student/session pair is unique.

Example body for `POST /api/attendance/sheets`, with one entry in `marks` per column:

```json
{
  "week": 11, "room": "404",
  "columns": [
    {"subject_code": "APP II", "subject_name": "Advanced Python Programming II", "date": "2026-10-19", "session": 1},
    {"subject_code": "APP II", "date": "2026-10-19", "session": 2}
  ],
  "rows": [
    {"student_id": "00056929", "marks": ["P", "P"]},
    {"student_id": "00058285", "marks": ["✓", "✓"]}
  ]
}
```

To view the marks as 0/1 in psql:

```sql
SELECT s.student_id, s.full_name_latin, sub.code, cs.session_date, cs.session_number, ar.is_present::int AS value
FROM attendance_records ar
JOIN students s ON s.id = ar.student_id
JOIN class_sessions cs ON cs.id = ar.class_session_id
JOIN subjects sub ON sub.id = cs.subject_id
ORDER BY cs.session_date, sub.code, cs.session_number, s.student_id;
```

## Extending further

The `students.id` BIGINT key is the stable reference for future tables, for example:

```text
subjects(id, code, name, …)
class_sessions(id, subject_id → subjects.id, starts_at, room, …)
enrollments(student_id → students.id, subject_id → subjects.id, academic_year, semester)
attendance_records(id, session_id → class_sessions.id, student_id → students.id, status, method, recorded_at)
face_profiles(id, student_id → students.id, embedding, created_at)
```

Because students are only ever deactivated, never deleted, these foreign keys stay valid. Add each
module as a new model, schema, service and router, plus a new Alembic revision. Add a new page and
sidebar entry on the frontend.

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| `password authentication failed` | Check the password in `DATABASE_URL`; URL-encode special characters. |
| `database "attendance_db" does not exist` | Run step 1. |
| `relation "students" does not exist` | Run `alembic upgrade head` in `backend`. |
| UI says "Cannot reach the server" | Start the backend on port 8000, or set `VITE_PROXY_TARGET`. |
| `401 invalid_api_key` | Enter the key on the Settings page; it must match `ADMIN_API_KEY`. |
| Khmer text garbled after opening an export in Excel | Use *Data → From Text/CSV* and pick UTF-8 (the export already includes a BOM). |
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
