# Student Management System (Microservices)

A full-stack Student Management System built on a microservices architecture. Users can register, log in, manage student records, manage courses, and assign students to courses.

## Architecture

```
                    +-----------------------+
   Browser  ------> |  React frontend :5173 |
                    +-----------+-----------+
                                |  (only talks to the gateway)
                                v
                    +-----------------------+
                    |  API Gateway   :8000  |
                    +----+------+------+----+
        /auth/*         |      |      |        /courses/*
          +-------------+      |      +--------------+
          v                    v                     v
 +----------------+  +------------------+  +------------------+
 | auth-service   |  | student-service  |  | course-service   |
 |     :8001      |  |      :8002       |  |      :8003       |
 |   auth.db      |  |   students.db    |  |   courses.db     |
 +----------------+  +------------------+  +---------+--------+
                              ^                       |
                              +-----------------------+
                       (course-service asks student-service
                        to verify / look up students)
```

| Component | Port | Responsibility | Database |
|-----------|------|----------------|----------|
| `frontend` | 5173 | React UI (login, register, dashboard, students, courses) | none |
| `api-gateway` | 8000 | Single entry point; routes `/auth/*`, `/students/*`, `/courses/*`; handles unknown routes (404) and downstream failures (502/503/504) | none |
| `auth-service` | 8001 | Registration, login, JWT creation, `/auth/me` | `auth.db` (SQLite) |
| `student-service` | 8002 | Student CRUD | `students.db` (SQLite) |
| `course-service` | 8003 | Course CRUD, enrollment (assign students, list students in a course) | `courses.db` (SQLite) |

Design notes:

