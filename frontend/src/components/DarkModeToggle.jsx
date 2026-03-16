import { Moon, Sun } from "lucide-react";
import { motion } from "framer-motion";

function DarkModeToggle({ isDark, toggle }) {
    return (
        <button
            onClick={toggle}
            className="relative flex items-center justify-center p-2 rounded-full bg-slate-100 dark:bg-slate-800/50 hover:bg-slate-200 dark:hover:bg-slate-700/50 border border-slate-200 dark:border-slate-700/50 transition-all shadow-sm"
            title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
        >
            <motion.div
                initial={false}
                animate={{ rotate: isDark ? 0 : 180, scale: isDark ? 1 : 0 }}
                className="absolute"
            >
                <Sun className="w-5 h-5 text-yellow-400" />
            </motion.div>
            <motion.div
                initial={false}
                animate={{ rotate: isDark ? -180 : 0, scale: isDark ? 0 : 1 }}
                className="absolute"
            >
                <Moon className="w-5 h-5 text-indigo-400" />
            </motion.div>
            <div className="w-5 h-5" aria-hidden="true" /> {/* Spacer */}
        </button >
    );
}

export default DarkModeToggle;
