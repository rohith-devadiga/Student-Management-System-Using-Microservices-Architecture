"""End-to-end smoke test that talks only to the API gateway.

Usage (all services running):  python tests/smoke_test.py [gateway_url]
"""
import sys
import uuid

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
client = httpx.Client(base_url=BASE, timeout=10)
passed = 0


def check(label, response, expected):
    global passed
    ok = response.status_code == expected
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: {response.status_code} (expected {expected})")
    if not ok:
        print("       body:", response.text[:300])
        sys.exit(1)
    passed += 1
    return response


suffix = uuid.uuid4().hex[:8]
email = f"user_{suffix}@example.com"
password = "secret123"

check("gateway health", client.get("/health"), 200)
check("invalid route", client.get("/nope"), 404)
check("register", client.post("/auth/register", json={"username": f"user_{suffix}", "email": email, "password": password}), 201)
check("register duplicate", client.post("/auth/register", json={"username": f"user_{suffix}", "email": email, "password": password}), 409)
check("register invalid email", client.post("/auth/register", json={"username": "abc", "email": "bad", "password": password}), 422)
check("login wrong password", client.post("/auth/login", json={"email": email, "password": "wrongpass"}), 401)
token = check("login", client.post("/auth/login", json={"email": email, "password": password}), 200).json()["access_token"]
auth = {"Authorization": f"Bearer {token}"}
check("me", client.get("/auth/me", headers=auth), 200)
check("students without token", client.get("/students"), 403)
check("students bad token", client.get("/students", headers={"Authorization": "Bearer junk"}), 401)

student = check(
    "create student",
    client.post(
        "/students",
        headers=auth,
        json={"name": "Asha Rao", "email": f"asha_{suffix}@example.com", "phone": "+91 98765 43210", "department": "CSE", "course": "Python"},
    ),
    201,
).json()
check("create student duplicate email", client.post("/students", headers=auth, json={**student, "name": "Dup"}), 409)
check("create student invalid phone", client.post("/students", headers=auth, json={**{k: student[k] for k in ("name", "email", "department", "course")}, "phone": "abc"}), 422)
check("list students", client.get("/students", headers=auth), 200)
check("get student", client.get(f"/students/{student['id']}", headers=auth), 200)
updated = check("update student", client.put(f"/students/{student['id']}", headers=auth, json={"department": "ECE"}), 200).json()
assert updated["department"] == "ECE"
check("student not found", client.get("/students/999999", headers=auth), 404)

course = check(
    "create course",
    client.post("/courses", headers=auth, json={"code": f"CS{suffix}", "name": "Intro to Python", "description": "Basics", "credits": 4}),
    201,
).json()
check("create course duplicate", client.post("/courses", headers=auth, json={"code": f"cs{suffix}", "name": "Other"}), 409)
check("list courses", client.get("/courses", headers=auth), 200)
check("get course", client.get(f"/courses/{course['id']}", headers=auth), 200)
check("update course", client.put(f"/courses/{course['id']}", headers=auth, json={"name": "Python Fundamentals"}), 200)
check("enroll student", client.post(f"/courses/{course['id']}/students", headers=auth, json={"student_id": student["id"]}), 201)
check("enroll duplicate", client.post(f"/courses/{course['id']}/students", headers=auth, json={"student_id": student["id"]}), 409)
check("enroll unknown student", client.post(f"/courses/{course['id']}/students", headers=auth, json={"student_id": 999999}), 404)
enrolled = check("list enrolled students", client.get(f"/courses/{course['id']}/students", headers=auth), 200).json()
assert enrolled["total"] == 1 and enrolled["students"][0]["id"] == student["id"]
check("unenroll student", client.delete(f"/courses/{course['id']}/students/{student['id']}", headers=auth), 204)
check("delete course", client.delete(f"/courses/{course['id']}", headers=auth), 204)
check("delete student", client.delete(f"/students/{student['id']}", headers=auth), 204)
check("get deleted student", client.get(f"/students/{student['id']}", headers=auth), 404)

print(f"\nAll {passed} checks passed.")