- **Independent services, separate databases.** Each service owns its own SQLite file. The course service stores only `student_id` for enrollments and calls the student service (over HTTP, forwarding the user's token) to verify a student on assignment and to show student details.
- **JWT.** The auth service signs tokens with `JWT_SECRET`. The student and course services validate them locally with the same shared secret, so they stay protected even if called directly. Logout is handled on the frontend by discarding the token.
- **Gateway.** The frontend only knows `VITE_API_URL` (the gateway). The gateway forwards the `Authorization` header and passes service responses through unchanged.
- **Deleting a student** does not cascade into the course service (separate databases). Enrollment lists simply skip students that no longer exist.

## Project structure

```
student-management/
├── frontend/          React (Vite) app: components/, pages/, services/
├── api-gateway/       main.py, requirements.txt
├── auth-service/      app/{main,models,schemas,database}.py
├── student-service/   app/{main,models,schemas,database}.py
├── course-service/    app/{main,models,schemas,database}.py
├── postman/           collection.json
├── tests/             smoke_test.py (end-to-end check through the gateway)
└── README.md
```

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- Postman (optional, for the collection)

## Environment variables

Every service has a `.env.example`. Copy it to `.env` and edit. **No secrets are hardcoded**: the three backend services refuse to start unless `JWT_SECRET` is set to a real value.

Generate a secret and use the **same value** in `auth-service`, `student-service` and `course-service`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

| Service | Variable | Purpose | Default in `.env.example` |
|---------|----------|---------|---------------------------|
| auth / student / course | `JWT_SECRET` | Shared signing secret (**required**) | `change-me` (rejected at startup) |
| auth / student / course | `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| auth | `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime | `60` |
| auth / student / course | `DATABASE_URL` | SQLite file | `sqlite:///./auth.db`, `students.db`, `courses.db` |
| course | `STUDENT_SERVICE_URL` | Where to reach the student service | `http://localhost:8002` |
| api-gateway | `AUTH_SERVICE_URL`, `STUDENT_SERVICE_URL`, `COURSE_SERVICE_URL` | Downstream service URLs | `http://localhost:8001` / `8002` / `8003` |
| api-gateway | `CORS_ORIGINS` | Allowed frontend origins (comma-separated) | `http://localhost:5173` |
| api-gateway | `REQUEST_TIMEOUT_SECONDS` | Timeout for downstream calls | `10` |
| frontend | `VITE_API_URL` | Gateway URL | `http://localhost:8000` |

## Setup and run

Open **five terminals** (one per component), starting from the `student-management/` folder. Start the services before the gateway.

### 1. Auth service (port 8001)

```bash
cd auth-service
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then set JWT_SECRET
uvicorn app.main:app --port 8001 --reload
```

### 2. Student service (port 8002)

```bash
cd student-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # same JWT_SECRET as the auth service
uvicorn app.main:app --port 8002 --reload
```

### 3. Course service (port 8003)

```bash
cd course-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # same JWT_SECRET as the auth service
uvicorn app.main:app --port 8003 --reload
```

### 4. API gateway (port 8000)

```bash
cd api-gateway
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --port 8000 --reload
```

### 5. Frontend (port 5173)

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173, register an account, sign in, and start adding courses and students.

Database tables are created automatically the first time each service starts (`Base.metadata.create_all` in each service's `app/main.py`; the models are in `app/models.py`).

## API documentation (Swagger UI)

Each FastAPI service serves interactive docs:

| Service | Swagger UI |
|---------|-----------|
| Auth | http://localhost:8001/docs |
| Student | http://localhost:8002/docs |
| Course | http://localhost:8003/docs |
| Gateway | http://localhost:8000/docs (gateway-level endpoints only; the proxied routes are documented by the services above) |

To call protected endpoints in Swagger: log in via `POST /auth/login`, copy the `access_token`, click **Authorize**, and paste the token.

## API reference

All client calls go through the gateway (`http://localhost:8000`). Everything except register/login requires `Authorization: Bearer <token>`.

**Auth**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create a user (`username`, `email`, `password`) |
| POST | `/auth/login` | Returns `access_token` and the user |
| GET | `/auth/me` | Current user from the token |

**Students**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/students` | Create (`name`, `email`, `phone`, `department`, `course`) |
| GET | `/students` | List all |
| GET | `/students/{student_id}` | Get one |
| PUT | `/students/{student_id}` | Update (partial fields allowed) |
| DELETE | `/students/{student_id}` | Delete |

**Courses and enrollment**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/courses` | Create (`code`, `name`, `description`, `credits`) |
| GET | `/courses` | List all |
| GET | `/courses/{course_id}` | Get one |
| PUT | `/courses/{course_id}` | Update |
| DELETE | `/courses/{course_id}` | Delete (removes its enrollments) |
| POST | `/courses/{course_id}/students` | Assign a student (`{"student_id": 1}`) |
| GET | `/courses/{course_id}/students` | Students enrolled in the course |
| DELETE | `/courses/{course_id}/students/{student_id}` | Remove a student from the course |

**Error handling**

| Status | Meaning |
|--------|---------|
| 401 | Missing/invalid/expired token or wrong credentials |
| 403 | No `Authorization` header sent |
| 404 | Resource or gateway route not found |
| 409 | Duplicate email / username / course code / enrollment |
| 422 | Validation error (field-level messages in `detail`) |
| 502 / 503 / 504 | Gateway: bad response from, unreachable, or timed-out downstream service |

## Testing

**Postman:** import `postman/collection.json`. Collection variables (`baseUrl`, `email`, `password`, ...) are pre-filled. Run in this order: Gateway, Auth (Register, then Login, which stores the token), Students, Courses and Enrollment, Cleanup. Each request includes basic status-code tests.

**Smoke test script** (all services and the gateway running; needs `pip install httpx`):

```bash
python tests/smoke_test.py            # defaults to http://localhost:8000
```

It registers a fresh user and exercises authentication, validation errors, student CRUD, course CRUD, enrollment, and cleanup through the gateway.

## Screenshots

Add your screenshots to a `screenshots/` folder and reference them here: login, dashboard, students list, add/edit student form, courses page with enrolled students, and Swagger UI / Postman responses.

## Git and GitHub

```bash
git init
git add .
git commit -m "feat: student management system with microservices"
git branch -M main
git remote add origin https://github.com/<your-username>/student-management.git
git push -u origin main
```

`.gitignore` already excludes `.env` files, `*.db` databases, virtual environments and `node_modules`; only the `.env.example` files are committed.
