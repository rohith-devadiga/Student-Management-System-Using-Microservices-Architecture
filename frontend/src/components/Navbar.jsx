import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../services/AuthContext.jsx";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <span className="brand">Student Management</span>
        {user ? (
          <nav>
            <NavLink to="/" end>Dashboard</NavLink>
            <NavLink to="/students">Students</NavLink>
            <NavLink to="/courses">Courses</NavLink>
            <span className="nav-user">{user.username}</span>
            <button className="btn btn-outline btn-small" onClick={handleLogout}>Logout</button>
          </nav>
        ) : (
          <nav>
            <NavLink to="/login">Login</NavLink>
            <NavLink to="/register">Register</NavLink>
          </nav>
        )}
      </div>
    </header>
  );
}
