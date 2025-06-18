import pytest
from mock_data.mock_data_generator import random_model
from tools.validators import validate_schedule


def test_validate_schedule_with_valid_data():
    model = random_model()
    validate_schedule(model, "test_schedule_id")  # Should not raise an exception


def test_validate_schedule_with_no_model_schedule():
    model = random_model()
    model.schedule = None
    with pytest.raises(
        ValueError,
        match="Model does not define a schedule matching the job's schedule id.",
    ):
        validate_schedule(model, "test_schedule_id")


def test_validate_schedule_with_mismatched_schedule_id():
    model = random_model()
    model.schedule.id = "model_schedule_id"
    with pytest.raises(
        ValueError,
        match="Model's schedule id does not match the job's schedule id.",
    ):
        validate_schedule(model, "job_schedule_id")
