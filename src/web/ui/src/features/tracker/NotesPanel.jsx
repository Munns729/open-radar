import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Plus, MessageSquare, Phone, Users, Clock } from 'lucide-react';

export default function NotesPanel({ notes, trackedId, onNoteAdded }) {
    const [isAdding, setIsAdding] = useState(false);
    const [newNote, setNewNote] = useState('');
    const [noteType, setNoteType] = useState('research');
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async () => {
        if (!newNote.trim()) return;
        setSubmitting(true);
        try {
            const res = await fetch(`/api/tracker/company/${trackedId}/note`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    note_text: newNote,
                    note_type: noteType,
                    created_by: 'User' // In real app, get from auth context
                })
            });

            if (res.ok) {
                setNewNote('');
                setIsAdding(false);
                onNoteAdded();
            }
        } catch (error) {
            console.error("Failed to add note", error);
        } finally {
            setSubmitting(false);
        }
    };

    const getIcon = (type) => {
        switch (type) {
            case 'call': return <Phone className="h-4 w-4" />;
            case 'meeting': return <Users className="h-4 w-4" />;
            default: return <MessageSquare className="h-4 w-4" />;
        }
    };

    return (
        <Card className="h-full bg-surface border-border-subtle flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between py-4">
                <CardTitle className="text-lg">Research Notes</CardTitle>
                <Button variant="outline" size="sm" onClick={() => setIsAdding(!isAdding)}>
                    <Plus className="h-4 w-4 mr-1" />
                    New
                </Button>
            </CardHeader>

            <CardContent className="flex-1 overflow-y-auto space-y-4">
                {isAdding && (
                    <div className="bg-surface-alt p-3 rounded-md border border-border-subtle space-y-3">
                        <textarea
                            className="w-full min-h-[80px] p-2 bg-surface border border-input rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                            placeholder="Enter notes..."
                            value={newNote}
                            onChange={(e) => setNewNote(e.target.value)}
                        />
                        <div className="flex justify-between">
                            <select
                                className="h-8 text-sm bg-surface border border-input rounded px-2"
                                value={noteType}
                                onChange={(e) => setNoteType(e.target.value)}
                            >
                                <option value="research">Research</option>
                                <option value="call">Call</option>
                                <option value="meeting">Meeting</option>
                                <option value="outreach">Outreach</option>
                            </select>
                            <div className="flex gap-2">
                                <Button variant="ghost" size="sm" onClick={() => setIsAdding(false)}>Cancel</Button>
                                <Button size="sm" onClick={handleSubmit} disabled={submitting}>Save</Button>
                            </div>
                        </div>
                    </div>
                )}

                {notes.length === 0 && !isAdding ? (
                    <div className="text-center text-text-ter py-8 text-sm">No notes yet.</div>
                ) : (
                    <div className="space-y-4">
                        {notes.map(note => (
                            <div key={note.id} className="flex gap-3">
                                <div className="mt-1 text-text-ter flex-shrink-0">
                                    {getIcon(note.note_type)}
                                </div>
                                <div className="flex-1 space-y-1">
                                    <div className="flex items-center gap-2">
                                        <Badge variant="secondary" className="text-[10px] h-5 py-0 capitalize">
                                            {note.note_type}
                                        </Badge>
                                        <span className="text-xs text-text-ter flex items-center gap-1">
                                            <Clock className="h-3 w-3" />
                                            {new Date(note.created_at).toLocaleString()}
                                        </span>
                                    </div>
                                    <p className="text-sm text-text-pri whitespace-pre-wrap">
                                        {note.note_text}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
