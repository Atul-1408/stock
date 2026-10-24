import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Bot, 
  Send, 
  User, 
  Sparkles, 
  MessageSquare, 
  Plus, 
  ChevronLeft, 
  TrendingUp, 
  ShieldAlert, 
  History, 
  Trash2,
  Terminal,
  Activity
} from "lucide-react";
import { toast } from "react-toastify";
import api from "../utils/api";

const ChatbotPanel = () => {
  const [conversations, setConversations] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef(null);

  const fetchConversations = async () => {
    try {
      const res = await api.get("/chat/conversations");
      setConversations(res.data.conversations || []);
      if (res.data.conversations?.length > 0 && !currentConversation) {
        setCurrentConversation(res.data.conversations[0]);
      }
    } catch (error) {
      console.error("Error fetching conversations:", error);
    }
  };

  const fetchMessages = async (id) => {
    try {
      const res = await api.get(`/chat/${id}/messages`);
      setMessages(res.data.messages || []);
    } catch (error) {
      toast.error("Failed to load message history");
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
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const startNewConversation = async () => {
    try {
      const res = await api.post("/chat/conversation", {
        title: `Query ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
      });
      const newConv = { id: res.data.conversation_id, title: res.data.title };
      setConversations([newConv, ...conversations]);
      setCurrentConversation(newConv);
      setMessages([]);
    } catch (error) {
      toast.error("Could not initiate intelligence thread");
    }
  };

  const deleteConversation = async (conv) => {
    if (!conv?.id) return;
    const ok = window.confirm(`Delete thread "${conv.title || "Untitled"}"?`);
    if (!ok) return;
    try {
      await api.delete(`/chat/${conv.id}`);
      setConversations((prev) => prev.filter((c) => c.id !== conv.id));
      if (currentConversation?.id === conv.id) {
        const remaining = conversations.filter((c) => c.id !== conv.id);
        const next = remaining.length > 0 ? remaining[0] : null;
        setCurrentConversation(next);
        setMessages([]);
      }
      toast.success("Intelligence session removed");
    } catch (error) {
      const msg = error?.response?.data?.message || "Could not delete thread";
      toast.error(msg);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || loading) return;

    let targetConv = currentConversation;
    if (!targetConv) {
      await startNewConversation();
      return;
    }

    const userMsgText = inputMessage;
    setInputMessage("");

    // Optimistic Update
    setMessages((prev) => [...prev, { role: "user", content: userMsgText }]);
    setLoading(true);

    try {
      const res = await api.post(`/chat/${targetConv.id}/message`, { message: userMsgText });
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.data.response,
          stocks_mentioned: Array.isArray(res.data.stocks_mentioned) ? res.data.stocks_mentioned : []
        }
      ]);
    } catch (error) {
      const msg = error?.response?.data?.message || "Inference node request failed";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const quickPrompts = [
    { text: "Analyze AAPL sentiment vs 30-day technical trend", icon: TrendingUp },
    { text: "Evaluate portfolio downside exposure for semiconductor earnings", icon: ShieldAlert },
    { text: "Scan NIFTY50 momentum breakouts with positive news volume", icon: Sparkles }
  ];

  return (
    <div className="flex h-[calc(100vh-140px)] min-h-[580px] bg-terminal-900 border border-terminal-800 rounded overflow-hidden">
      {/* Thread History Sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 280, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            className="flex flex-col border-r border-terminal-800 bg-terminal-950/80 shrink-0"
          >
            <div className="p-4 border-b border-terminal-800">
              <button
                onClick={startNewConversation}
                className="w-full flex items-center justify-center gap-2 bg-terminal-cyan/10 border border-terminal-cyan/40 hover:bg-terminal-cyan/20 text-terminal-cyan py-2.5 rounded font-mono text-xs uppercase font-bold tracking-wider transition-all"
              >
                <Plus className="w-4 h-4" /> New Query Stream
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-1">
              <div className="px-2 py-1 font-mono text-2xs uppercase tracking-wider text-slate-400 font-bold flex items-center gap-1.5">
                <History className="w-3 h-3 text-slate-400" /> Session History
              </div>

              {conversations.map((conv) => {
                const isSelected = currentConversation?.id === conv.id;
                return (
                  <div
                    key={conv.id}
                    onClick={() => setCurrentConversation(conv)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") setCurrentConversation(conv);
                    }}
                    className={`w-full text-left px-3 py-2 rounded font-mono text-xs flex items-center justify-between group transition-colors cursor-pointer ${
                      isSelected
                        ? "bg-terminal-850 text-terminal-cyan border-l-2 border-terminal-cyan"
                        : "text-slate-400 hover:text-slate-200 hover:bg-terminal-900"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-70" />
                      <span className="truncate">{conv.title || "Untitled Session"}</span>
                    </div>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteConversation(conv);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:text-terminal-coral transition-opacity"
                      title="Delete thread"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })}

              {conversations.length === 0 && (
                <div className="p-4 text-center font-mono text-2xs text-slate-400">
                  No previous sessions logged.
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Terminal Chat Area */}
      <div className="flex-1 flex flex-col bg-[#070b12] relative overflow-hidden">
        {/* Stream Header */}
        <div className="px-5 py-3 border-b border-terminal-800 bg-terminal-900/60 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1.5 rounded border border-terminal-700 hover:border-terminal-600 bg-terminal-950 text-slate-400 hover:text-slate-200 transition-colors"
              title="Toggle sidebar"
            >
              <ChevronLeft className={`w-4 h-4 transition-transform ${!sidebarOpen ? "rotate-180" : ""}`} />
            </button>

            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold uppercase tracking-wider text-slate-100 flex items-center gap-1.5">
                  <Terminal className="w-4 h-4 text-terminal-cyan" />
                  Neural Financial Intelligence Node
                </span>
                <span className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded font-mono text-2xs uppercase bg-terminal-emerald/10 border border-terminal-emerald/30 text-terminal-emerald font-semibold">
                  <span className="w-1.5 h-1.5 rounded-full bg-terminal-emerald animate-pulse" />
                  ONLINE
                </span>
              </div>
              <div className="font-mono text-2xs text-slate-400">
                Context: Global Indices &bull; News Sentiment Wire &bull; Technical Oscillators
              </div>
            </div>
          </div>
        </div>

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-xl mx-auto px-4 py-8">
              <div className="w-12 h-12 rounded border border-terminal-700 bg-terminal-950 flex items-center justify-center text-terminal-cyan mb-4">
                <Bot className="w-6 h-6" />
              </div>
              <h2 className="font-mono text-sm uppercase font-bold text-slate-100 tracking-wider mb-1">
                Awaiting Command Stream
              </h2>
              <p className="font-mono text-xs text-slate-400 mb-6 max-w-md">
                Query market sentiment vectors, verify asset fundamentals, or run risk impact models on custom positions.
              </p>

              <div className="grid grid-cols-1 gap-2.5 w-full">
                {quickPrompts.map((prompt) => {
                  const Icon = prompt.icon;
                  return (
                    <button
                      key={prompt.text}
                      onClick={() => setInputMessage(prompt.text)}
                      className="p-3 rounded border border-terminal-800 bg-terminal-950/60 hover:border-terminal-cyan/50 hover:bg-terminal-900 transition-all text-left flex items-center gap-3 group"
                    >
                      <Icon className="w-4 h-4 text-terminal-cyan shrink-0" />
                      <span className="font-mono text-xs text-slate-300 group-hover:text-slate-100">
                        {prompt.text}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded p-4 font-mono text-xs ${
                  msg.role === "user"
                    ? "bg-terminal-cyan/10 border border-terminal-cyan/30 text-slate-100"
                    : "bg-terminal-900 border border-terminal-800 text-slate-200"
                }`}
              >
                <div className="flex items-center gap-2 mb-2 font-mono text-2xs uppercase tracking-wider text-slate-400">
                  {msg.role === "user" ? (
                    <>
                      <User className="w-3.5 h-3.5 text-terminal-cyan" />
                      <span className="font-bold text-terminal-cyan">Operator</span>
                    </>
                  ) : (
                    <>
                      <Bot className="w-3.5 h-3.5 text-terminal-emerald" />
                      <span className="font-bold text-terminal-emerald">Intelligence Engine</span>
                    </>
                  )}
                </div>

                <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>

                {Array.isArray(msg.stocks_mentioned) && msg.stocks_mentioned.length > 0 && (
                  <div className="mt-3 pt-2 border-t border-terminal-800 flex items-center gap-2 flex-wrap">
                    <span className="text-2xs text-slate-400 uppercase font-bold">Identified Symbols:</span>
                    {msg.stocks_mentioned.map((t, idx) => (
                      <span
                        key={`${t}-${idx}`}
                        className="px-1.5 py-0.2 rounded bg-terminal-950 border border-terminal-700 text-terminal-cyan text-2xs font-bold"
                      >
                        ${t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="rounded p-3 bg-terminal-900 border border-terminal-800 flex items-center gap-2 text-slate-400 font-mono text-xs">
                <Bot className="w-4 h-4 text-terminal-cyan animate-pulse" />
                <span>Running tensor inference & news correlation...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-terminal-800 bg-terminal-950/70">
          <form onSubmit={sendMessage} className="relative flex items-center">
            <span className="absolute left-3.5 text-slate-500 font-mono text-xs">&gt;</span>
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              disabled={loading}
              placeholder="Query terminal intelligence (e.g. 'Assess volatility risks for NVDA this week')..."
              className="w-full bg-terminal-900 border border-terminal-700 rounded pl-8 pr-12 py-3 font-mono text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-terminal-cyan"
            />
            <button
              type="submit"
              disabled={!inputMessage.trim() || loading}
              className="absolute right-2 p-1.5 rounded bg-terminal-cyan/15 hover:bg-terminal-cyan/30 text-terminal-cyan disabled:opacity-30 disabled:hover:bg-transparent transition-all"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          <div className="mt-2 flex items-center justify-between font-mono text-2xs text-slate-400">
            <div className="flex items-center gap-4">
              <span>Shift + Enter for multiline</span>
              <span>&bull;</span>
              <span>Encrypted Session</span>
            </div>
            <span>Node: LLaMA-3.3-70B / Claude-3.5</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatbotPanel;
