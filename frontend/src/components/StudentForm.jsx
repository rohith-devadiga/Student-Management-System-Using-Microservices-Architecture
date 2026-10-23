import { useState } from "react";
import Alert from "./Alert.jsx";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^\+?[0-9][0-9\- ]{6,18}$/;

const EMPTY = { name: "", email: "", phone: "", department: "", course: "" };

function validate(values) {
  const errors = {};
  if (values.name.trim().length < 2) errors.name = "Name must be at least 2 characters";
  if (!EMAIL_RE.test(values.email.trim())) errors.email = "Enter a valid email address";
  if (!PHONE_RE.test(values.phone.trim())) errors.phone = "Enter a valid phone number (7-15 digits, optional +)";
  if (values.department.trim().length < 2) errors.department = "Department is required";
  if (values.course.trim().length < 2) errors.course = "Course is required";
  return errors;
}

export default function StudentForm({ initialValues, courses = [], onSubmit, submitLabel, apiError }) {
  const [values, setValues] = useState({ ...EMPTY, ...initialValues });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (e) => {
    setValues((v) => ({ ...v, [e.target.name]: e.target.value }));
    setErrors((errs) => ({ ...errs, [e.target.name]: undefined }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const found = validate(values);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setSubmitting(true);
    try {
      await onSubmit({
        name: values.name.trim(),
        email: values.email.trim(),
        phone: values.phone.trim(),
        department: values.department.trim(),
        course: values.course.trim(),
      });
    } finally {
      setSubmitting(false);
    }
  };

  const field = (name, label, props = {}) => (
    <div className="form-group">
      <label htmlFor={name}>{label}</label>
      <input id={name} name={name} value={values[name]} onChange={handleChange} {...props} />
      {errors[name] && <span className="field-error">{errors[name]}</span>}
    </div>
  );

  return (
    <form onSubmit={handleSubmit} noValidate className="card form">
      <Alert message={apiError} />
      {field("name", "Full name", { placeholder: "Asha Rao" })}
      {field("email", "Email", { type: "email", placeholder: "asha@example.com" })}
      {field("phone", "Phone number", { placeholder: "+91 98765 43210" })}
      {field("department", "Department", { placeholder: "Computer Science" })}
      {field("course", "Course", { placeholder: "Select or type a course", list: "course-options" })}
      <datalist id="course-options">
        {courses.map((c) => (
          <option key={c.id} value={c.name} />
        ))}
      </datalist>
      <button className="btn" type="submit" disabled={submitting}>
        {submitting ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}
