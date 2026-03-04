from pydantic import BaseModel, Field


class ExecutePollingResponse(BaseModel):
    """Response model for the single-task agent polling endpoint."""

    status: str = Field(description="Status of the operation")
    task_id: str = Field(description="Task ID that was enqueued")


class DiscoverAndPollResponse(BaseModel):
    """Response model for the execute-all agent polling endpoint."""

    status: str = Field(description="Status of the operation")
    discovered: int = Field(description="Number of new agent tasks created")
    traces_fetched: int = Field(
        description="Total number of traces fetched across all tasks (0 in async mode)"
    )
