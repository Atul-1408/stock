import React, { useState, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Menu,
  Bell,
  HelpCircle,
  ChevronDown,
  User,
  LogOut,
  Wallet,
  Search,
  X,
  ShieldCheck,
  ShieldAlert,
  Moon,
  Sun,
} from "lucide-react";
import api from "../../utils/api";
import CurrencySelector from "../CurrencySelector";
import { useCurrency } from "../../contexts/CurrencyContext";
import { formatCurrency } from "../../utils/currency";

const ROUTE_LABELS = {
  "/dashboard": { desk: "DESK", label: "MARKET OVERVIEW" },
  "/market": { desk: "DESK", label: "TRADE TERMINAL" },
  "/analytics": { desk: "DESK", label: "PORTFOLIO & RISK" },
  "/bot": { desk: "ALGO", label: "AUTONOMOUS TRADING BOT" },
  "/alerts": { desk: "ALGO", label: "AUTOMATED SIGNALS" },
  "/chat": { desk: "INTEL", label: "NEURAL ASSISTANT" },
  "/leaderboard": { desk: "NETWORK", label: "GLOBAL RANKINGS" },
};

const POPULAR_SYMBOLS = [
  // Cryptocurrencies
  { symbol: "BTC-USD", company_name: "Bitcoin (BTC)", exchange: "CRYPTO" },
  { symbol: "ETH-USD", company_name: "Ethereum (ETH)", exchange: "CRYPTO" },
  { symbol: "SOL-USD", company_name: "Solana (SOL)", exchange: "CRYPTO" },
  { symbol: "DOGE-USD", company_name: "Dogecoin (DOGE)", exchange: "CRYPTO" },
  { symbol: "BNB-USD", company_name: "Binance Coin (BNB)", exchange: "CRYPTO" },
  { symbol: "XRP-USD", company_name: "XRP / Ripple", exchange: "CRYPTO" },
  { symbol: "ADA-USD", company_name: "Cardano (ADA)", exchange: "CRYPTO" },
  { symbol: "AVAX-USD", company_name: "Avalanche (AVAX)", exchange: "CRYPTO" },
  { symbol: "LINK-USD", company_name: "Chainlink (LINK)", exchange: "CRYPTO" },
  { symbol: "DOT-USD", company_name: "Polkadot (DOT)", exchange: "CRYPTO" },
  { symbol: "MATIC-USD", company_name: "Polygon (MATIC)", exchange: "CRYPTO" },
  { symbol: "LTC-USD", company_name: "Litecoin (LTC)", exchange: "CRYPTO" },
  { symbol: "SHIB-USD", company_name: "Shiba Inu (SHIB)", exchange: "CRYPTO" },

  // Indian Equities (NSE)
  { symbol: "RELIANCE.NS", company_name: "Reliance Industries", exchange: "NSE" },
  { symbol: "TCS.NS", company_name: "Tata Consultancy Services", exchange: "NSE" },
  { symbol: "HDFCBANK.NS", company_name: "HDFC Bank Ltd.", exchange: "NSE" },
  { symbol: "INFY.NS", company_name: "Infosys Ltd.", exchange: "NSE" },
  { symbol: "ICICIBANK.NS", company_name: "ICICI Bank Ltd.", exchange: "NSE" },
  { symbol: "BHARTIARTL.NS", company_name: "Bharti Airtel Ltd.", exchange: "NSE" },
  { symbol: "SBIN.NS", company_name: "State Bank of India", exchange: "NSE" },
  { symbol: "TATAMOTORS.NS", company_name: "Tata Motors Ltd.", exchange: "NSE" },
  { symbol: "TATASTEEL.NS", company_name: "Tata Steel Ltd.", exchange: "NSE" },
  { symbol: "WIPRO.NS", company_name: "Wipro Ltd.", exchange: "NSE" },
  { symbol: "BAJFINANCE.NS", company_name: "Bajaj Finance Ltd.", exchange: "NSE" },
  { symbol: "ADANIENT.NS", company_name: "Adani Enterprises Ltd.", exchange: "NSE" },
  { symbol: "ADANIPORTS.NS", company_name: "Adani Ports & SEZ", exchange: "NSE" },
  { symbol: "ZOMATO.NS", company_name: "Zomato Ltd.", exchange: "NSE" },
  { symbol: "ITC.NS", company_name: "ITC Ltd.", exchange: "NSE" },
  { symbol: "LT.NS", company_name: "Larsen & Toubro Ltd.", exchange: "NSE" },
  { symbol: "KOTAKBANK.NS", company_name: "Kotak Mahindra Bank", exchange: "NSE" },
  { symbol: "MARUTI.NS", company_name: "Maruti Suzuki India", exchange: "NSE" },
  { symbol: "TITAN.NS", company_name: "Titan Company Ltd.", exchange: "NSE" },
  { symbol: "SUNPHARMA.NS", company_name: "Sun Pharmaceutical", exchange: "NSE" },
  { symbol: "HINDUNILVR.NS", company_name: "Hindustan Unilever", exchange: "NSE" },
  { symbol: "NTPC.NS", company_name: "NTPC Ltd.", exchange: "NSE" },
  { symbol: "POWERGRID.NS", company_name: "Power Grid Corp", exchange: "NSE" },

  // US Equities (NASDAQ / NYSE)
  { symbol: "AAPL", company_name: "Apple Inc.", exchange: "NASDAQ" },
  { symbol: "MSFT", company_name: "Microsoft Corporation", exchange: "NASDAQ" },
  { symbol: "NVDA", company_name: "NVIDIA Corporation", exchange: "NASDAQ" },
  { symbol: "GOOGL", company_name: "Alphabet Inc. (Google)", exchange: "NASDAQ" },
  { symbol: "AMZN", company_name: "Amazon.com Inc.", exchange: "NASDAQ" },
  { symbol: "META", company_name: "Meta Platforms Inc.", exchange: "NASDAQ" },
  { symbol: "TSLA", company_name: "Tesla Inc.", exchange: "NASDAQ" },
  { symbol: "NFLX", company_name: "Netflix Inc.", exchange: "NASDAQ" },
  { symbol: "AMD", company_name: "Advanced Micro Devices", exchange: "NASDAQ" },
  { symbol: "ADBE", company_name: "Adobe Inc.", exchange: "NASDAQ" },
  { symbol: "INTC", company_name: "Intel Corporation", exchange: "NASDAQ" },
  { symbol: "CSCO", company_name: "Cisco Systems Inc.", exchange: "NASDAQ" },
  { symbol: "COIN", company_name: "Coinbase Global Inc.", exchange: "NASDAQ" },
  { symbol: "JPM", company_name: "JPMorgan Chase & Co.", exchange: "NYSE" },
  { symbol: "V", company_name: "Visa Inc.", exchange: "NYSE" },
  { symbol: "WMT", company_name: "Walmart Inc.", exchange: "NYSE" },
  { symbol: "DIS", company_name: "Walt Disney Company", exchange: "NYSE" },
  { symbol: "BA", company_name: "Boeing Company", exchange: "NYSE" },
  { symbol: "UBER", company_name: "Uber Technologies", exchange: "NYSE" },
];

