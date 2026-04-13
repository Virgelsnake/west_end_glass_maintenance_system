import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { AlertCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch {
      setError("Invalid username or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4" style={{background: '#0d2d52'}}>
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="mb-8 text-center">
          <img src="/logo.png" alt="West End Glass" className="mx-auto mb-4 h-20 w-20 object-contain" />
          <h1 className="text-2xl font-bold text-white">West End Glass</h1>
          <p className="mt-1 text-sm" style={{color: '#7cadd8'}}>Maintenance System — Admin Portal</p>
        </div>

        {/* Card */}
        <div className="rounded-2xl bg-white p-8 shadow-2xl">
          <h2 className="mb-6 text-center text-lg font-semibold text-slate-800">Sign in to your account</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">Username</label>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                placeholder="admin"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoComplete="username"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">Password</label>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-700">
                <AlertCircle size={15} className="flex-shrink-0" />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold text-white transition-colors disabled:opacity-60"
              style={{background: '#ee6300'}}
            >
              {loading && <Loader2 size={15} className="animate-spin" />}
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>
        </div>

        <p className="mt-4 text-center text-xs text-slate-500">
          Field technician?{" "}
          <a href="/tech/login" className="hover:underline" style={{color: '#ee6300'}}>
            Access the field portal →
          </a>
        </p>
        {import.meta.env.VITE_APP_VERSION && (
          <p className="mt-3 text-center" style={{color: 'rgba(255,255,255,0.25)', fontSize: 10, letterSpacing: '0.05em'}}>
            v{import.meta.env.VITE_APP_VERSION.split('+')[0]}
            &nbsp;&middot;&nbsp;
            {import.meta.env.VITE_APP_VERSION.split('+')[1]?.slice(0, 7)}
          </p>
        )}
      </div>
    </div>
  );
}

