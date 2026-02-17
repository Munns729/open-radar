/**
 * MoatBreakdown Component Tests — NEEDS REWRITE.
 *
 * Previously tested with hardcoded Picard pillar names (geographic, liability, physical).
 * MoatBreakdown is now thesis-driven — it renders whatever pillar keys appear in the
 * attributes prop, filtering out deal_screening and risk_penalty.
 *
 * TODO: Rewrite to test with arbitrary pillar keys (e.g. retention, data_asset, integration)
 * and verify dynamic rendering, color cycling, and icon fallback behavior.
 *
 * For backend coverage, see: tests/unit/test_thesis_configurability.py
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MoatBreakdown } from '../MoatBreakdown';

describe('MoatBreakdown Component', () => {
    it('renders nothing when attributes are missing', () => {
        const { container } = render(<MoatBreakdown attributes={null} />);
        expect(container.firstChild).toBeNull();
    });

    it('renders present moat attributes from any thesis', () => {
        const attributes = {
            retention: { present: true, score: 80, justification: '130% NRR' },
            data_asset: { present: true, score: 60, justification: 'Proprietary dataset' },
            integration: { present: false, score: 0, justification: '' },
        };

        render(<MoatBreakdown attributes={attributes} />);

        expect(screen.getByText('80')).toBeInTheDocument();
        expect(screen.getByText('60')).toBeInTheDocument();
    });

    it('ignores deal_screening and risk_penalty keys', () => {
        const attributes = {
            regulatory: { present: true, score: 70, justification: 'AS9100' },
            network: { present: false, score: 0, justification: '' },
            deal_screening: {
                financial_fit: { score: 50, factors: ['Revenue fit'] },
                competitive_position: { score: 15, factors: ['Market Leader'] }
            },
            risk_penalty: { present: true, justification: 'administration', score: -10 }
        };

        render(<MoatBreakdown attributes={attributes} />);

        expect(screen.getByText('70')).toBeInTheDocument();
        expect(screen.queryByText('50')).not.toBeInTheDocument();
        expect(screen.queryByText('-10')).not.toBeInTheDocument();
    });

    it('hides attributes that are not present or have score 0', () => {
        const attributes = {
            alpha: { present: false, score: 80, justification: 'Test' },
            beta: { present: true, score: 0, justification: 'Test' },
            gamma: { present: true, score: 50, justification: 'Real evidence' },
        };

        render(<MoatBreakdown attributes={attributes} />);

        expect(screen.queryByText('80')).not.toBeInTheDocument();
        expect(screen.getByText('50')).toBeInTheDocument();
    });
});
