import React, { useState, useEffect, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Activity, Mail, Lock, AlertCircle, ArrowRight, User, Terminal, Loader2 } from "lucide-react";
import api from "../utils/api";
import { initGSI, renderGSIButton } from "../utils/gsi";

const SignupPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const googleBtnRef = useRef(null);

  useEffect(() => {
    const loadGoogle = () => {
      if (initGSI(handleGoogleResponse)) {
        renderGSIButton(googleBtnRef.current, { text: "signup_with" });
      }
    };
    if (window.google?.accounts?.id) {
      loadGoogle();
    } else {
      const interval = setInterval(() => {
        if (window.google?.accounts?.id) {
          loadGoogle();
          clearInterval(interval);
        }
      }, 200);
      return () => clearInterval(interval);
    }
  }, []);

  const handleGoogleResponse = async (response) => {
    setError("");
    setLoading(true);
    try {
      const res = await api.post("/auth/google", { credential: response.credential });
      localStorage.setItem("token", res.data.access_token);
      localStorage.setItem("user_id", res.data.user_id);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.message || "Google onboarding failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await api.post("/auth/signup", {
        email,
        password,
        username,
        full_name: fullName
      });
      localStorage.setItem("token", response.data.access_token);
      localStorage.setItem("user_id", response.data.user_id);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.message || "Registration failed. Verify credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b12] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Terminal Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded border border-terminal-700 bg-terminal-900 text-terminal-cyan mb-3">
            <Terminal className="w-6 h-6" />
          </div>
          <h1 className="font-mono text-lg font-bold text-slate-100 uppercase tracking-widest">
            Sovereign Intelligence
          </h1>
          <p className="font-mono text-2xs uppercase tracking-wider text-slate-400 mt-0.5">
            Institutional Desk Registration &bull; Operator Enrollment
          </p>
        </div>

        <div className="terminal-card bg-[#0c1322] border-terminal-800 shadow-2xl p-6">
          {/* Google Sign-Up */}
          <div className="mb-5">
            <div ref={googleBtnRef} className="flex justify-center [&>div]:!w-full" />
          </div>

          {/* Divider */}
          <div className="flex items-center gap-3 mb-5">
            <div className="flex-1 h-px bg-terminal-800" />
            <span className="font-mono text-2xs uppercase tracking-widest text-slate-400">OR REGISTER PROFILE</span>
            <div className="flex-1 h-px bg-terminal-800" />
          </div>

          <form onSubmit={handleSignup} className="space-y-4">
            {error && (
              <div className="flex items-center gap-2.5 p-3 rounded bg-terminal-coral/10 border border-terminal-coral/30 text-terminal-coral font-mono text-xs">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-mono text-2xs uppercase tracking-wider text-slate-300 mb-1.5">
                  Handle / ID
                </label>
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    placeholder="trader_alpha"
                    className="w-full bg-terminal-950 border border-terminal-700 rounded py-2.5 pl-10 pr-3 font-mono text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-terminal-cyan"
                  />
                </div>
              </div>

              <div>
                <label className="block font-mono text-2xs uppercase tracking-wider text-slate-300 mb-1.5">
                  Full Name
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  placeholder="Alex Mercer"
                  className="w-full bg-terminal-950 border border-terminal-700 rounded py-2.5 px-3 font-mono text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-terminal-cyan"
                />
              </div>
            </div>

            <div>
              <label className="block font-mono text-2xs uppercase tracking-wider text-slate-300 mb-1.5">
                Operator Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="operator@desk.internal"
                  className="w-full bg-terminal-950 border border-terminal-700 rounded py-2.5 pl-10 pr-3 font-mono text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-terminal-cyan"
                />
              </div>
            </div>

            <div>
              <label className="block font-mono text-2xs uppercase tracking-wider text-slate-300 mb-1.5">
                Passkey
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••••••"
                  className="w-full bg-terminal-950 border border-terminal-700 rounded py-2.5 pl-10 pr-3 font-mono text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-terminal-cyan"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2.5 rounded bg-terminal-cyan/15 border border-terminal-cyan/40 hover:bg-terminal-cyan/25 text-terminal-cyan font-mono text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <span>Initialize Account & Portfolio</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-terminal-800 text-center font-mono text-xs text-slate-400">
            Already have an active seat?{" "}
            <Link to="/login" className="text-terminal-cyan hover:underline uppercase font-bold">
              Sign In to Desk &rarr;
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignupPage;
