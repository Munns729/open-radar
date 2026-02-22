import React from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import Dashboard from './Dashboard';
import UniverseTable from '@/features/universe/UniverseTable';
import CompetitiveFeed from '@/features/competitive/CompetitiveFeed';
import CarveoutBoard from '@/features/carveout/CarveoutBoard';
import CapitalFlows from '@/features/capital/CapitalFlows';
import Reports from './Reports';
import PlaceholderPage from '@/components/PlaceholderPage';
import ThesisValidator from '@/features/thesis/ThesisValidator';
import IntelligenceDashboard from '@/features/intelligence/IntelligenceDashboard';
import DealDetail from '@/features/intelligence/DealDetail';
import TrackerDashboard from '@/features/tracker/TrackerDashboard';
import TrackerDetail from '@/features/tracker/TrackerDetail';
import RelationshipsDashboard from '@/features/relationships';
import IntelDashboard from '@/features/intel/IntelDashboard';

import NetworkPage from './NetworkPage';

// Page title mapping for routes
const PAGE_TITLES = {
  '/': 'Dashboard',
  '/universe': 'Universe Scanner',
  '/network': 'Network Graph',
  '/tracker': 'Target Tracker',
  '/intelligence': 'Deal Intelligence',
  '/competitive': 'Competitive Radar',
  '/intel': 'Market Intel',
  '/portfolio': 'Portfolio',
  '/relationships': 'Relationships',
  '/capital': 'Capital Flows',
  '/carveout': 'Carveouts',
  '/thesis': 'Thesis Validator',
  '/reports': 'Reports',
  '/settings': 'Settings'
};

import { CurrencyProvider } from '@/context/CurrencyContext';

function App() {
  const location = useLocation();
  const pageTitle = PAGE_TITLES[location.pathname] || 'RADAR';

  return (
    <CurrencyProvider>
      <DashboardLayout pageTitle={pageTitle}>
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/universe" element={<UniverseTable />} />
            <Route path="/network" element={<NetworkPage />} />
            <Route path="/intelligence" element={<IntelligenceDashboard />} />
            <Route path="/intelligence/:id" element={<DealDetail />} />

            <Route path="/tracker" element={<TrackerDashboard />} />
            <Route path="/tracker/:id" element={<TrackerDetail />} />
            <Route path="/competitive" element={<CompetitiveFeed />} />
            <Route path="/intel" element={<IntelDashboard />} />
            <Route path="/portfolio" element={<PlaceholderPage title="Portfolio" description="Track and monitor your existing portfolio companies." />} />
            <Route path="/relationships" element={<RelationshipsDashboard />} />
            <Route path="/capital" element={<CapitalFlows />} />
            <Route path="/carveout" element={<CarveoutBoard />} />
            <Route path="/thesis" element={<ThesisValidator />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<PlaceholderPage title="Settings" description="Configure RADAR settings, API keys, and preferences." />} />
          </Routes>
        </AnimatePresence>
      </DashboardLayout>
    </CurrencyProvider>
  );
}

export default App;
