from arthur_client.api_bindings import Model


def validate_schedule(model: Model, schedule_id: str) -> None:
    if not model.schedule:
        raise ValueError(
            "Model does not define a schedule matching the job's schedule id. It may have been deleted or modified.",
        )
    elif model.schedule.id != schedule_id:
        raise ValueError(
            "Model's schedule id does not match the job's schedule id. It may have been modified.",
        )
