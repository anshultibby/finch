"""
Scheduled job schemas.

An automation is a time + an instruction. Both the user (via /jobs) and the
agent (via schedule_job in the finch_api skill) create them the same way.
"""
import re

from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime

# None = one-off. Named cadences are what users and the agent pick;
# "every_<N>m" is additionally accepted for minute-level built-ins (heartbeat),
# which is why the read DTO types recurrence as a plain str.
Recurrence = Literal["hourly", "daily", "weekly", "weekdays"]
JobStatus = Literal["pending", "running", "done", "failed", "cancelled", "paused"]

# Approx runs-per-week per cadence — for projecting ongoing cost.
RUNS_PER_WEEK = {"hourly": 168, "daily": 7, "weekdays": 5, "weekly": 1}


class JobCreate(BaseModel):
    message: str = Field(description="The instruction the agent runs when the job fires")
    run_at: datetime = Field(description="First/next planned execution time (UTC)")
    recurrence: Optional[Recurrence] = Field(None, description="None = one-off; else repeats on this cadence")
    name: Optional[str] = Field(None, description="Short human-friendly name")


class JobUpdate(BaseModel):
    """Partial update — only set fields are changed."""
    message: Optional[str] = None
    run_at: Optional[datetime] = None
    recurrence: Optional[Recurrence] = None
    clear_recurrence: bool = Field(False, description="Set true to make a recurring job one-off")
    name: Optional[str] = None


class Job(BaseModel):
    id: str
    user_id: str
    name: str
    message: str
    run_at: datetime
    recurrence: Optional[str] = None  # named cadence or "every_<N>m"
    status: JobStatus = "pending"
    created_at: datetime
    last_run_at: Optional[datetime] = None
    run_count: int = 0
    last_error: Optional[str] = None
    last_run_credits: int = 0
    credits_spent: int = 0
    system_key: Optional[str] = None  # set on Finch-provisioned built-ins
    comped: bool = False
    activity_gated: bool = False
    # Chat the most recent run executed in — exposed once there's something to
    # look at, so the UI can open the execution.
    run_chat_id: Optional[str] = None

    @property
    def is_recurring(self) -> bool:
        return self.recurrence is not None

    @property
    def is_system(self) -> bool:
        return self.system_key is not None

    @property
    def projected_weekly_credits(self) -> int:
        """Estimated ongoing credits/week from the last run's cost."""
        if not self.recurrence or not self.last_run_credits:
            return 0
        runs = RUNS_PER_WEEK.get(self.recurrence, 0)
        if not runs:
            m = re.fullmatch(r"every_(\d+)m", self.recurrence)
            if m:
                runs = 7 * 24 * 60 // max(int(m.group(1)), 5)
        return self.last_run_credits * runs


class JobList(BaseModel):
    jobs: List[Job]
    recurring_count: int
    oneoff_count: int
    recurring_limit: int
    oneoff_limit: int
