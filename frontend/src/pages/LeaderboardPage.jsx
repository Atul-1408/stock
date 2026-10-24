import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Trophy, TrendingUp, Users, Target, Activity, ChevronRight, Share2 } from 'lucide-react';
import api from '../utils/api';
import { toast } from 'react-toastify';

const LeaderboardPage = () => {
    const [leaderboard, setLeaderboard] = useState([]);
    const [myRank, setMyRank] = useState(null);
    const [period, setPeriod] = useState('all_time');
    const [loading, setLoading] = useState(true);

    const handleShare = (trader) => {
        const text = `Check out ${trader.username}'s performance on Stock Sense! Return: ${trader.total_return_pct >= 0 ? '+' : ''}${trader.total_return_pct.toFixed(2)}%`;
        if (navigator.share) {
            navigator.share({
                title: 'Stock Sense Leaderboard',
                text: text,
                url: window.location.href
            }).catch(() => {});
        } else {
            navigator.clipboard.writeText(text);
            toast.info("Stats copied to clipboard!");
        }
    };

    const handleViewProfile = () => {
        toast.info("Public profile pages are coming soon in the next update!");
    };

    const fetchLeaderboard = async () => {
        try {
            setLoading(true);
            const [boardRes, rankRes] = await Promise.all([
                api.get(`/leaderboard?period=${period}`),
                api.get('/leaderboard/my-rank')
            ]);
            setLeaderboard(boardRes.data.leaderboard);
            setMyRank(rankRes.data.rank);
        } catch (error) {
            console.error('Error fetching leaderboard:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLeaderboard();
    }, [period]);

    const getMedal = (rank) => {
        if (rank === 1) return '🥇';
        if (rank === 2) return '🥈';
        if (rank === 3) return '🥉';
        return `#${rank}`;
    };

    return (
        <div className="space-y-8 pb-20">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                <div>
                    <h2 className="text-3xl font-black text-slate-900 dark:text-white flex items-center gap-3">
                        <Trophy className="w-8 h-8 text-yellow-500" /> Elite Traders
                    </h2>
                    <p className="text-slate-500 mt-1">Real-time ranking of the most profitable intelligence nodes.</p>
                </div>

                <div className="flex bg-slate-200/50 dark:bg-slate-800/50 p-1.5 rounded-xl w-full md:w-auto">
                    {['weekly', 'monthly', 'all_time'].map((p) => (
                        <button
                            key={p}
                            onClick={() => setPeriod(p)}
                            className={`flex-1 md:flex-none px-6 py-2 rounded-lg text-xs font-black uppercase transition-all ${period === p
                                    ? "bg-white dark:bg-slate-700 shadow-md text-accent scale-[1.02]"
                                    : "text-slate-500 hover:text-slate-700"
                                }`}
                        >
                            {p.replace('_', ' ')}
                        </button>
                    ))}
                </div>
            </div>

            {myRank && (
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="bg-accent/5 border border-accent/20 p-6 rounded-2xl flex items-center justify-between"
                >
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center text-accent">
                            <Users className="w-6 h-6" />
                        </div>
                        <div>
                            <p className="text-xs font-black text-accent uppercase tracking-widest">Your Current Position</p>
                            <h3 className="text-2xl font-black text-slate-900 dark:text-white">Ranked #{myRank} Global</h3>
                        </div>
                    </div>
                    <button 
                        onClick={handleViewProfile}
                        className="hidden md:flex items-center gap-2 text-sm font-bold text-accent hover:underline"
                    >
                        View Public Profile <ChevronRight className="w-4 h-4" />
                    </button>
                </motion.div>
            )}

            <div className="card overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="bg-slate-50 dark:bg-slate-800/30">
                                <th className="px-6 py-4 text-xs font-black text-slate-500 uppercase tracking-widest">Rank</th>
                                <th className="px-6 py-4 text-xs font-black text-slate-500 uppercase tracking-widest">Intelligence Node</th>
                                <th className="px-6 py-4 text-xs font-black text-slate-500 uppercase tracking-widest text-right">Return Pct</th>
                                <th className="px-6 py-4 text-xs font-black text-slate-500 uppercase tracking-widest text-right">Win Rate</th>
                                <th className="px-6 py-4 text-xs font-black text-slate-500 uppercase tracking-widest text-right">Sharpe</th>
                                <th className="px-6 py-4 text-xs font-black text-slate-500 uppercase tracking-widest text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {loading ? (
                                <tr>
                                    <td colSpan="6" className="py-20 text-center animate-pulse text-slate-400 font-medium italic">Synchronizing leaderboard data...</td>
                                </tr>
                            ) : leaderboard.length === 0 ? (
                                <tr>
                                    <td colSpan="6" className="py-20 text-center text-slate-400 font-medium italic">No traders ranked yet.</td>
                                </tr>
                            ) : (
                                leaderboard.map((trader) => (
                                    <tr key={trader.user_id} className={`group hover:bg-slate-50 dark:hover:bg-slate-800/20 transition-colors ${trader.rank <= 3 ? 'bg-yellow-50/10' : ''}`}>
                                        <td className="px-6 py-5">
                                            <span className={`inline-flex items-center justify-center w-10 h-10 rounded-xl font-black ${trader.rank === 1 ? 'bg-yellow-500 text-white' :
                                                    trader.rank === 2 ? 'bg-slate-300 text-slate-700' :
                                                        trader.rank === 3 ? 'bg-orange-400 text-white' :
                                                            'bg-slate-100 dark:bg-slate-800 text-slate-500'
                                                }`}>
                                                {getMedal(trader.rank)}
                                            </span>
                                        </td>
                                        <td className="px-6 py-5">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                                                    {trader.avatar_url ? <img src={trader.avatar_url} className="w-full h-full object-cover" /> : null}
                                                </div>
                                                <div>
                                                    <h4 className="font-black text-slate-900 dark:text-white capitalize">{trader.username}</h4>
                                                    <p className="text-[10px] text-slate-500 font-bold uppercase">{trader.total_trades} Trades Logged</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-5 text-right font-black">
                                            <span className={`text-lg ${trader.total_return_pct >= 0 ? 'text-green-500' : 'text-rose-500'}`}>
                                                {trader.total_return_pct >= 0 ? '+' : ''}{trader.total_return_pct.toFixed(2)}%
                                            </span>
                                        </td>
                                        <td className="px-6 py-5 text-right font-bold text-slate-600 dark:text-slate-400">
                                            {trader.win_rate.toFixed(1)}%
                                        </td>
                                        <td className="px-6 py-5 text-right font-bold text-slate-600 dark:text-slate-400">
                                            {trader.sharpe_ratio.toFixed(2)}
                                        </td>
                                        <td className="px-6 py-5 text-right">
                                            <button 
                                                onClick={() => handleShare(trader)}
                                                className="bg-slate-100 dark:bg-slate-800 p-2 rounded-lg text-slate-500 hover:text-accent transition-colors"
                                            >
                                                <Share2 className="w-4 h-4" />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default LeaderboardPage;
