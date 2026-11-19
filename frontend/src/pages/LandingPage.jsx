import React from "react";
import { Link } from "react-router-dom";
import { useSeo } from "../utils/seo";

const FEATURES = [
  { title: "News sentiment for every stock", text: "Headlines for NSE-listed and US stocks are scored with VADER and FinBERT so you can see whether the mood is bullish, bearish or neutral." },
  { title: "Paper trading with virtual money", text: "Practise market, limit and stop orders, track your portfolio and profit and loss, and learn without risking real money." },
  { title: "Rule-based AI trading bot", text: "Set risk level, stop-loss, take-profit and trading hours, add a watchlist, and let the bot place simulated trades with built-in risk limits." },
  { title: "AI market assistant", text: "Ask questions about a stock. The assistant is instructed to use only verified data and never to promise returns." },
  { title: "Price alerts", text: "Create alerts on price and sentiment and get notified when a rule triggers." },
  { title: "Portfolio analytics and leaderboard", text: "See sector allocation, risk metrics and history against a benchmark, and compare your results with other traders." },
];

const FAQ = [
  { q: "Is this real money trading?", a: "No. Sovereign Intelligence is a paper-trading platform. All balances and trades are simulated." },
  { q: "Is this financial advice?", a: "No. Sentiment scores, signals and chatbot answers are for education and research only. Markets involve risk." },
  { q: "Which markets are covered?", a: "Stocks listed on India's NSE (symbols ending in .NS) and major US exchanges." },
  { q: "How is sentiment calculated?", a: "Recent news headlines are processed with VADER and, when enabled, the FinBERT financial language model, then combined into a score per stock." },
  { q: "Can I sign in with Google?", a: "Yes. You can use email and password, a one-time email code, or Google sign-in." },
];

const faqJsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: FAQ.map(({ q, a }) => ({ "@type": "Question", name: q, acceptedAnswer: { "@type": "Answer", text: a } })),
};

export default function LandingPage() {
  useSeo({
    title: "AI Stock Sentiment & Paper Trading Platform for NSE and US Stocks",
    description:
      "Practise trading with virtual money. Get AI news sentiment for NSE and US stocks, run a rule-based trading bot, set price alerts and track your portfolio.",
    path: "/",
  });
  const loggedIn = !!localStorage.getItem("token");

  return (
    <div className="min-h-screen bg-[#070b12] text-slate-100">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }} />
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <span className="text-lg font-bold tracking-tight">Sovereign Intelligence</span>
        <nav aria-label="Primary" className="flex items-center gap-4 text-sm">
          <a href="#features" className="hover:text-white text-slate-300">Features</a>
          <a href="#faq" className="hover:text-white text-slate-300">FAQ</a>
          {loggedIn ? (
            <Link to="/dashboard" className="rounded-lg bg-blue-600 px-4 py-2 font-semibold hover:bg-blue-500">Open dashboard</Link>
          ) : (
            <Link to="/login" className="rounded-lg border border-white/20 px-4 py-2 font-semibold hover:bg-white/10">Log in</Link>
          )}
        </nav>
      </header>

      <main>
        <section className="mx-auto max-w-4xl px-6 py-20 text-center">
          <h1 className="text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl">
            AI stock sentiment and paper trading for NSE and US markets
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-300">
            See what the news says about a stock, test your ideas with virtual money, and automate them with a risk-controlled trading bot. No real money involved.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Link to="/signup" className="rounded-xl bg-blue-600 px-6 py-3 font-semibold hover:bg-blue-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-300">
              Create an account
            </Link>
            <Link to="/login" className="rounded-xl border border-white/20 px-6 py-3 font-semibold hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-300">
              Log in
            </Link>
          </div>
        </section>

        <section id="features" aria-labelledby="features-h" className="mx-auto max-w-6xl px-6 py-16">
          <h2 id="features-h" className="text-center text-3xl font-bold">Everything you need to practise trading</h2>
          <ul className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <li key={f.title} className="rounded-2xl border border-white/10 bg-white/5 p-6">
                <h3 className="text-lg font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-300">{f.text}</p>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="how-h" className="mx-auto max-w-4xl px-6 py-16">
          <h2 id="how-h" className="text-center text-3xl font-bold">How it works</h2>
          <ol className="mt-8 space-y-4 text-slate-300">
            <li><strong className="text-white">1. Sign up</strong> with email, a one-time code or Google.</li>
            <li><strong className="text-white">2. Research</strong> a stock: price chart, news and sentiment in one view.</li>
            <li><strong className="text-white">3. Trade</strong> with virtual cash, or switch on the bot with your own risk limits.</li>
            <li><strong className="text-white">4. Review</strong> your analytics, alerts and leaderboard rank.</li>
          </ol>
        </section>

        <section id="faq" aria-labelledby="faq-h" className="mx-auto max-w-3xl px-6 py-16">
          <h2 id="faq-h" className="text-center text-3xl font-bold">Frequently asked questions</h2>
          <dl className="mt-8 space-y-6">
            {FAQ.map(({ q, a }) => (
              <div key={q}>
                <dt className="font-semibold">{q}</dt>
                <dd className="mt-1 text-slate-300">{a}</dd>
              </div>
            ))}
          </dl>
        </section>
      </main>

      <footer className="border-t border-white/10 px-6 py-8 text-center text-xs text-slate-400">
        <p>Educational paper-trading platform. Not financial advice. Markets involve risk.</p>
        <p className="mt-2">© {new Date().getFullYear()} Sovereign Intelligence</p>
      </footer>
    </div>
  );
}
