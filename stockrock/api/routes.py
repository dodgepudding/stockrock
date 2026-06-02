from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import asyncio

from stockrock.engine.screener import Screener, get_job
from stockrock.engine.universe import UniverseFilter
from stockrock.strategies.base import list_strategies
from stockrock.strategies.params import normalize_strategy_params

router = APIRouter(prefix="/api")


class ScreenRequest(BaseModel):
    strategy_id: str
    provider: str = "akshare"
    lookback_days: int = 120
    exclude_st: bool = True
    exclude_bj: bool = True
    include_kcb: bool = True
    include_cyb: bool = True
    max_symbols: int | None = Field(default=None, description="Limit for testing")
    strategy_params: dict | None = Field(
        default=None,
        description="Strategy-specific params, e.g. cost_period for low_sideways_build",
    )


class ScreenResponse(BaseModel):
    job_id: str


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/strategies")
def strategies():
    return {"strategies": list_strategies()}


@router.post("/screen", response_model=ScreenResponse)
def start_screen(req: ScreenRequest):
    try:
        params = normalize_strategy_params(req.strategy_id, req.strategy_params)
        screener = Screener()
        job_id = screener.start_job(
            strategy_id=req.strategy_id,
            lookback_days=req.lookback_days,
            universe_filter=UniverseFilter(
                exclude_st=req.exclude_st,
                exclude_bj=req.exclude_bj,
                include_kcb=req.include_kcb,
                include_cyb=req.include_cyb,
                max_symbols=req.max_symbols,
            ),
            provider_name=req.provider,
            strategy_params=params,
        )
        return ScreenResponse(job_id=job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/screen/{job_id}")
def screen_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return Screener.job_to_dict(job)


@router.get("/screen/{job_id}/events")
async def screen_events(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_stream():
        last_processed = -1
        while True:
            j = get_job(job_id)
            if not j:
                break
            data = Screener.job_to_dict(j)
            if j.processed != last_processed or j.status in ("completed", "failed"):
                last_processed = j.processed
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            if j.status in ("completed", "failed"):
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
