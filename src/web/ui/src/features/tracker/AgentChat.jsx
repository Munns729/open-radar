import React, { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import {
    Send,
    Bot,
    User,
    Upload,
    FileText,
    Loader2,
    Search,
    MessageSquare,
    Sparkles,
    Trash2,
    Paperclip
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function AgentChat({ trackedId, companyName }) {
    const [messages, setMessages] = useState([
        {
            role: 'assistant',
            content: `Hello! I'm your RADAR Agent. I have access to ${companyName}'s profile, research notes, events, and any uploaded documents. How can I help you analyze this target?`,
            timestamp: new Date().toISOString()
        }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [documents, setDocuments] = useState([]);
    const [uploading, setUploading] = useState(false);
    const scrollRef = useRef(null);
    const fileInputRef = useRef(null);

    useEffect(() => {
        fetchDocuments();
    }, [trackedId]);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const fetchDocuments = async () => {
        try {
            const res = await fetch(`/api/tracker/company/${trackedId}/documents`);
            if (res.ok) {
                const data = await res.json();
                setDocuments(data);
            }
        } catch (error) {
            console.error("Failed to fetch documents", error);
        }
    };

    const handleUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setUploading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch(`/api/tracker/company/${trackedId}/documents`, {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                fetchDocuments();
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: `Success! I've processed **${file.name}** and added it to my knowledge base. You can now ask questions about its content.`,
                    timestamp: new Date().toISOString()
                }]);
            }
        } catch (error) {
            console.error("Upload failed", error);
        } finally {
            setUploading(false);
        }
    };

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMsg = { role: 'user', content: input, timestamp: new Date().toISOString() };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const res = await fetch(`/api/tracker/company/${trackedId}/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: input })
            });

            if (res.ok) {
                const data = await res.json();
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: data.answer,
                    sources: data.sources,
                    timestamp: new Date().toISOString()
                }]);
            }
        } catch (error) {
            console.error("Query failed", error);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: "Sorry, I encountered an error while processing that request.",
                timestamp: new Date().toISOString()
            }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-full min-h-0">
            {/* Chat Area */}
            <Card className="lg:col-span-3 flex flex-col h-full border-border-subtle bg-surface min-h-0">
                <CardHeader className="py-3 border-b border-border-subtle flex flex-row items-center justify-between">
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                        <MessageSquare className="h-4 w-4 text-primary" />
                        AI Research Assistant
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-[10px] text-text-ter border-border-subtle">
                            Context: {documents.length} Docs + Notes + Events
                        </Badge>
                    </div>
                </CardHeader>

                <CardContent
                    ref={scrollRef}
                    className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-hide bg-surface-alt/20"
                >
                    {messages.map((msg, i) => (
                        <div
                            key={i}
                            className={cn(
                                "flex gap-3 max-w-[85%]",
                                msg.role === 'user' ? "ml-auto flex-row-reverse" : ""
                            )}
                        >
                            <div className={cn(
                                "h-8 w-8 rounded-full flex items-center justify-center shrink-0",
                                msg.role === 'user' ? "bg-primary text-white" : "bg-surface border border-border-subtle text-primary shadow-sm"
                            )}>
                                {msg.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                            </div>
                            <div className="space-y-1">
                                <div className={cn(
                                    "p-3 rounded-2xl text-sm shadow-sm",
                                    msg.role === 'user'
                                        ? "bg-primary text-white rounded-tr-none"
                                        : "bg-surface border border-border-subtle text-text-pri rounded-tl-none"
                                )}>
                                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

                                    {msg.sources && msg.sources.length > 0 && (
                                        <div className="mt-3 pt-2 border-t border-border-subtle/50 flex flex-wrap gap-1">
                                            {msg.sources.map((s, idx) => (
                                                <span key={idx} className="text-[10px] px-1.5 py-0.5 bg-surface-alt/50 rounded flex items-center gap-1">
                                                    <Search className="h-2 w-2" /> {s}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                                <div className={cn(
                                    "text-[10px] text-text-ter px-1",
                                    msg.role === 'user' ? "text-right" : ""
                                )}>
                                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </div>
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="flex gap-3 max-w-[85%]">
                            <div className="h-8 w-8 rounded-full bg-surface border border-border-subtle text-primary flex items-center justify-center shadow-sm">
                                <Bot className="h-4 w-4" />
                            </div>
                            <div className="bg-surface border border-border-subtle p-3 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2">
                                <Loader2 className="h-3 w-3 animate-spin text-primary" />
                                <span className="text-xs text-text-sec">Analyzing knowledge base...</span>
                            </div>
                        </div>
                    )}
                </CardContent>

                <CardFooter className="p-4 border-t border-border-subtle bg-surface">
                    <form
                        className="w-full flex gap-2"
                        onSubmit={(e) => { e.preventDefault(); handleSend(); }}
                    >
                        <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="shrink-0 text-text-ter hover:text-primary transition-colors"
                            onClick={() => fileInputRef.current?.click()}
                            disabled={uploading}
                        >
                            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Paperclip className="h-5 w-5" />}
                        </Button>
                        <input
                            type="file"
                            className="hidden"
                            ref={fileInputRef}
                            onChange={handleUpload}
                            accept=".pdf,.txt,.md,.csv"
                        />
                        <Input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Ask me anything about this company..."
                            className="flex-1 bg-surface-alt border-border-subtle focus:ring-primary"
                        />
                        <Button type="submit" size="icon" disabled={!input.trim() || loading} className="shrink-0">
                            <Send className="h-4 w-4" />
                        </Button>
                    </form>
                </CardFooter>
            </Card>

            {/* Knowledge Base Sidebar */}
            <div className="lg:col-span-1 space-y-6 flex flex-col h-full min-h-0">
                <Card className="flex-1 border-border-subtle bg-surface flex flex-col min-h-0">
                    <CardHeader className="py-3 border-b border-border-subtle">
                        <CardTitle className="text-sm font-semibold flex items-center gap-2">
                            <FileText className="h-4 w-4" />
                            Knowledge Base
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 overflow-y-auto p-2 space-y-1">
                        {documents.length === 0 ? (
                            <div className="text-center py-8 px-4">
                                <Upload className="h-8 w-8 text-text-ter mx-auto mb-2 opacity-50" />
                                <p className="text-xs text-text-ter">No documents uploaded yet. Add PDFs, Pitch Decks, or IMs to ground the agent.</p>
                            </div>
                        ) : (
                            documents.map(doc => (
                                <div
                                    key={doc.id}
                                    className="p-2.5 rounded-md hover:bg-surface-alt group cursor-default border border-transparent hover:border-border-subtle transition-all"
                                >
                                    <div className="flex items-start gap-3">
                                        <div className="h-8 w-8 rounded bg-primary/10 text-primary flex items-center justify-center shrink-0">
                                            <FileText className="h-4 w-4" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-xs font-medium text-text-pri truncate" title={doc.filename}>
                                                {doc.filename}
                                            </p>
                                            <p className="text-[10px] text-text-ter uppercase font-bold mt-0.5">
                                                {doc.file_type} • {new Date(doc.uploaded_at).toLocaleDateString()}
                                            </p>
                                        </div>
                                        <button className="opacity-0 group-hover:opacity-100 p-1 text-text-ter hover:text-danger hover:bg-danger/10 rounded transition-all">
                                            <Trash2 className="h-3 w-3" />
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </CardContent>
                    <CardFooter className="p-3 border-t border-border-subtle bg-surface-alt/50">
                        <p className="text-[10px] text-text-ter italic leading-tight">
                            Uploaded information is parsed and indexed for contextual reasoning.
                        </p>
                    </CardFooter>
                </Card>

                {/* Suggestions Card */}
                <Card className="border-primary/20 bg-primary/5 shadow-none">
                    <CardHeader className="py-2.5">
                        <CardTitle className="text-[11px] font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                            <Sparkles className="h-3 w-3" /> Suggested Queries
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="py-0 pb-4 space-y-2">
                        {[
                            "Summarize the key moats based on recent notes.",
                            "What are the main risks mentioned in the docs?",
                            "List milestones from the timeline.",
                            "Cross-reference research notes with events."
                        ].map((q, idx) => (
                            <button
                                key={idx}
                                onClick={() => setInput(q)}
                                className="w-full text-left text-[11px] text-text-sec hover:text-primary hover:bg-white/50 p-2 rounded border border-transparent hover:border-primary/20 transition-all font-medium"
                            >
                                "{q}"
                            </button>
                        ))}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
