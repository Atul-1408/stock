import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Activity, Mail, Lock, AlertCircle, ArrowRight, KeyRound, Smartphone, Loader2, CheckCircle2 } from 'lucide-react';
import api from '../utils/api';
import { initGSI, renderGSIButton } from '../utils/gsi';

const LoginPage = () => {
    const [activeTab, setActiveTab] = useState('password'); // 'password' | 'otp'
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [otp, setOtp] = useState('');
    const [otpSent, setOtpSent] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);
    const [countdown, setCountdown] = useState(0);
    const navigate = useNavigate();
    const googleBtnRef = useRef(null);

    // Google Sign-In initialization
    useEffect(() => {
        const loadGoogle = () => {
            if (initGSI(handleGoogleResponse)) {
                renderGSIButton(googleBtnRef.current, { text: 'continue_with' });
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
        const timer = setTimeout(() => setCountdown(c => c - 1), 1000);
        return () => clearTimeout(timer);
    }, [countdown]);

    const handleGoogleResponse = async (response) => {
        setError('');
        setLoading(true);
        try {
            const res = await api.post('/auth/google', { credential: response.credential });
            localStorage.setItem('token', res.data.access_token);
            localStorage.setItem('user_id', res.data.user_id);
            navigate('/dashboard');
        } catch (err) {
            setError(err.response?.data?.message || 'Google login failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handlePasswordLogin = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            const response = await api.post('/auth/login', { email, password });
            localStorage.setItem('token', response.data.access_token);
            localStorage.setItem('user_id', response.data.user_id);
            navigate('/dashboard');
        } catch (err) {
            setError(err.response?.data?.message || 'Login failed. Please check your credentials.');
        } finally {
            setLoading(false);
        }
    };

    const handleSendOtp = async () => {
        if (!email) {
            setError('Please enter your email address first.');
            return;
        }
        setError('');
        setSuccess('');
        setLoading(true);
        try {
            await api.post('/auth/otp/send', { email });
            setOtpSent(true);
            setCountdown(60);
            setSuccess('OTP sent! Check your email inbox.');
        } catch (err) {
            setError(err.response?.data?.message || 'Failed to send OTP.');
        } finally {
            setLoading(false);
        }
    };

    const handleVerifyOtp = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        setLoading(true);
        try {
            const res = await api.post('/auth/otp/verify', { email, otp });
            localStorage.setItem('token', res.data.access_token);
            localStorage.setItem('user_id', res.data.user_id);
            navigate('/dashboard');
        } catch (err) {
            setError(err.response?.data?.message || 'Invalid or expired OTP.');
        } finally {
            setLoading(false);
        }
    };

    const tabs = [
        { id: 'password', label: 'Password', icon: <Lock className="w-4 h-4" /> },
        { id: 'otp', label: 'Email OTP', icon: <Smartphone className="w-4 h-4" /> },
    ];

    return (
        <div className="min-h-screen bg-[#0A0B10] flex items-center justify-center p-4">
            {/* Background Glow */}
            <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[120px] pointer-events-none" />
            <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[120px] pointer-events-none" />

            <div className="w-full max-w-md relative">
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-500/10 rounded-2xl mb-4 border border-blue-500/20">
                        <Activity className="w-8 h-8 text-blue-500" />
                    </div>
                    <h1 className="text-3xl font-bold text-white mb-2">Sovereign Intelligence</h1>
                    <p className="text-gray-400">Welcome back! Choose your login method.</p>
                </div>

                <div className="bg-white/5 backdrop-blur-xl border border-white/10 p-8 rounded-3xl shadow-2xl">

                    {/* ── Google Sign-In ── */}
                    <div className="mb-6">
                        <div
                            ref={googleBtnRef}
                            className="flex justify-center [&>div]:!w-full"
                        />
                    </div>

                    {/* ── OR Divider ── */}
                    <div className="flex items-center gap-4 mb-6">
                        <div className="flex-1 h-px bg-white/10" />
                        <span className="text-xs font-semibold text-gray-500 uppercase tracking-widest">or</span>
                        <div className="flex-1 h-px bg-white/10" />
                    </div>

                    {/* ── Auth Tabs ── */}
                    <div className="flex bg-white/5 p-1 rounded-xl mb-6">
                        {tabs.map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => { setActiveTab(tab.id); setError(''); setSuccess(''); setOtpSent(false); setOtp(''); }}
                                className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-bold transition-all ${activeTab === tab.id
                                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/25'
                                    : 'text-gray-400 hover:text-gray-200'
                                    }`}
                            >
                                {tab.icon}
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    {/* ── Error / Success ── */}
                    {error && (
                        <div className="flex items-center gap-3 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm mb-4">
                            <AlertCircle className="w-4 h-4 flex-shrink-0" />
                            <p>{error}</p>
                        </div>
                    )}
                    {success && (
                        <div className="flex items-center gap-3 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm mb-4">
                            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                            <p>{success}</p>
                        </div>
                    )}

                    {/* ── Password Tab ── */}
                    {activeTab === 'password' && (
                        <form onSubmit={handlePasswordLogin} className="space-y-5">
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-gray-300 ml-1">Email Address</label>
                                <div className="relative">
                                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                                        placeholder="name@company.com"
                                        required
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium text-gray-300 ml-1">Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                                    <input
                                        type="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                                        placeholder="••••••••"
                                        required
                                    />
                                </div>
                            </div>

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 text-white font-semibold py-3 rounded-xl transition-all flex items-center justify-center gap-2 group"
                            >
                                {loading ? (
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                ) : (
                                    <>
                                        Sign In
                                        <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                                    </>
                                )}
                            </button>
                        </form>
                    )}

                    {/* ── OTP Tab ── */}
                    {activeTab === 'otp' && (
                        <form onSubmit={handleVerifyOtp} className="space-y-5">
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-gray-300 ml-1">Email Address</label>
                                <div className="relative">
                                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                                        placeholder="name@company.com"
                                        required
                                        disabled={otpSent}
                                    />
                                </div>
                            </div>

                            {!otpSent ? (
                                <button
                                    type="button"
                                    onClick={handleSendOtp}
                                    disabled={loading || !email}
                                    className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 disabled:opacity-50 text-white font-semibold py-3 rounded-xl transition-all flex items-center justify-center gap-2"
                                >
                                    {loading ? (
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                    ) : (
                                        <>
                                            <Mail className="w-5 h-5" />
                                            Send OTP to Email
                                        </>
                                    )}
                                </button>
                            ) : (
                                <>
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-gray-300 ml-1">Enter 6-digit OTP</label>
                                        <div className="relative">
                                            <KeyRound className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                                            <input
                                                type="text"
                                                value={otp}
                                                onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                                className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all text-center text-xl tracking-[0.5em] font-mono"
                                                placeholder="••••••"
                                                maxLength={6}
                                                autoFocus
                                                required
                                            />
                                        </div>
                                    </div>

                                    <button
                                        type="submit"
                                        disabled={loading || otp.length !== 6}
                                        className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold py-3 rounded-xl transition-all flex items-center justify-center gap-2 group"
                                    >
                                        {loading ? (
                                            <Loader2 className="w-5 h-5 animate-spin" />
                                        ) : (
                                            <>
                                                Verify & Login
                                                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                                            </>
                                        )}
                                    </button>

                                    <div className="text-center">
                                        <button
                                            type="button"
                                            onClick={() => { setOtpSent(false); setOtp(''); setSuccess(''); }}
                                            className="text-sm text-gray-500 hover:text-gray-300 transition-colors mr-4"
                                        >
                                            Change email
                                        </button>
                                        <button
                                            type="button"
                                            onClick={handleSendOtp}
                                            disabled={countdown > 0 || loading}
                                            className="text-sm text-blue-500 hover:text-blue-400 disabled:text-gray-600 transition-colors font-medium"
                                        >
                                            {countdown > 0 ? `Resend in ${countdown}s` : 'Resend OTP'}
                                        </button>
                                    </div>
                                </>
                            )}
                        </form>
                    )}

                    <p className="text-center mt-8 text-gray-400">
                        Don't have an account?{' '}
                        <Link to="/signup" className="text-blue-500 hover:text-blue-400 font-medium underline underline-offset-4">
                            Sign up for free
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default LoginPage;
