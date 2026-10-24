import React, { useState, useEffect, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { 
  Activity, 
  Mail, 
  Lock, 
  AlertCircle, 
  ArrowRight, 
  KeyRound, 
  Loader2, 
  CheckCircle2, 
  ShieldCheck,
  Terminal
} from "lucide-react";
import api from "../utils/api";
import { initGSI, renderGSIButton } from "../utils/gsi";

const LoginPage = () => {
  const [activeTab, setActiveTab] = useState("password"); // 'password' | 'otp'
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const navigate = useNavigate();
  const googleBtnRef = useRef(null);

  // Google Sign-In initialization
  useEffect(() => {
    const loadGoogle = () => {
      if (initGSI(handleGoogleResponse)) {
        renderGSIButton(googleBtnRef.current, { text: "continue_with" });
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

  // Countdown timer for resend OTP
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  const handleGoogleResponse = async (response) => {
    setError("");
    setLoading(true);
    try {
      const res = await api.post("/auth/google", { credential: response.credential });
      localStorage.setItem("token", res.data.access_token);
      localStorage.setItem("user_id", res.data.user_id);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.message || "Google authentication rejected.");
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const response = await api.post("/auth/login", { email, password });
      localStorage.setItem("token", response.data.access_token);
      localStorage.setItem("user_id", response.data.user_id);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.message || "Access denied. Check credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleSendOtp = async () => {
    if (!email) {
      setError("Please specify registered operator email.");
      return;
    }
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      await api.post("/auth/otp/send", { email });
      setOtpSent(true);
      setCountdown(60);
      setSuccess("One-time security token dispatched to email.");
    } catch (err) {
      setError(err.response?.data?.message || "Failed to dispatch security OTP.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    if (otp.length !== 6) return;
    setError("");
    setLoading(true);
    try {
      const response = await api.post("/auth/otp/verify", { email, otp });
      localStorage.setItem("token", response.data.access_token);
      localStorage.setItem("user_id", response.data.user_id);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.message || "Invalid or expired security code.");
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: "password", label: "Password Key", icon: <Lock className="w-3.5 h-3.5" /> },
    { id: "otp", label: "OTP Token", icon: <KeyRound className="w-3.5 h-3.5" /> }
  ];

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
            Institutional Financial Terminal &bull; Access Gate
          </p>
        </div>

        {/* Auth Panel */}
        <div className="terminal-card bg-[#0c1322] border-terminal-800 shadow-2xl p-6">
          {/* Google Sign-In */}
          <div className="mb-5">
            <div ref={googleBtnRef} className="flex justify-center [&>div]:!w-full" />
          </div>

          {/* Divider */}
          <div className="flex items-center gap-3 mb-5">
            <div className="flex-1 h-px bg-terminal-800" />
            <span className="font-mono text-2xs uppercase tracking-widest text-slate-400">OR DIRECT PROTOCOL</span>
            <div className="flex-1 h-px bg-terminal-800" />
          </div>

          {/* Auth Tab Switcher */}
          <div className="flex bg-terminal-950 p-1 rounded border border-terminal-800 mb-5">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  setError("");
                  setSuccess("");
                  setOtpSent(false);
                  setOtp("");
                }}
                className={`flex-1 flex items-center justify-center gap-2 py-2 rounded font-mono text-xs uppercase tracking-wider transition-all ${
                  activeTab === tab.id
                    ? "bg-terminal-cyan/15 text-terminal-cyan font-bold border border-terminal-cyan/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {/* Error & Success Banners */}
          {error && (
            <div className="flex items-center gap-2.5 p-3 rounded bg-terminal-coral/10 border border-terminal-coral/30 text-terminal-coral font-mono text-xs mb-4">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="flex items-center gap-2.5 p-3 rounded bg-terminal-emerald/10 border border-terminal-emerald/30 text-terminal-emerald font-mono text-xs mb-4">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{success}</span>
            </div>
          )}

          {/* Password Mode */}
          {activeTab === "password" && (
            <form onSubmit={handlePasswordLogin} className="space-y-4">
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
                  Secure Passkey
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
                    <span>Authenticate Session</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* OTP Mode */}
          {activeTab === "otp" && (
            <form onSubmit={handleVerifyOtp} className="space-y-4">
              <div>
                <label className="block font-mono text-2xs uppercase tracking-wider text-slate-300 mb-1.5">
                  Registered Operator Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={otpSent}
                    required
                    placeholder="operator@desk.internal"
                    className="w-full bg-terminal-950 border border-terminal-700 rounded py-2.5 pl-10 pr-3 font-mono text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-terminal-cyan disabled:opacity-50"
                  />
                </div>
              </div>

              {!otpSent ? (
                <button
                  type="button"
                  onClick={handleSendOtp}
                  disabled={loading || !email}
                  className="w-full py-2.5 rounded bg-terminal-cyan/15 border border-terminal-cyan/40 hover:bg-terminal-cyan/25 text-terminal-cyan font-mono text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Mail className="w-4 h-4" />
                      <span>Dispatch OTP Token</span>
                    </>
                  )}
                </button>
              ) : (
                <>
                  <div>
                    <label className="block font-mono text-2xs uppercase tracking-wider text-slate-300 mb-1.5 text-center">
                      Enter 6-Digit Verification Token
                    </label>
                    <div className="relative">
                      <KeyRound className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                      <input
                        type="text"
                        value={otp}
                        onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                        placeholder="••••••"
                        maxLength={6}
                        autoFocus
                        required
                        className="w-full bg-terminal-950 border border-terminal-700 rounded py-2.5 pl-10 pr-3 font-mono text-center text-lg tracking-[0.4em] text-slate-100 focus:outline-none focus:border-terminal-cyan"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading || otp.length !== 6}
                    className="w-full py-2.5 rounded bg-terminal-cyan/15 border border-terminal-cyan/40 hover:bg-terminal-cyan/25 text-terminal-cyan font-mono text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <span>Verify & Enter Desk</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>

                  <div className="flex items-center justify-between font-mono text-2xs pt-1">
                    <button
                      type="button"
                      onClick={() => {
                        setOtpSent(false);
                        setOtp("");
                        setSuccess("");
                      }}
                      className="text-slate-400 hover:text-slate-200 uppercase"
                    >
                      Use Different Email
                    </button>
                    <button
                      type="button"
                      onClick={handleSendOtp}
                      disabled={countdown > 0 || loading}
                      className="text-terminal-cyan hover:underline uppercase disabled:text-slate-600 disabled:no-underline"
                    >
                      {countdown > 0 ? `Resend (${countdown}s)` : "Resend Token"}
                    </button>
                  </div>
                </>
              )}
            </form>
          )}

          {/* Footer Link */}
          <div className="mt-6 pt-4 border-t border-terminal-800 text-center font-mono text-xs text-slate-400">
            Unregistered operator?{" "}
            <Link to="/signup" className="text-terminal-cyan hover:underline uppercase font-bold">
              Enroll Terminal Access &rarr;
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
