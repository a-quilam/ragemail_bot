from datetime import datetime
from zoneinfo import ZoneInfo
from app.infra.repo.stats_repo import StatsRepo

class StatsService:
    def __init__(self, repo: StatsRepo, tz: ZoneInfo):
        self.repo = repo
        self.tz = tz

    def _today_key(self) -> str:
        return datetime.now(self.tz).strftime("%Y-%m-%d")

    async def inc(self, key: str) -> None:
        await self.repo.inc(self._today_key(), key)
