import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import client from "../../api/client";
import { Wrench, AlertCircle, Loader2 } from "lucide-react";

export default function TechLogin() {
  const navigate = useNavigate();
  const { loginTech } = useAuth();
  const [phone, setPhone] = useState("");
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await client.post("/auth/technician/login", { phone_number: phone, pin });
      loginTech(res.data.access_token, { phone_number: phone, name: res.data.name });
      navigate("/tech/tickets");
    } catch (err) {
      setError(err.response?.data?.detail || "Invalid phone or PIN.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-svh bg-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="rounded-2xl bg-white shadow-2xl overflow-hidden">
          {/* Brand header */}
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 px-8 py-8 text-center">
            <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-500">
              <Wrench size={28} className="text-white" />
            </div>
            <h1 className="text-lg font-bold text-white">West End Glass</h1>
            <p className="mt-1 text-xs text-slate-400">Field Engineer Portal</p>
          </div>

          <form onSubmit={handleSubmit} className="px-8 py-7 space-y-5">
            <div>
              <label className="mb-1.5 block text-xs font-semibold text-slate-700">Phone Number</label>
              <input
                type="tel"
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-center text-lg tracking-wider focus:border-blue-500 focus:outline-none"
                placeholder="+44 7700 000000"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold text-slate-700">PIN</label>
              <input
                type="password"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={8}
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-center text-2xl tracking-widest focus:border-blue-500 focus:outline-none"
                placeholder="••••"
                value={pin}
                onChange={(e) => setPin(e.target.value.replace(/[^0-9]/g, ""))}
                required
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
                <AlertCircle size={16} className="flex-shrink-0" />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-3 text-base font-bold text-white hover:bg-blue-700 disabled:opacity-60 transition-colors"
            >
              {loading && <Loader2 size={18} className="animate-spin" />}
              {loading ? "Signing in…" : "Sign In"}
            </button>

            <p className="text-center text-xs text-slate-400">
              Contact your dispatcher if you need a PIN set up.
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
