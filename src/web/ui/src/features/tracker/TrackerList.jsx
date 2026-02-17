import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { useNavigate } from 'react-router-dom';
import { Clock, Tag, ExternalLink, MoreHorizontal, AlertCircle } from 'lucide-react';

export default function TrackerList() {
    const [companies, setCompanies] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        fetchTrackedCompanies();
    }, []);

    const fetchTrackedCompanies = async () => {
        try {
            const data = await api.getTrackedCompanies();
            setCompanies(data);
        } catch (error) {
            console.error("Failed to fetch tracked companies", error);
        } finally {
            setLoading(false);
        }
    };

    const getPriorityColor = (priority) => {
        switch (priority) {
            case 'high': return 'bg-danger/10 text-danger border-danger/20';
            case 'medium': return 'bg-warning/10 text-warning border-warning/20';
            case 'low': return 'bg-success/10 text-success border-success/20';
            default: return 'bg-surface-alt text-text-sec border-border-subtle';
        }
    };

    return (
        <Card className="h-full border-border-subtle bg-surface">
            <CardContent className="p-0">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead className="w-[250px]">Company</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Priority</TableHead>
                            <TableHead>Next Check</TableHead>
                            <TableHead>Last Update</TableHead>
                            <TableHead className="w-[100px]"></TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {loading ? (
                            <TableRow>
                                <TableCell colSpan={6} className="h-24 text-center text-text-sec">
                                    Loading tracker...
                                </TableCell>
                            </TableRow>
                        ) : companies.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={6} className="h-48 text-center">
                                    <div className="flex flex-col items-center gap-2 text-text-sec">
                                        <AlertCircle className="h-8 w-8 opacity-50" />
                                        <p>No companies currently tracked.</p>
                                        <p className="text-xs">Use "Add Target" to start monitoring.</p>
                                    </div>
                                </TableCell>
                            </TableRow>
                        ) : (
                            companies.map((company) => (
                                <TableRow
                                    key={company.id}
                                    className="cursor-pointer hover:bg-surface-alt/50"
                                    onClick={() => navigate(`/tracker/${company.id}`)}
                                >
                                    <TableCell>
                                        <div className="font-medium text-text-pri">
                                            Company ID: {company.company_id}
                                        </div>
                                        <div className="flex gap-1 mt-1">
                                            {company.tags?.slice(0, 2).map((tag, i) => (
                                                <Badge key={i} variant="outline" className="text-[10px] py-0 h-5">
                                                    {tag}
                                                </Badge>
                                            ))}
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <Badge variant="secondary" className="capitalize">
                                            {company.tracking_status}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>
                                        <Badge className={`capitalize ${getPriorityColor(company.priority)}`}>
                                            {company.priority}
                                        </Badge>
                                    </TableCell>
                                    <TableCell className="text-text-sec font-mono text-xs">
                                        {company.next_check_due ? new Date(company.next_check_due).toLocaleDateString() : '-'}
                                    </TableCell>
                                    <TableCell className="text-text-sec text-xs">
                                        {company.last_checked ? new Date(company.last_checked).toLocaleDateString() : 'Never'}
                                    </TableCell>
                                    <TableCell>
                                        <Button variant="ghost" size="icon" className="h-8 w-8">
                                            <MoreHorizontal className="h-4 w-4" />
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
}
