import React from 'react';
import UniverseGraph from './features/network/UniverseGraph';

const NetworkPage = () => {
    return (
        <div className="container mx-auto p-6 h-[calc(100vh-4rem)] flex flex-col gap-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight text-foreground">
                    Network Intelligence
                </h1>
                <p className="text-muted-foreground">
                    Explore the connected universe of companies, suppliers, and partners.
                </p>
            </div>

            <div className="flex-1 min-h-0">
                <UniverseGraph />
            </div>
        </div>
    );
};

export default NetworkPage;