export default function TopBar({
  onMobileMenuToggle,
  onOpenNotifications,
  onOpenAbout,
  hasNewNotifs,
  isDark,
  toggleTheme,
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const { currency, formatPrice } = useCurrency();

  const [user, setUser] = useState(null);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const searchRef = useRef(null);
  const inputRef = useRef(null);

  // Fetch authenticated user info
  const fetchUser = async () => {
    try {
      const res = await api.get("/auth/me");
      if (res.data?.user) {
        setUser(res.data.user);
      }
    } catch (err) {}
  };

  useEffect(() => {
    fetchUser();
  }, []);

  // Keyboard shortcut Ctrl+K / Cmd+K
  useEffect(() => {
    const handleGlobalKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
        setIsSearching(true);
      }
    };
    window.addEventListener("keydown", handleGlobalKeyDown);
    return () => window.removeEventListener("keydown", handleGlobalKeyDown);
  }, []);

  // Close menus on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false);
      }
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setIsSearching(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Quick symbol search with instant local fallback
  useEffect(() => {
    const q = searchQuery.trim().toUpperCase();
    if (!q) {
      setSearchResults([]);
      return;
    }

    const localMatches = POPULAR_SYMBOLS.filter((s) => {
      const sym = s.symbol.toUpperCase();
      const baseSym = sym.replace("-USD", "").replace(".NS", "");
      const name = s.company_name.toUpperCase();
      const ex = (s.exchange || "").toUpperCase();
      return (
        sym.includes(q) ||
        baseSym.includes(q) ||
        name.includes(q) ||
        (q === "CRYPTO" && ex === "CRYPTO") ||
        (q === "NSE" && ex === "NSE") ||
        (q === "NASDAQ" && ex === "NASDAQ") ||
        (q === "US" && (ex === "NASDAQ" || ex === "NYSE")) ||
        (q === "INDIA" && ex === "NSE")
      );
    });

    const timeout = setTimeout(async () => {
      try {
        const res = await api.get(`/stocks/search?q=${encodeURIComponent(q)}&limit=6`);
        if (res.data?.results && res.data.results.length > 0) {
          setSearchResults(res.data.results);
        } else {
          setSearchResults(localMatches);
        }
      } catch (err) {
        setSearchResults(localMatches);
      }
    }, 150);
    return () => clearTimeout(timeout);
  }, [searchQuery]);

  const handleSelectSymbol = (sym) => {
    const cleanSym = (sym || "").trim().toUpperCase();
    if (!cleanSym) return;
    setSearchQuery("");
    setIsSearching(false);
    navigate(`/dashboard?symbol=${encodeURIComponent(cleanSym)}`);
  };

  const handleSubmitSearch = (e) => {
    if (e) e.preventDefault();
    const query = searchQuery.trim().toUpperCase();
    if (query) {
      handleSelectSymbol(query);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user_id");
    navigate("/login", { replace: true });
  };

  const routeInfo = ROUTE_LABELS[location.pathname] || { desk: "TERMINAL", label: "VIEW" };
  const initials = (user?.username?.[0] || user?.email?.[0] || "U").toUpperCase();

  return (
    <header
      style={{ top: "32px" }}
      className="h-14 bg-[#070b12] border-b border-white/10 px-3 md:px-5 flex items-center justify-between sticky top-8 z-30 select-none"
    >
      {/* Left: Mobile Toggle & Breadcrumb Tag */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMobileMenuToggle}
          aria-label="Open mobile navigation menu"
          className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:outline-none transition-colors"
          title="Open Menu"
        >
          <Menu size={18} />
        </button>

        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="hidden sm:inline-block px-1.5 py-0.5 rounded bg-white/5 text-slate-400 font-semibold border border-white/5">
            {routeInfo.desk}
          </span>
          <span className="hidden sm:inline-block text-slate-600">//</span>
          <span className="text-white font-bold tracking-wider">{routeInfo.label}</span>
        </div>
      </div>

      {/* Center: Global Symbol Search */}
      <div className="relative hidden md:block w-64 lg:w-80" ref={searchRef}>
        <form onSubmit={handleSubmitSearch} className="relative">
          <button
            type="submit"
            aria-label="Search symbol"
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-cyan-400 focus:outline-none transition-colors"
          >
            <Search className="w-3.5 h-3.5" />
          </button>
          <input
            ref={inputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setIsSearching(true);
            }}
            onFocus={() => setIsSearching(true)}
            placeholder="Search ticker, company... (Ctrl+K)"
            className="w-full bg-[#0d1424] border border-white/10 rounded-lg py-1.5 pl-8 pr-16 text-xs text-slate-200 placeholder-slate-500 font-mono focus:outline-none focus:border-cyan-500/50 transition-colors"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery("");
                setSearchResults([]);
              }}
              className="absolute right-10 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 p-0.5"
              aria-label="Clear search"
            >
              <X className="w-3 h-3" />
            </button>
          )}
          <button
            type="submit"
            aria-label="Submit search"
            className="absolute right-1.5 top-1/2 -translate-y-1/2 px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 font-mono text-[10px] font-bold border border-cyan-500/30 transition-colors"
          >
            GO
          </button>
        </form>

        {/* Search Results Dropdown */}
        {isSearching && searchResults.length > 0 && (
          <div className="absolute left-0 right-0 top-full mt-1.5 bg-[#0c1322] border border-white/10 rounded-lg shadow-xl shadow-black/50 py-1 z-50 overflow-hidden">
            {searchResults.map((item) => (
              <button
                key={item.symbol}
                onClick={() => handleSelectSymbol(item.symbol)}
                className="w-full px-3 py-1.5 text-left text-xs hover:bg-white/5 flex items-center justify-between transition-colors font-mono"
              >
                <div>
                  <span className="font-bold text-white mr-2">{item.symbol}</span>
                  <span className="text-slate-400 text-[11px] truncate">{item.company_name}</span>
                </div>
                <span className="text-[10px] text-cyan-400 bg-cyan-500/10 px-1 py-0.5 rounded">
                  {item.exchange}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right: Currency, Paper Cash, Notifications, User Menu */}
      <div className="flex items-center gap-2 md:gap-3">
        {/* Currency Selector */}
        <div className="hidden sm:block">
          <CurrencySelector />
        </div>

        {/* Environment Indicator */}
        <div className="hidden md:flex items-center gap-1.5 px-2 py-1 rounded-lg text-[10px] font-mono font-semibold tracking-wider uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20" title="Trading environment: Paper Simulation (Safety Enforced)">
          <ShieldAlert size={12} className="text-amber-400" />
          <span>PAPER SIMULATION</span>
        </div>

        {/* Paper Balance Pill */}
        {user?.current_balance != null && (
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono">
            <Wallet size={13} className="text-emerald-400" />
            <span className="text-slate-400 text-[10px] uppercase">CASH:</span>
            <span className="font-bold text-emerald-400">
              {formatPrice(user.current_balance, 'USD')}
            </span>
          </div>
        )}

        {/* Notification Bell */}
        <button
          onClick={onOpenNotifications}
          aria-label="Alerts and notifications"
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:outline-none transition-colors relative"
          title="Alerts & Notifications"
        >
          <Bell size={16} />
          {hasNewNotifs && (
            <span className="absolute top-1 right-1 w-2 h-2 bg-coral-500 rounded-full animate-ping" />
          )}
        </button>

        {/* Help / About Modal Trigger */}
        <button
          onClick={onOpenAbout}
          aria-label="Terminal architecture and about system"
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:outline-none transition-colors"
          title="Terminal Architecture & About"
        >
          <HelpCircle size={16} />
        </button>

        {/* User Menu Dropdown */}
        <div className="relative" ref={userMenuRef}>
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            aria-label="User account menu"
            className="flex items-center gap-1.5 p-1 pl-1.5 pr-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:outline-none transition-colors"
          >
            <div className="w-6 h-6 rounded-md bg-cyan-500/20 text-cyan-400 font-mono text-xs font-bold flex items-center justify-center">
              {initials}
            </div>
            <ChevronDown size={13} className="text-slate-400" />
          </button>

          {userMenuOpen && (
            <div className="absolute right-0 top-full mt-1.5 w-56 bg-[#0c1322] border border-white/10 rounded-lg shadow-xl shadow-black/60 py-1 z-50 overflow-hidden font-mono text-xs">
              <div className="px-3 py-2 border-b border-white/10">
                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">OPERATOR</p>
                <p className="font-bold text-white truncate">{user?.username || user?.email}</p>
                {user?.current_balance != null && (
                  <p className="text-emerald-400 text-[11px] mt-0.5">
                    {formatPrice(user.current_balance, 'USD')}
                  </p>
                )}
              </div>

              <button
                onClick={() => {
                  setUserMenuOpen(false);
                  navigate("/analytics");
                }}
                className="w-full px-3 py-2 text-left text-slate-300 hover:bg-white/5 flex items-center gap-2"
              >
                <User size={14} className="text-slate-400" />
                <span>My Portfolio</span>
              </button>

              <div className="border-t border-white/10 my-1" />

              <button
                onClick={handleLogout}
                className="w-full px-3 py-2 text-left text-coral-400 hover:bg-coral-500/10 flex items-center gap-2 font-bold"
              >
                <LogOut size={14} />
                <span>Disconnect</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
