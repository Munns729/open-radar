import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Bell, CheckCircle, AlertTriangle, Info, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function AlertsFeed() {
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchAlerts();
    }, []);

    const fetchAlerts = async () => {
        try {
            const data = await api.getAlerts({ limit: 20 });
            setAlerts(data);
        } catch (error) {
            console.error("Failed to fetch alerts", error);
        } finally {
            setLoading(false);
        }
    };

    const markAsRead = async (id) => {
        try {
            await api.markAlertRead(id);
            setAlerts(prev => prev.map(a => a.id === id ? { ...a, is_read: true } : a));
        } catch (error) {
            console.error("Failed to mark alert as read", error);
        }
    };

    const getIcon = (type) => {
        switch (type?.toLowerCase()) {
            case 'funding': return <Zap className="h-4 w-4 text-warning" />;
            case 'news': return <Info className="h-4 w-4 text-blue-400" />;
            case 'leadership': return <AlertTriangle className="h-4 w-4 text-danger" />;
            default: return <Bell className="h-4 w-4 text-primary" />;
        }
    };

    return (
        <Card className="h-full bg-surface border-border-subtle flex flex-col">
            <CardHeader className="pb-3 border-b border-border-subtle">
                <CardTitle className="flex items-center gap-2 text-lg">
                    <Bell className="h-5 w-5" />
                    Recent Alerts
                </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-0">
                {loading ? (
                    <div className="p-4 text-center text-text-sec text-sm">Loading alerts...</div>
                ) : alerts.length === 0 ? (
                    <div className="p-8 text-center text-text-ter text-sm">
                        No active alerts.
                    </div>
                ) : (
                    <div className="divide-y divide-border-subtle">
                        {alerts.map(alert => (
                            <div
                                key={alert.id}
                                className={cn(
                                    "p-4 transition-colors hover:bg-surface-alt group relative",
                                    !alert.is_read ? "bg-primary/5" : ""
                                )}
                            >
                                <div className="flex gap-3">
                                    <div className="mt-1 flex-shrink-0">
                                        {getIcon(alert.alert_type)}
                                    </div>
                                    <div className="flex-1 space-y-1">
                                        <p className="text-sm font-medium text-text-pri leading-snug">
                                            {alert.message}
                                        </p>
                                        <div className="flex justify-between items-center text-xs text-text-ter">
                                            <span>
                                                {new Date(alert.created_at).toLocaleDateString()}
                                            </span>
                                            {!alert.is_read && (
                                                <button
                                                    onClick={() => markAsRead(alert.id)}
                                                    className="opacity-0 group-hover:opacity-100 transition-opacity text-primary hover:text-primary-hover flex items-center gap-1"
                                                >
                                                    <CheckCircle className="h-3 w-3" />
                                                    Mark read
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
