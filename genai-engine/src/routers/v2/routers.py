from .dataset_management_routes import dataset_management_routes
from .feedback_routes import feedback_routes
from .query_routes import query_routes
from .rule_management_routes import rule_management_routes
from .system_management_routes import system_management_routes
from .task_management_routes import task_management_routes
from .validate_routes import validate_routes

all = [
    feedback_routes,
    query_routes,
    rule_management_routes,
    system_management_routes,
    task_management_routes,
    validate_routes,
    dataset_management_routes,
]
