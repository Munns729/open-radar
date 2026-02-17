import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../Table';

describe('Table Components', () => {
    it('renders basic table structure correctly', () => {
        render(
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead>Header 1</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    <TableRow>
                        <TableCell>Data 1</TableCell>
                    </TableRow>
                </TableBody>
            </Table>
        );

        expect(screen.getByText('Header 1')).toBeInTheDocument();
        expect(screen.getByText('Data 1')).toBeInTheDocument();
        expect(screen.getByRole('table')).toBeInTheDocument();
    });

    it('applies custom classNames', () => {
        const { container } = render(
            <Table className="custom-table">
                <TableBody>
                    <TableRow className="custom-row">
                        <TableCell className="custom-cell">Data</TableCell>
                    </TableRow>
                </TableBody>
            </Table>
        );

        expect(container.querySelector('.custom-table')).toBeInTheDocument();
        expect(container.querySelector('.custom-row')).toBeInTheDocument();
        expect(container.querySelector('.custom-cell')).toBeInTheDocument();
    });
});
