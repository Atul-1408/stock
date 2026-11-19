import React from "react";
import { Link } from "react-router-dom";
import { useSeo } from "../utils/seo";

export default function NotFoundPage() {
  useSeo({ title: "Page not found", description: "This page does not exist.", noindex: true });
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-[#070b12] px-6 text-center text-slate-100">
      <h1 className="text-5xl font-extrabold">404</h1>
      <p className="mt-4 text-slate-300">We could not find that page.</p>
      <Link to="/" className="mt-8 rounded-xl bg-blue-600 px-6 py-3 font-semibold hover:bg-blue-500">Go to home page</Link>
    </main>
  );
}
