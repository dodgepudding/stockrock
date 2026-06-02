import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

import pandas as pd

from stockrock import config
from stockrock.data.cached_provider import CachedDataProvider
from stockrock.data.capital import get_capital_hands
from stockrock.engine.universe import UniverseFilter, build_universe
from stockrock.strategies.base import Strategy, get_strategy
from stockrock.watchlist.quotes import fetch_major_sectors


@dataclass
class ScreenResult:
    code: str
    name: str
    close: float
    date: str
    extra: dict = field(default_factory=dict)


@dataclass
class ScreenJob:
    job_id: str
    strategy_id: str
    status: str = "pending"
    total: int = 0
    processed: int = 0
    hits: list[ScreenResult] = field(default_factory=list)
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


_jobs: dict[str, ScreenJob] = {}
_jobs_lock = threading.Lock()


def get_job(job_id: str) -> ScreenJob | None:
    with _jobs_lock:
        return _jobs.get(job_id)


class Screener:
    def __init__(
        self,
        provider: CachedDataProvider | None = None,
        universe_filter: UniverseFilter | None = None,
        max_workers: int | None = None,
    ):
        self.provider = provider or CachedDataProvider()
        self.universe_filter = universe_filter or UniverseFilter()
        self.max_workers = max_workers if max_workers is not None else config.SCREEN_WORKERS

    def _screen_symbol(
        self,
        code: str,
        name: str,
        strategy: Strategy,
        start: str,
        end: str,
        min_bars: int,
    ) -> ScreenResult | None:
        try:
            df = self.provider.get_daily_bars(
                symbol=code, start=start, end=end, adjust="qfq"
            )
            if df is None or len(df) < min_bars:
                return None
            capital_hands = None
            if getattr(strategy, "needs_capital", False):
                capital_hands = get_capital_hands(code)
                if not capital_hands:
                    return None
            if strategy.latest_signal(
                df,
                lookback_days=1,
                code=code,
                name=name,
                capital_hands=capital_hands,
            ):
                last = df.iloc[-1]
                return ScreenResult(
                    code=code,
                    name=name,
                    close=float(last["close"]),
                    date=last["date"].strftime("%Y-%m-%d")
                    if hasattr(last["date"], "strftime")
                    else str(last["date"])[:10],
                )
        except Exception:
            pass
        return None

    def run(
        self,
        strategy: Strategy,
        lookback_days: int | None = None,
        on_progress: Callable[[int, int], None] | None = None,
        end_date: str | None = None,
    ) -> list[ScreenResult]:
        lookback = lookback_days or config.LOOKBACK_DAYS
        min_bars = getattr(strategy, "min_bars", 30)
        calendar_days = max(lookback + 60, int(min_bars * 1.6) + 60)
        universe = build_universe(self.provider, self.universe_filter)
        end = end_date or datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=calendar_days)).strftime(
            "%Y-%m-%d"
        )

        symbols = [(str(row["code"]), str(row["name"])) for _, row in universe.iterrows()]
        total = len(symbols)
        if total == 0:
            return []

        results: list[ScreenResult] = []
        progress_lock = threading.Lock()
        done = 0

        def on_one_complete():
            nonlocal done
            with progress_lock:
                done += 1
                if on_progress:
                    on_progress(done, total)

        workers = max(1, self.max_workers)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    self._screen_symbol, code, name, strategy, start, end, min_bars
                )
                for code, name in symbols
            ]
            for future in as_completed(futures):
                hit = future.result()
                if hit is not None:
                    results.append(hit)
                on_one_complete()

        return results

    def start_job(
        self,
        strategy_id: str,
        lookback_days: int | None = None,
        universe_filter: UniverseFilter | None = None,
        provider_name: str | None = None,
        strategy_params: dict | None = None,
    ) -> str:
        from stockrock.data.base import get_provider

        job_id = str(uuid.uuid4())
        job = ScreenJob(
            job_id=job_id,
            strategy_id=strategy_id,
            status="running",
            started_at=datetime.now().isoformat(),
        )
        with _jobs_lock:
            _jobs[job_id] = job

        filt = universe_filter or self.universe_filter
        provider = CachedDataProvider(
            provider=get_provider(provider_name)  # type: ignore[arg-type]
        )

        def worker():
            try:
                strategy = get_strategy(strategy_id, params=strategy_params)
                screener = Screener(provider=provider, universe_filter=filt)
                universe = build_universe(provider, filt)
                with _jobs_lock:
                    job.total = len(universe)

                def on_progress(done: int, total: int):
                    with _jobs_lock:
                        job.processed = done

                hits = screener.run(strategy, lookback_days=lookback_days, on_progress=on_progress)
                sectors = fetch_major_sectors([h.code for h in hits])
                for h in hits:
                    sector = sectors.get(h.code)
                    if sector:
                        h.extra["major_sector"] = sector
                with _jobs_lock:
                    job.hits = hits
                    job.processed = job.total
                    job.status = "completed"
                    job.finished_at = datetime.now().isoformat()
            except Exception as e:
                with _jobs_lock:
                    job.status = "failed"
                    job.error = str(e)
                    job.finished_at = datetime.now().isoformat()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return job_id

    @staticmethod
    def job_to_dict(job: ScreenJob) -> dict:
        return {
            "job_id": job.job_id,
            "strategy_id": job.strategy_id,
            "status": job.status,
            "total": job.total,
            "processed": job.processed,
            "progress": job.processed / job.total if job.total else 0,
            "hits": [
                {
                    "code": h.code,
                    "name": h.name,
                    "close": h.close,
                    "date": h.date,
                    **h.extra,
                }
                for h in job.hits
            ],
            "error": job.error,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
        }
