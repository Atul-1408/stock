import { Github, Globe } from "lucide-react";

function Footer() {
    return (
        <footer className="mt-20 py-10 border-t border-slate-200/60 dark:border-slate-800/60 bg-slate-50/50 dark:bg-slate-900/10 transition-colors duration-400">
            <div className="max-w-7xl mx-auto px-4 md:px-8 flex flex-col items-center gap-6">
                <div className="text-center">
                    <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100 flex items-center justify-center gap-2">
                        Stock Sentiment Dashboard
                    </h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                        Built for university final year project &bull; 2025
                    </p>
                </div>
            </div>
        </footer>
    );
}

export default Footer;
