"""
Diagnostic script to check Universe Database content.
"""
import asyncio
from sqlalchemy import select, func
from src.core.database import async_session_factory
from src.universe.database import CompanyModel

from sqlalchemy import text

async def inspect_db():
    async with async_session_factory() as session:
        # 0. List Tables
        print("Checking tables in DB...")
        from sqlalchemy import inspect
        
        def get_tables(conn):
            return inspect(conn).get_table_names()
            
        tables = await session.connection().run_sync(get_tables)
        print(f"Tables found: {tables}")
        
        if 'companies' not in tables:
            print("CRITICAL: 'companies' table NOT found.")
            return

        # 1. Count Companies
        stmt = select(func.count(CompanyModel.id))
        result = await session.execute(stmt)
        count = result.scalar()
        print(f"Total Companies in 'companies' table: {count}")
        
        if count == 0:
            return

        # 2. Check for Revenue Data
        stmt = select(CompanyModel).where(CompanyModel.revenue_gbp.isnot(None)).limit(5)
        result = await session.execute(stmt)
        companies_with_rev = result.scalars().all()
        
        print(f"\nSample Companies with Revenue:")
        for c in companies_with_rev:
            print(f" - {c.name}: £{c.revenue_gbp:,.2f}")
            
        # 3. Check for specific targets > £150M
        stmt = select(CompanyModel).where(CompanyModel.revenue_gbp > 150000000)
        result = await session.execute(stmt)
        targets = result.scalars().all()
        print(f"\nCompanies with > £150M Revenue: {len(targets)}")
        for t in targets[:5]:
            print(f" - {t.name}: £{t.revenue_gbp:,.2f}")

if __name__ == "__main__":
    asyncio.run(inspect_db())
