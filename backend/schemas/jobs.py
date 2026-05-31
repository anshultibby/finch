"""
Scheduled job schemas. A job is a JSON message + starting context files + a
planned execution time. The agent schedules them; a waker runs them.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime

# Recurrence: None = one-off. Otherwise a simple cadence.
Recurrence = Literal["hourly", "daily", "weekly", "weekdays"]
JobStatus = Literal["pending", "running", "done", "failed", "cancelled", "paused"]

# Approx runs-per-week per cadence — for projecting ongoing cost.
RUNS_PER_WEEK = {"hourly": 168, "daily": 7, "weekdays": 5, "weekly": 1}


class JobCreate(BaseModel):
    message: str = Field(description="The instruction the agent runs when the job fires")
    run_at: datetime = Field(description="First/next planned execution time (UTC)")
    recurrence: Optional[Recurrence] = Field(None, description="None = one-off; else repeats on this cadence")
    priority: int = Field(5, ge=0, le=9, description="0 = highest priority, 9 = lowest")
    name: Optional[str] = Field(None, description="Short human-friendly name")
    chat_id: Optional[str] = Field(None, description="Chat to run in / post results to")
    context_paths: List[str] = Field(
        default_factory=list,
        description="Paths of files to include as starting context (references, not copies)",
    )


class JobUpdate(BaseModel):
    """Partial update — only set fields are changed."""
    message: Optional[str] = None
    run_at: Optional[datetime] = None
    recurrence: Optional[Recurrence] = None
    clear_recurrence: bool = Field(False, description="Set true to make a recurring job one-off")
    priority: Optional[int] = Field(None, ge=0, le=9)
    name: Optional[str] = None


class Job(BaseModel):
    id: str
    user_id: str
    name: str
    message: str
    run_at: datetime
    recurrence: Optional[Recurrence] = None
    priority: int = 5
    status: JobStatus = "pending"
    created_at: datetime
    last_run_at: Optional[datetime] = None
    run_count: int = 0
    chat_id: Optional[str] = None
    context_paths: List[str] = Field(default_factory=list)
    last_error: Optional[str] = None
    last_run_credits: int = 0
    credits_spent: int = 0

    @property
    def is_recurring(self) -> bool:
        return self.recurrence is not None

    @property
    def projected_weekly_credits(self) -> int:
        """Estimated ongoing credits/week from the last run's cost."""
        if not self.recurrence or not self.last_run_credits:
            return 0
        return self.last_run_credits * RUNS_PER_WEEK.get(self.recurrence, 0)


class JobList(BaseModel):
    jobs: List[Job]
    recurring_count: int
    oneoff_count: int
    recurring_limit: int
    oneoff_limit: int
