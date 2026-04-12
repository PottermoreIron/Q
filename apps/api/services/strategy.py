from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.strategy import Strategy
from schemas.strategy import StrategyIn, StrategyPatch


async def list_strategies(db: AsyncSession, user_id: Optional[str]) -> List[Strategy]:
    stmt = select(Strategy).order_by(Strategy.updated_at.desc())
    if user_id:
        stmt = stmt.where(Strategy.user_id == user_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_strategy(db: AsyncSession, strategy_id: str) -> Optional[Strategy]:
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    return result.scalar_one_or_none()


async def create_strategy(
    db: AsyncSession,
    body: StrategyIn,
    user_id: Optional[str],
) -> Strategy:
    strategy = Strategy(
        name=body.name,
        description=body.description,
        blocks=[b.model_dump() for b in body.blocks],
        python_code=body.python_code,
        user_id=user_id,
    )
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)
    return strategy


async def update_strategy(
    db: AsyncSession,
    strategy: Strategy,
    patch: StrategyPatch,
) -> Strategy:
    if patch.name is not None:
        strategy.name = patch.name
    if patch.description is not None:
        strategy.description = patch.description
    if patch.blocks is not None:
        strategy.blocks = [b.model_dump() for b in patch.blocks]
    if patch.python_code is not None:
        strategy.python_code = patch.python_code
    await db.commit()
    await db.refresh(strategy)
    return strategy


async def delete_strategy(db: AsyncSession, strategy: Strategy) -> None:
    await db.delete(strategy)
    await db.commit()
