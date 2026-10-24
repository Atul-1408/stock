import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Send, User, Sparkles, MessageSquare, Plus, ChevronLeft, TrendingUp, ShieldAlert, History, Trash2 } from 'lucide-react';
import { toast } from 'react-toastify';
import api from '../utils/api';

const ChatbotPanel = () => {
    const [conversations, setConversations] = useState([]);
    const [currentConversation, setCurrentConversation] = useState(null);
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [loading, setLoading] = useState(false);
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const messagesEndRef = useRef(null);

    const fetchConversations = async () => {
        try {
            const res = await api.get('/chat/conversations');
            setConversations(res.data.conversations);
            if (res.data.conversations.length > 0 && !currentConversation) {
                setCurrentConversation(res.data.conversations[0]);
            }
        } catch (error) {
            console.error('Error fetching conversations:', error);
        }
    };

    const fetchMessages = async (id) => {
        try {
            const res = await api.get(`/chat/${id}/messages`);
            setMessages(res.data.messages);
        } catch (error) {
            toast.error("Failed to load history");
        }
    };

    useEffect(() => {
        fetchConversations();
    }, []);

    useEffect(() => {
        if (currentConversation) {
            fetchMessages(currentConversation.id);
        }
    }, [currentConversation]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const startNewConversation = async () => {
        try {
            const res = await api.post('/chat/conversation', { title: `New Analysis ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` });
            const newConv = { id: res.data.conversation_id, title: res.data.title };
            setConversations([newConv, ...conversations]);
            setCurrentConversation(newConv);
            setMessages([]);
        } catch (error) {
            toast.error("Could not start new chat");
        }
    };

    const deleteConversation = async (conv) => {
        if (!conv?.id) return;
        const ok = window.confirm(`Delete chat "${conv.title || 'Untitled'}"?`);
        if (!ok) return;
        try {
            await api.delete(`/chat/${conv.id}`);
            setConversations(prev => prev.filter(c => c.id !== conv.id));
            if (currentConversation?.id === conv.id) {
                const remaining = conversations.filter(c => c.id !== conv.id);
                const next = remaining.length > 0 ? remaining[0] : null;
                setCurrentConversation(next);
                setMessages([]);
            }
            toast.success('Chat deleted');
        } catch (error) {
            const msg = error?.response?.data?.message || 'Could not delete chat';
            toast.error(msg);
        }
    };

    const sendMessage = async (e) => {
        e.preventDefault();
        if (!inputMessage.trim() || loading) return;

        let targetConv = currentConversation;
        if (!targetConv) {
            await startNewConversation();
            // The effect will handle switching, but for immediate UI we'll wait for the next tick
            return;
        }

        const userMsgText = inputMessage;
        setInputMessage('');

        // Optimistic Update
        setMessages(prev => [...prev, { role: 'user', content: userMsgText }]);
        setLoading(true);

        try {
            const res = await api.post(`/chat/${targetConv.id}/message`, { message: userMsgText });
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: res.data.response,
                stocks_mentioned: Array.isArray(res.data.stocks_mentioned) ? res.data.stocks_mentioned : []
            }]);
        } catch (error) {
            const msg = error?.response?.data?.message || 'Chat request failed';
            toast.error(msg);
        } finally {
            setLoading(false);
        }
    };

    const quickPrompts = [
        { text: "Should I buy AAPL?", icon: <TrendingUp className="w-4 h-4" /> },
        { text: "TSLA Sentiment check", icon: <Sparkles className="w-4 h-4" /> },
        { text: "Portfolio risk analysis", icon: <ShieldAlert className="w-4 h-4" /> }
    ];

    return (
        <div className="flex h-[80vh] bg-white/50 dark:bg-slate-900/50 backdrop-blur-xl rounded-3xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-2xl">
            {/* Sidebar */}
            <AnimatePresence>
                {sidebarOpen && (
                    <motion.div
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 300, opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        className="flex flex-col border-r border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20"
                    >
                        <div className="p-6">
                            <button
                                onClick={startNewConversation}
                                className="w-full flex items-center justify-center gap-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 py-3 rounded-xl font-black text-sm hover:opacity-90 transition-all shadow-lg"
                            >
                                <Plus className="w-4 h-4" /> New Intelligence Session
                            </button>
                        </div>

                        <div className="flex-1 overflow-y-auto px-4 space-y-2">
                            <h4 className="px-4 text-[10px] font-black uppercase text-slate-400 tracking-widest mb-2 flex items-center gap-2">
                                <History className="w-3 h-3" /> Recent Loops
                            </h4>
                            {conversations.map(conv => (
                                <div
                                    key={conv.id}
                                    onClick={() => setCurrentConversation(conv)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' || e.key === ' ') {
                                            e.preventDefault();
                                            setCurrentConversation(conv);
                                        }
                                    }}
                                    role="button"
                                    tabIndex={0}
                                    className={`w-full text-left p-3 rounded-xl flex items-center gap-3 transition-all ${currentConversation?.id === conv.id
                                        ? "bg-accent/10 border border-accent/20 text-accent font-bold"
                                        : "hover:bg-slate-200/50 dark:hover:bg-slate-800/50 text-slate-500"
                                        }`}
                                >
                                    <MessageSquare className="w-4 h-4 shrink-0" />
                                    <span className="truncate text-xs">{conv.title}</span>
                                    <span className="ml-auto flex items-center gap-2">
                                        <button
                                            type="button"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                deleteConversation(conv);
                                            }}
                                            className="p-1 rounded-md hover:bg-rose-500/10 text-slate-400 hover:text-rose-500 transition-colors"
                                            title="Delete chat"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </span>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col relative">
                <header className="p-6 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center bg-white/80 dark:bg-slate-900/80 backdrop-blur-md z-10">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => setSidebarOpen(!sidebarOpen)}
                            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400"
                        >
                            <ChevronLeft className={`w-5 h-5 transition-transform ${!sidebarOpen ? 'rotate-180' : ''}`} />
                        </button>
                        <div>
                            <h3 className="font-black text-slate-900 dark:text-white flex items-center gap-2">
                                <Bot className="w-5 h-5 text-accent" /> Claude 3.5 Sonnet
                                <span className="text-[10px] px-2 py-0.5 bg-green-500/10 text-green-500 rounded-full font-bold">LIVE CONTEXT</span>
                            </h3>
                            <p className="text-xs text-slate-500">Trading Intelligence Node Alpha</p>
                        </div>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto p-6 space-y-6 flex flex-col no-scrollbar">
                    {messages.length === 0 && (
                        <div className="flex-1 flex flex-col items-center justify-center text-center space-y-8 animate-in fade-in zoom-in duration-500">
                            <div className="w-20 h-20 bg-accent/10 rounded-3xl flex items-center justify-center text-accent">
                                <Sparkles className="w-10 h-10" />
                            </div>
                            <div>
                                <h2 className="text-2xl font-black mb-2 text-slate-900 dark:text-white">Initialize Intelligence Stream</h2>
                                <p className="text-slate-500 max-w-sm mx-auto">Analyze your portfolio, verify stock sentiment, or request trade recommendations based on current market signals.</p>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 w-full max-w-2xl px-4">
                                {quickPrompts.map(prompt => (
                                    <button
                                        key={prompt.text}
                                        onClick={() => setInputMessage(prompt.text)}
                                        className="p-4 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-accent hover:bg-accent/5 transition-all text-left group"
                                    >
                                        <div className="text-slate-400 group-hover:text-accent mb-2">{prompt.icon}</div>
                                        <span className="text-sm font-bold text-slate-700 dark:text-slate-300">{prompt.text}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {messages.map((msg, i) => (
                        <motion.div
                            key={i}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div className={`max-w-[85%] flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                                <div className={`w-8 h-8 rounded-full shrink-0 flex items-center justify-center ${msg.role === 'user' ? 'bg-slate-900 text-white' : 'bg-accent text-white'}`}>
                                    {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                                </div>
                                <div className={`p-4 rounded-2xl ${msg.role === 'user'
                                    ? 'bg-accent text-white font-medium rounded-tr-none'
                                    : 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-tl-none border border-slate-200 dark:border-slate-700'
                                    }`}>
                                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                                    {Array.isArray(msg.stocks_mentioned) && msg.stocks_mentioned.length > 0 && (
                                        <div className="mt-3 flex gap-2 flex-wrap">
                                            {msg.stocks_mentioned.map((t, index) => (
                                                <span key={`${t}-${index}`} className="px-2 py-0.5 bg-white/20 dark:bg-black/20 rounded-md text-[10px] font-black uppercase tracking-widest">{t}</span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </motion.div>
                    ))}
                    {loading && (
                        <div className="flex justify-start">
                            <div className="flex gap-4">
                                <div className="w-8 h-8 rounded-full bg-accent text-white flex items-center justify-center animate-pulse">
                                    <Bot className="w-4 h-4" />
                                </div>
                                <div className="p-4 bg-slate-100 dark:bg-slate-800 rounded-2xl rounded-tl-none flex items-center gap-1">
                                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"></span>
                                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:0.2s]"></span>
                                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:0.4s]"></span>
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                <div className="p-6 bg-white/50 dark:bg-slate-900/50 backdrop-blur-xl border-t border-slate-200 dark:border-slate-800">
                    <form onSubmit={sendMessage} className="relative group max-w-4xl mx-auto">
                        <input
                            type="text"
                            className="w-full bg-slate-100 dark:bg-slate-800/50 border-2 border-transparent focus:border-accent rounded-2xl px-6 py-4 outline-none text-slate-900 dark:text-white font-medium shadow-inner transition-all group-hover:bg-slate-200/50 dark:group-hover:bg-slate-800"
                            placeholder="How is AAPL sentiment looking for a long trade?"
                            value={inputMessage}
                            onChange={e => setInputMessage(e.target.value)}
                            disabled={loading}
                        />
                        <button
                            type="submit"
                            disabled={!inputMessage.trim() || loading}
                            className="absolute right-3 top-3 bg-accent text-white p-2.5 rounded-xl hover:opacity-90 disabled:opacity-30 disabled:grayscale transition-all shadow-lg shadow-accent/20"
                        >
                            <Send className="w-5 h-5" />
                        </button>
                    </form>
                    <div className="mt-4 flex justify-center items-center gap-6">
                        <div className="flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                            <Sparkles className="w-3 h-3 text-accent" /> Real-time Sentiment
                        </div>
                        <div className="flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                            <TrendingUp className="w-3 h-3 text-accent" /> Portfolio Context
                        </div>
                        <div className="flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                            <ShieldAlert className="w-3 h-3 text-accent" /> Risk Assessment
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ChatbotPanel;
