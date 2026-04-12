from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from routers.auth import get_current_user
from schemas.strategy import (
    CompileBlocksOut,
    StrategyIn,
    StrategyOut,
    StrategyPatch,
    ValidateCodeIn,
    ValidateCodeOut,
)
from services import strategy as strategy_svc
from services.block_compiler import compile_blocks
from services.python_validator import validate

router = APIRouter(prefix="/strategies", tags=["strategies"])


def _out(s) -> StrategyOut:
    return StrategyOut(
        id=s.id,
        name=s.name,
        description=s.description,
        blocks=s.blocks,
        python_code=s.python_code,
        user_id=s.user_id,
        created_at=s.created_at.isoformat(),
        updated_at=s.updated_at.isoformat(),
    )


@router.get("", response_model=List[StrategyOut])
async def list_strategies(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
) -> List[StrategyOut]:
    strategies = await strategy_svc.list_strategies(db, user.id if user else None)
    return [_out(s) for s in strategies]


@router.post("", response_model=StrategyOut, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    body: StrategyIn,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
) -> StrategyOut:
    # Auto-compile blocks to Python if no code provided
    if not body.python_code and body.blocks:
        body = body.model_copy(
            update={"python_code": compile_blocks([b.model_dump() for b in body.blocks])}
        )
    elif not body.python_code:
        body = body.model_copy(update={"python_code": compile_blocks([])})

    s = await strategy_svc.create_strategy(db, body, user.id if user else None)
    return _out(s)


@router.get("/{strategy_id}", response_model=StrategyOut)
async def get_strategy(
    strategy_id: str,
    db: AsyncSession = Depends(get_db),
) -> StrategyOut:
    s = await strategy_svc.get_strategy(db, strategy_id)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return _out(s)


@router.patch("/{strategy_id}", response_model=StrategyOut)
async def update_strategy(
    strategy_id: str,
    patch: StrategyPatch,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
) -> StrategyOut:
    s = await strategy_svc.get_strategy(db, strategy_id)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    if s.user_id and (not user or s.user_id != user.id):
        raise HTTPException(status_code=403, detail="Not your strategy")

    # Auto-recompile when blocks change but code is not provided
    if patch.blocks is not None and patch.python_code is None:
        patch = patch.model_copy(
            update={"python_code": compile_blocks([b.model_dump() for b in patch.blocks])}
        )

    s = await strategy_svc.update_strategy(db, s, patch)
    return _out(s)


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
) -> None:
    s = await strategy_svc.get_strategy(db, strategy_id)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    if s.user_id and (not user or s.user_id != user.id):
        raise HTTPException(status_code=403, detail="Not your strategy")
    await strategy_svc.delete_strategy(db, s)


# ── Utility endpoints ─────────────────────────────────────────────────────────

@router.post("/compile", response_model=CompileBlocksOut)
async def compile_strategy_blocks(body: StrategyIn) -> CompileBlocksOut:
    """Compile blocks to Python without saving. Used by the builder UI."""
    code = compile_blocks([b.model_dump() for b in body.blocks])
    return CompileBlocksOut(python_code=code)


@router.post("/validate", response_model=ValidateCodeOut)
async def validate_python_code(body: ValidateCodeIn) -> ValidateCodeOut:
    """Validate user-written Python without saving or executing it."""
    valid, errors = validate(body.code)
    return ValidateCodeOut(valid=valid, errors=errors)
