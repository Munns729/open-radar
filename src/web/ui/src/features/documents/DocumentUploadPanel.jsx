import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Upload, FileText, Loader2, CheckCircle, XCircle, AlertCircle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

const DOCUMENT_TYPES = [
    'cim',
    'mgmt_call',
    'expert_call',
    'customer_ref',
    'financial_model',
    'news',
    'other',
];

const ACCEPT = '.pdf,.txt,.docx';

export default function DocumentUploadPanel({ companyId }) {
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [documentType, setDocumentType] = useState('cim');
    const [dragActive, setDragActive] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null);
    const [error, setError] = useState(null);

    const fetchDocuments = useCallback(async () => {
        if (!companyId) return;
        try {
            const data = await api.getCompanyDocumentsIngestion(companyId);
            setDocuments(Array.isArray(data) ? data : []);
        } catch (e) {
            if (e.status !== 404) setError(e.message || 'Failed to load documents.');
        } finally {
            setLoading(false);
        }
    }, [companyId]);

    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);

    const hasProcessing = documents.some(
        (d) => d.processing_status === 'processing' || d.processing_status === 'pending'
    );
    useEffect(() => {
        if (!hasProcessing || !companyId) return;
        const interval = setInterval(fetchDocuments, 3000);
        return () => clearInterval(interval);
    }, [hasProcessing, companyId, fetchDocuments]);

    const handleUpload = async () => {
        if (!selectedFile || !companyId) return;
        setUploading(true);
        setError(null);
        try {
            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('document_type', documentType);
            await api.uploadCompanyDocumentIngestion(companyId, formData);
            setSelectedFile(null);
            await fetchDocuments();
        } catch (e) {
            setError(e.message || 'Upload failed.');
        } finally {
            setUploading(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragActive(false);
        const file = e.dataTransfer?.files?.[0];
        if (file) setSelectedFile(file);
    };
    const handleDragOver = (e) => {
        e.preventDefault();
        setDragActive(true);
    };
    const handleDragLeave = () => setDragActive(false);
    const handleFileChange = (e) => {
        const file = e.target?.files?.[0];
        if (file) setSelectedFile(file);
    };

    const statusBadge = (status) => {
        const map = {
            pending: { label: 'Pending', variant: 'secondary', Icon: Clock },
            processing: { label: 'Processing', variant: 'default', Icon: Loader2 },
            complete: { label: 'Complete', variant: 'success', Icon: CheckCircle },
            failed: { label: 'Failed', variant: 'destructive', Icon: XCircle },
        };
        const { label, Icon } = map[status] || { label: status, Icon: FileText };
        return (
            <Badge
                key={status}
                variant={map[status]?.variant || 'secondary'}
                className="flex items-center gap-1"
            >
                {status === 'processing' && <Loader2 className="h-3 w-3 animate-spin" />}
                <Icon className="h-3 w-3" />
                {label}
            </Badge>
        );
    };

    if (!companyId) return null;

    return (
        <Card className="bg-surface border-border-subtle">
            <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                    <Upload className="h-5 w-5" />
                    Document upload
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="flex flex-wrap gap-2 items-center">
                    <span className="text-sm text-text-sec">Type:</span>
                    <select
                        className="h-9 rounded-md border border-input bg-surface px-3 text-sm"
                        value={documentType}
                        onChange={(e) => setDocumentType(e.target.value)}
                    >
                        {DOCUMENT_TYPES.map((t) => (
                            <option key={t} value={t}>
                                {t.replace(/_/g, ' ')}
                            </option>
                        ))}
                    </select>
                </div>
                <div
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    className={cn(
                        'border-2 border-dashed rounded-lg p-6 text-center transition-colors',
                        dragActive ? 'border-primary bg-primary/5' : 'border-border-subtle bg-surface-alt'
                    )}
                >
                    <input
                        type="file"
                        accept={ACCEPT}
                        onChange={handleFileChange}
                        className="hidden"
                        id="doc-upload"
                    />
                    <label htmlFor="doc-upload" className="cursor-pointer block">
                        {selectedFile ? (
                            <span className="text-text-pri font-medium">{selectedFile.name}</span>
                        ) : (
                            <span className="text-text-sec">
                                Drag and drop or click to select (PDF, TXT, DOCX)
                            </span>
                        )}
                    </label>
                </div>
                <Button
                    onClick={handleUpload}
                    disabled={!selectedFile || uploading}
                    className="w-full sm:w-auto"
                >
                    {uploading ? (
                        <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Uploading…
                        </>
                    ) : (
                        <>
                            <Upload className="h-4 w-4 mr-2" />
                            Upload
                        </>
                    )}
                </Button>
                {error && (
                    <div className="flex items-center gap-2 text-danger text-sm">
                        <AlertCircle className="h-4 w-4 shrink-0" />
                        {error}
                    </div>
                )}
                {loading ? (
                    <div className="text-text-sec text-sm">Loading documents…</div>
                ) : documents.length === 0 ? (
                    <div className="text-text-sec text-sm">No documents uploaded yet.</div>
                ) : (
                    <ul className="space-y-2">
                        {documents.map((d) => (
                            <li
                                key={d.id}
                                className="flex items-center justify-between gap-2 py-2 border-b border-border-subtle last:border-0"
                            >
                                <span className="text-sm text-text-pri truncate flex-1">
                                    {d.filename}
                                </span>
                                {statusBadge(d.processing_status)}
                                {d.error_message && (
                                    <span className="text-xs text-danger truncate max-w-[120px]">
                                        {d.error_message}
                                    </span>
                                )}
                            </li>
                        ))}
                    </ul>
                )}
            </CardContent>
        </Card>
    );
}

