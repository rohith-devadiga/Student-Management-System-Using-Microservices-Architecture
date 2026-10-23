import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Alert from "../components/Alert.jsx";
import api, { getErrorMessage } from "../services/api.js";

export default function Students() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    api
      .get("/students")
      .then((res) => setStudents(res.data))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = async (student) => {
    if (!window.confirm(`Delete ${student.name}? This cannot be undone.`)) return;
    setError("");
    setNotice("");
    try {
      await api.delete(`/students/${student.id}`);
      setStudents((list) => list.filter((s) => s.id !== student.id));
      setNotice(`${student.name} was deleted.`);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return students;
    return students.filter((s) =>
      [s.name, s.email, s.department, s.course].some((v) => v.toLowerCase().includes(q))
    );
  }, [students, search]);

  return (
    <>
      <div className="page-header">
        <h1>Students</h1>
        <Link to="/students/new" className="btn">Add student</Link>
      </div>
      <Alert message={error} />
      <Alert type="success" message={notice} />
      <input
        className="search"
        placeholder="Search by name, email, department or course"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <div className="card table-wrap">
        {loading ? (
          <p className="muted pad">Loading students...</p>
        ) : filtered.length === 0 ? (
          <p className="muted pad">{students.length === 0 ? "No students yet. Add the first one." : "No students match your search."}</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Department</th>
                <th>Course</th>
                <th className="actions-col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr key={s.id}>
                  <td>{s.id}</td>
                  <td>{s.name}</td>
                  <td>{s.email}</td>
                  <td>{s.phone}</td>
                  <td>{s.department}</td>
                  <td>{s.course}</td>
                  <td className="actions">
                    <Link to={`/students/${s.id}/edit`} className="btn btn-outline btn-small">Edit</Link>
                    <button className="btn btn-danger btn-small" onClick={() => handleDelete(s)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}