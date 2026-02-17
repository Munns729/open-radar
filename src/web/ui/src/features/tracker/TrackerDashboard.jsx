import React, { useState } from 'react';
import TrackerList from './TrackerList';
import AlertsFeed from './AlertsFeed';
import { Button } from '@/components/ui/Button';
import { Plus, Bell, Target } from 'lucide-react';
import AddTargetModal from './AddTargetModal';

export default function TrackerDashboard() {
    const [isAddModalOpen, setIsAddModalOpen] = useState(false);
    const [refreshTrigger, setRefreshTrigger] = useState(0);

    const handleRefresh = () => {
        setRefreshTrigger(prev => prev + 1);
    };

    return (
        <div className="h-full flex flex-col space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-text-pri flex items-center gap-2">
                        <Target className="h-8 w-8 text-primary" />
                        Target Tracker
                    </h1>
                    <p className="text-text-sec mt-1">
                        Monitor high-priority targets and track key lifecycle events.
                    </p>
                </div>
                <div className="flex gap-3">
                    <Button onClick={() => setIsAddModalOpen(true)} className="flex items-center gap-2">
                        <Plus className="h-4 w-4" />
                        Add Target
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-full min-h-0">
                {/* Main Content - Tracker List */}
                <div className="lg:col-span-3 h-full flex flex-col min-h-0">
                    <TrackerList key={refreshTrigger} />
                </div>

                {/* Sidebar - Alerts Feed */}
                <div className="lg:col-span-1 h-full min-h-0 overflow-y-auto">
                    <AlertsFeed />
                </div>
            </div>

            {/* Add Target Modal */}
            {isAddModalOpen && (
                <AddTargetModal
                    isOpen={isAddModalOpen}
                    onClose={() => setIsAddModalOpen(false)}
                    onSuccess={handleRefresh}
                />
            )}
        </div>
    );
}
