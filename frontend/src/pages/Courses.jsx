import { useEffect, useState } from "react";
import Alert from "../components/Alert.jsx";
import api, { getErrorMessage } from "../services/api.js";

const EMPTY = { code: "", name: "", description: "", credits: 3 };

export default function Courses() {
  const [courses, setCourses] = useState([]);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [formErrors, setFormErrors] = useState({});
  const [formApiError, setFormApiError] = useState("");

  const [selected, setSelected] = useState(null); // course whose enrolled students are shown
  const [enrolled, setEnrolled] = useState([]);
  const [studentToAssign, setStudentToAssign] = useState("");
  const [panelError, setPanelError] = useState("");

  const loadCourses = () =>
    api
      .get("/courses")
      .then((res) => setCourses(res.data))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));

  useEffect(() => {
    loadCourses();
    api.get("/students").then((res) => setStudents(res.data)).catch(() => {});
  }, []);

  const handleChange = (e) => {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
    setFormErrors((errs) => ({ ...errs, [e.target.name]: undefined }));
  };

  const resetForm = () => {
    setForm(EMPTY);
    setEditingId(null);
    setFormErrors({});
    setFormApiError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const found = {};
    if (form.code.trim().length < 2) found.code = "Code must be at least 2 characters";
    if (form.name.trim().length < 2) found.name = "Name must be at least 2 characters";
    const credits = Number(form.credits);
    if (!Number.isInteger(credits) || credits < 1 || credits > 10) found.credits = "Credits must be between 1 and 10";
    setFormErrors(found);
    if (Object.keys(found).length > 0) return;

    const payload = {
      code: form.code.trim(),
      name: form.name.trim(),
      description: form.description.trim() || null,
      credits,
    };
    setFormApiError("");
    setNotice("");
    try {
      if (editingId) await api.put(`/courses/${editingId}`, payload);
      else await api.post("/courses", payload);
      setNotice(editingId ? "Course updated." : "Course created.");
      resetForm();
      loadCourses();
    } catch (err) {
      setFormApiError(getErrorMessage(err));
    }
  };

  const startEdit = (course) => {
    setEditingId(course.id);
    setForm({ code: course.code, name: course.name, description: course.description || "", credits: course.credits });
    setFormErrors({});
    setFormApiError("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleDelete = async (course) => {
    if (!window.confirm(`Delete course ${course.code}? Its enrollments will be removed too.`)) return;
    setError("");
    setNotice("");
    try {
      await api.delete(`/courses/${course.id}`);
      if (selected?.id === course.id) setSelected(null);
      if (editingId === course.id) resetForm();
      setNotice(`Course ${course.code} was deleted.`);
      loadCourses();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const loadEnrolled = async (course) => {
    setPanelError("");
    try {
      const res = await api.get(`/courses/${course.id}/students`);
      setEnrolled(res.data.students);
    } catch (err) {
      setEnrolled([]);
      setPanelError(getErrorMessage(err));
    }
  };

  const openStudents = (course) => {
    setSelected(course);
    setStudentToAssign("");
    loadEnrolled(course);
  };

  const handleAssign = async (e) => {
    e.preventDefault();
    if (!studentToAssign) {
      setPanelError("Choose a student to assign");
      return;
    }
    setPanelError("");
    try {
      await api.post(`/courses/${selected.id}/students`, { student_id: Number(studentToAssign) });
      setStudentToAssign("");
      loadEnrolled(selected);
    } catch (err) {
      setPanelError(getErrorMessage(err));
    }
  };

  const handleUnassign = async (student) => {
    setPanelError("");
    try {
      await api.delete(`/courses/${selected.id}/students/${student.id}`);
      loadEnrolled(selected);
    } catch (err) {
      setPanelError(getErrorMessage(err));
    }
  };

  const enrolledIds = new Set(enrolled.map((s) => s.id));
  const assignable = students.filter((s) => !enrolledIds.has(s.id));

  return (
    <>
      <h1>Courses</h1>
      <Alert message={error} />
      <Alert type="success" message={notice} />

      <form onSubmit={handleSubmit} noValidate className="card form inline-form">
        <h2>{editingId ? "Edit course" : "Add course"}</h2>
        <Alert message={formApiError} />
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="code">Code</label>
            <input id="code" name="code" value={form.code} onChange={handleChange} placeholder="CS101" />
            {formErrors.code && <span className="field-error">{formErrors.code}</span>}
          </div>
          <div className="form-group grow">
            <label htmlFor="name">Name</label>
            <input id="name" name="name" value={form.name} onChange={handleChange} placeholder="Intro to Python" />
            {formErrors.name && <span className="field-error">{formErrors.name}</span>}
          </div>
          <div className="form-group">
            <label htmlFor="credits">Credits</label>
            <input id="credits" name="credits" type="number" min="1" max="10" value={form.credits} onChange={handleChange} />
            {formErrors.credits && <span className="field-error">{formErrors.credits}</span>}
          </div>
        </div>
        <div className="form-group">
          <label htmlFor="description">Description</label>
          <input id="description" name="description" value={form.description} onChange={handleChange} placeholder="Optional" />
        </div>
        <div className="actions">
          <button className="btn" type="submit">{editingId ? "Save changes" : "Add course"}</button>
          {editingId && (
            <button className="btn btn-outline" type="button" onClick={resetForm}>Cancel</button>
          )}
        </div>
      </form>

      <div className="card table-wrap">
        {loading ? (
          <p className="muted pad">Loading courses...</p>
        ) : courses.length === 0 ? (
          <p className="muted pad">No courses yet. Add the first one above.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Credits</th>
                <th>Description</th>
                <th className="actions-col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {courses.map((c) => (
                <tr key={c.id} className={selected?.id === c.id ? "row-selected" : ""}>
                  <td>{c.code}</td>
                  <td>{c.name}</td>
                  <td>{c.credits}</td>
                  <td>{c.description}</td>
                  <td className="actions">
                    <button className="btn btn-outline btn-small" onClick={() => openStudents(c)}>Students</button>
                    <button className="btn btn-outline btn-small" onClick={() => startEdit(c)}>Edit</button>
                    <button className="btn btn-danger btn-small" onClick={() => handleDelete(c)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selected && (
        <div className="card panel">
          <div className="page-header">
            <h2>
              Students in {selected.code} - {selected.name}
            </h2>
            <button className="btn btn-outline btn-small" onClick={() => setSelected(null)}>Close</button>
          </div>
          <Alert message={panelError} />
          <form onSubmit={handleAssign} className="assign-form">
            <select value={studentToAssign} onChange={(e) => setStudentToAssign(e.target.value)} aria-label="Student to assign">
              <option value="">Select a student to assign...</option>
              {assignable.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.email})
                </option>
              ))}
            </select>
            <button className="btn" type="submit">Assign</button>
          </form>
          {enrolled.length === 0 ? (
            <p className="muted">No students are enrolled in this course yet.</p>
          ) : (
            <ul className="enrolled-list">
              {enrolled.map((s) => (
                <li key={s.id}>
                  <span>
                    <strong>{s.name}</strong> <span className="muted">{s.email}</span>
                  </span>
                  <button className="btn btn-danger btn-small" onClick={() => handleUnassign(s)}>Remove</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </>
  );
}
