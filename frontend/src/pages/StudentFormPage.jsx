import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Alert from "../components/Alert.jsx";
import StudentForm from "../components/StudentForm.jsx";
import api, { getErrorMessage } from "../services/api.js";

export default function StudentFormPage() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const [student, setStudent] = useState(null);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(isEdit);
  const [loadError, setLoadError] = useState("");
  const [apiError, setApiError] = useState("");

  useEffect(() => {
    api.get("/courses").then((res) => setCourses(res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!isEdit) return;
    api
      .get(`/students/${id}`)
      .then((res) => setStudent(res.data))
      .catch((err) => setLoadError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id, isEdit]);

  const handleSubmit = async (values) => {
    setApiError("");
    try {
      if (isEdit) await api.put(`/students/${id}`, values);
      else await api.post("/students", values);
      navigate("/students");
    } catch (err) {
      setApiError(getErrorMessage(err));
    }
  };

  return (
    <>
      <div className="page-header">
        <h1>{isEdit ? "Edit student" : "Add student"}</h1>
        <Link to="/students" className="btn btn-outline">Back</Link>
      </div>
      {loading && <p className="muted">Loading...</p>}
      <Alert message={loadError} />
      {!loading && !loadError && (
        <StudentForm
          initialValues={student}
          courses={courses}
          onSubmit={handleSubmit}
          submitLabel={isEdit ? "Save changes" : "Create student"}
          apiError={apiError}
        />
      )}
    </>
  );
}
