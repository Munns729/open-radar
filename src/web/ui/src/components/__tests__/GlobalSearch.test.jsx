import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import GlobalSearch from '../GlobalSearch';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useNavigate: () => mockNavigate,
    };
});

// Mock fetch
global.fetch = vi.fn();

describe('GlobalSearch Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        fetch.mockReset();
    });

    it('renders the search trigger button', () => {
        render(
            <MemoryRouter>
                <GlobalSearch />
            </MemoryRouter>
        );
        expect(screen.getByText('Search...')).toBeInTheDocument();
        expect(screen.getByText('K')).toBeInTheDocument();
    });

    it('opens the search modal when clicking the trigger button', () => {
        render(
            <MemoryRouter>
                <GlobalSearch />
            </MemoryRouter>
        );

        fireEvent.click(screen.getByText('Search...'));
        expect(screen.getByPlaceholderText(/Search companies, contacts, deals/i)).toBeInTheDocument();
    });

    it('shows loading state and results when typing', async () => {
        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                companies: [{ id: 1, name: 'Test Corp', sector: 'Tech' }],
                contacts: [],
                deals: []
            })
        });

        render(
            <MemoryRouter>
                <GlobalSearch />
            </MemoryRouter>
        );

        fireEvent.click(screen.getByText('Search...'));
        const input = screen.getByPlaceholderText(/Search companies, contacts, deals/i);

        await act(async () => {
            fireEvent.change(input, { target: { value: 'Test' } });
        });

        // Search is debounced by 300ms, so we wait
        await waitFor(() => {
            expect(screen.getByText('Test Corp')).toBeInTheDocument();
        }, { timeout: 1000 });

        expect(screen.getByText('Tech')).toBeInTheDocument();
    });

    it('navigates when clicking a result', async () => {
        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                companies: [{ id: 1, name: 'Test Corp', sector: 'Tech' }],
                contacts: [],
                deals: []
            })
        });

        render(
            <MemoryRouter>
                <GlobalSearch />
            </MemoryRouter>
        );

        fireEvent.click(screen.getByText('Search...'));
        fireEvent.change(screen.getByPlaceholderText(/Search companies, contacts, deals/i), { target: { value: 'Test' } });

        await waitFor(() => screen.getByText('Test Corp'));

        fireEvent.click(screen.getByText('Test Corp'));

        expect(mockNavigate).toHaveBeenCalledWith('/universe?search=Test%20Corp');
    });

    it('closes the modal when pressing Escape', async () => {
        render(
            <MemoryRouter>
                <GlobalSearch />
            </MemoryRouter>
        );

        fireEvent.click(screen.getByText('Search...'));
        expect(screen.queryByPlaceholderText(/Search companies, contacts, deals/i)).toBeInTheDocument();

        fireEvent.keyDown(document, { key: 'Escape' });

        await waitFor(() => {
            expect(screen.queryByPlaceholderText(/Search companies, contacts, deals/i)).not.toBeInTheDocument();
        });
    });
});
