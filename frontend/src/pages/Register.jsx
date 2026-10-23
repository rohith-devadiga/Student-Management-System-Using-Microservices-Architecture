import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import Alert from "../components/Alert.jsx";
import { getErrorMessage } from "../services/api.js";
import { useAuth } from "../services/AuthContext.jsx";

export default function Register() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", email: "", password: "", confirm: "" });
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const handleChange = (e) => {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
    setErrors((errs) => ({ ...errs, [e.target.name]: undefined }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const found = {};
    if (form.username.trim().length < 3) found.username = "Username must be at least 3 characters";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) found.email = "Enter a valid email address";
    if (form.password.length < 6) found.password = "Password must be at least 6 characters";
    if (form.password !== form.confirm) found.confirm = "Passwords do not match";
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setLoading(true);
    setApiError("");
    try {
      await register(form.username.trim(), form.email.trim(), form.password);
      navigate("/login", { replace: true, state: { registered: true } });
    } catch (err) {
      setApiError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const field = (name, label, props = {}) => (
    <div className="form-group">
      <label htmlFor={name}>{label}</label>
      <input id={name} name={name} value={form[name]} onChange={handleChange} {...props} />
      {errors[name] && <span className="field-error">{errors[name]}</span>}
    </div>
  );

  return (
    <div className="auth-wrapper">
      <form onSubmit={handleSubmit} noValidate className="card form">
        <h1>Create account</h1>
        <Alert message={apiError} />
        {field("username", "Username", { autoComplete: "username" })}
        {field("email", "Email", { type: "email", autoComplete: "email" })}
        {field("password", "Password", { type: "password", autoComplete: "new-password" })}
        {field("confirm", "Confirm password", { type: "password", autoComplete: "new-password" })}
        <button className="btn" type="submit" disabled={loading}>
          {loading ? "Creating..." : "Register"}
        </button>
        <p className="muted">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
