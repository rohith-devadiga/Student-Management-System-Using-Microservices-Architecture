import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Alert from "../components/Alert.jsx";
import api, { getErrorMessage } from "../services/api.js";
import { useAuth } from "../services/AuthContext.jsx";

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([api.get("/students"), api.get("/courses")])
      .then(([students, courses]) => {
        if (active) setStats({ students: students.data.length, courses: courses.data.length });
      })
      .catch((err) => active && setError(getErrorMessage(err)));
    return () => {
      active = false;
    };
  }, []);

  return (
    <>
      <h1>Welcome, {user.username}</h1>
      <Alert message={error} />
      <div className="stat-grid">
        <Link to="/students" className="card stat">
          <span className="stat-value">{stats ? stats.students : "-"}</span>
          <span className="stat-label">Total students</span>
        </Link>
        <Link to="/courses" className="card stat">
          <span className="stat-value">{stats ? stats.courses : "-"}</span>
          <span className="stat-label">Available courses</span>
        </Link>
      </div>
    </>
  );
}
