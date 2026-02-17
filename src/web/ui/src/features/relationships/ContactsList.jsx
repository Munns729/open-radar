import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Users, Plus, Search, Filter } from 'lucide-react';

const CONTACT_TYPES = ['founder', 'ceo', 'cfo', 'advisor', 'banker', 'lawyer', 'investor'];
const STRENGTH_LEVELS = ['cold', 'warm', 'hot'];

const strengthColors = {
    cold: 'bg-blue-500/20 text-blue-300 ring-blue-500/30',
    warm: 'bg-amber-500/20 text-amber-300 ring-amber-500/30',
    hot: 'bg-red-500/20 text-red-300 ring-red-500/30'
};

const typeColors = {
    founder: 'bg-purple-500/20 text-purple-300',
    ceo: 'bg-indigo-500/20 text-indigo-300',
    cfo: 'bg-sky-500/20 text-sky-300',
    advisor: 'bg-emerald-500/20 text-emerald-300',
    banker: 'bg-amber-500/20 text-amber-300',
    lawyer: 'bg-slate-500/20 text-slate-300',
    investor: 'bg-rose-500/20 text-rose-300'
};

export default function ContactsList({ onSelectContact }) {
    const [contacts, setContacts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [typeFilter, setTypeFilter] = useState('');
    const [strengthFilter, setStrengthFilter] = useState('');
    const [showAddModal, setShowAddModal] = useState(false);
    const [newContact, setNewContact] = useState({
        full_name: '',
        email: '',
        phone: '',
        company_name: '',
        job_title: '',
        contact_type: 'founder',
        location: '',
        linkedin_url: '',
        notes: '',
        tags: []
    });

    const fetchContacts = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (searchTerm) params.append('search', searchTerm);
            if (typeFilter) params.append('contact_type', typeFilter);
            if (strengthFilter) params.append('strength', strengthFilter);

            const res = await fetch(`/api/relationships/contacts?${params}`);
            const data = await res.json();
            setContacts(data.contacts || []);
        } catch (error) {
            console.error("Failed to fetch contacts", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchContacts();
    }, [searchTerm, typeFilter, strengthFilter]);

    const handleAddContact = async (e) => {
        e.preventDefault();
        try {
            const res = await fetch('/api/relationships/contact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newContact)
            });

            if (res.ok) {
                setShowAddModal(false);
                setNewContact({
                    full_name: '',
                    email: '',
                    phone: '',
                    company_name: '',
                    job_title: '',
                    contact_type: 'founder',
                    location: '',
                    linkedin_url: '',
                    notes: '',
                    tags: []
                });
                fetchContacts();
            } else {
                const error = await res.json();
                alert(error.detail || 'Failed to add contact');
            }
        } catch (error) {
            console.error("Error adding contact", error);
        }
    };

    return (
        <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <Users className="h-5 w-5 text-purple-400" />
                            Contacts
                        </CardTitle>
                        <CardDescription>Manage your network of founders, advisors, and deal contacts.</CardDescription>
                    </div>
                    <button
                        onClick={() => setShowAddModal(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                    >
                        <Plus className="h-4 w-4" />
                        Add Contact
                    </button>
                </div>

                {/* Filters */}
                <div className="flex gap-4 mt-4">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <input
                            type="text"
                            placeholder="Search contacts..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 bg-background/50 border border-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                        />
                    </div>
                    <select
                        value={typeFilter}
                        onChange={(e) => setTypeFilter(e.target.value)}
                        className="px-4 py-2 bg-background/50 border border-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                    >
                        <option value="">All Types</option>
                        {CONTACT_TYPES.map(type => (
                            <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option>
                        ))}
                    </select>
                    <select
                        value={strengthFilter}
                        onChange={(e) => setStrengthFilter(e.target.value)}
                        className="px-4 py-2 bg-background/50 border border-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                    >
                        <option value="">All Strengths</option>
                        {STRENGTH_LEVELS.map(level => (
                            <option key={level} value={level}>{level.charAt(0).toUpperCase() + level.slice(1)}</option>
                        ))}
                    </select>
                </div>
            </CardHeader>

            <CardContent>
                <div className="rounded-md border border-border/50 bg-background/50">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Name</TableHead>
                                <TableHead>Company</TableHead>
                                <TableHead>Type</TableHead>
                                <TableHead>Strength</TableHead>
                                <TableHead>Score</TableHead>
                                <TableHead>Last Contact</TableHead>
                                <TableHead>Tags</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={7} className="text-center h-24 text-muted-foreground">
                                        Loading contacts...
                                    </TableCell>
                                </TableRow>
                            ) : contacts.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={7} className="text-center h-24 text-muted-foreground">
                                        No contacts found. Add your first contact to get started.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                contacts.map((contact) => (
                                    <TableRow
                                        key={contact.id}
                                        className="hover:bg-purple-950/10 cursor-pointer"
                                        onClick={() => onSelectContact && onSelectContact(contact.id)}
                                    >
                                        <TableCell className="font-medium text-foreground">
                                            <div>
                                                <div>{contact.full_name}</div>
                                                {contact.job_title && (
                                                    <div className="text-xs text-muted-foreground">{contact.job_title}</div>
                                                )}
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-muted-foreground">
                                            {contact.company_name || '-'}
                                        </TableCell>
                                        <TableCell>
                                            <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${typeColors[contact.contact_type] || 'bg-gray-500/20 text-gray-300'}`}>
                                                {contact.contact_type}
                                            </span>
                                        </TableCell>
                                        <TableCell>
                                            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${strengthColors[contact.relationship_strength]}`}>
                                                {contact.relationship_strength}
                                            </span>
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex items-center gap-2">
                                                <div className="w-12 h-2 bg-gray-700 rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
                                                        style={{ width: `${contact.relationship_score}%` }}
                                                    />
                                                </div>
                                                <span className="text-xs text-muted-foreground">{contact.relationship_score}</span>
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-muted-foreground text-xs">
                                            {contact.last_contact_date
                                                ? new Date(contact.last_contact_date).toLocaleDateString()
                                                : 'Never'
                                            }
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex gap-1 flex-wrap">
                                                {(contact.tags || []).slice(0, 3).map((tag, i) => (
                                                    <span key={i} className="text-xs px-2 py-0.5 bg-muted rounded">
                                                        {tag}
                                                    </span>
                                                ))}
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </div>
            </CardContent>

            {/* Add Contact Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-card border border-border rounded-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
                        <h2 className="text-xl font-semibold mb-4">Add New Contact</h2>
                        <form onSubmit={handleAddContact} className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1">Full Name *</label>
                                    <input
                                        type="text"
                                        required
                                        value={newContact.full_name}
                                        onChange={(e) => setNewContact({ ...newContact, full_name: e.target.value })}
                                        className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Email</label>
                                    <input
                                        type="email"
                                        value={newContact.email}
                                        onChange={(e) => setNewContact({ ...newContact, email: e.target.value })}
                                        className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1">Company</label>
                                    <input
                                        type="text"
                                        value={newContact.company_name}
                                        onChange={(e) => setNewContact({ ...newContact, company_name: e.target.value })}
                                        className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Job Title</label>
                                    <input
                                        type="text"
                                        value={newContact.job_title}
                                        onChange={(e) => setNewContact({ ...newContact, job_title: e.target.value })}
                                        className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1">Type</label>
                                    <select
                                        value={newContact.contact_type}
                                        onChange={(e) => setNewContact({ ...newContact, contact_type: e.target.value })}
                                        className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                    >
                                        {CONTACT_TYPES.map(type => (
                                            <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Phone</label>
                                    <input
                                        type="tel"
                                        value={newContact.phone}
                                        onChange={(e) => setNewContact({ ...newContact, phone: e.target.value })}
                                        className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">LinkedIn URL</label>
                                <input
                                    type="url"
                                    value={newContact.linkedin_url}
                                    onChange={(e) => setNewContact({ ...newContact, linkedin_url: e.target.value })}
                                    className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                    placeholder="https://linkedin.com/in/..."
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Location</label>
                                <input
                                    type="text"
                                    value={newContact.location}
                                    onChange={(e) => setNewContact({ ...newContact, location: e.target.value })}
                                    className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                    placeholder="London, UK"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Notes</label>
                                <textarea
                                    value={newContact.notes}
                                    onChange={(e) => setNewContact({ ...newContact, notes: e.target.value })}
                                    className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                    rows={3}
                                />
                            </div>
                            <div className="flex gap-3 justify-end">
                                <button
                                    type="button"
                                    onClick={() => setShowAddModal(false)}
                                    className="px-4 py-2 text-muted-foreground hover:text-foreground transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                                >
                                    Add Contact
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </Card>
    );
}
