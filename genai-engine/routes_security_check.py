import argparse
import ast
import logging
import os
import sys
from typing import List, Tuple

HTTP_METHODS = {"get", "post", "put", "delete", "patch"}


class EndpointVisitor(ast.NodeVisitor):
    def __init__(self):
        self.endpoints = []
        self.current_decorators = []
        self.router_names = set()  # Track router variable names

    def visit_Assign(self, node):
        # Capture router variable definitions like: router = APIRouter()
        try:
            if (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "APIRouter"
            ):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.router_names.add(target.id)
        except Exception:
            pass
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        """Handle async function definitions the same way as regular functions"""
        self.visit_FunctionDef(node)

    def visit_FunctionDef(self, node):
        # Reset decorators for new function
        self.current_decorators = []
        # Visit decorators first
        for decorator in node.decorator_list:
            self.visit(decorator)

        # Check if this is an endpoint function
        is_endpoint = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if hasattr(decorator.func, "value") and isinstance(
                    decorator.func.value,
                    ast.Name,
                ):
                    # Check against known router names and captured router variables
                    router_id = decorator.func.value.id
                    if router_id in self.router_names:
                        is_endpoint = True
                        break
                elif isinstance(decorator.func, ast.Name):
                    # Direct route decorators
                    if decorator.func.id in HTTP_METHODS:
                        is_endpoint = True
                        break
                elif isinstance(decorator.func, ast.Attribute):
                    # Handle cases like router.get, router.post, etc.
                    if decorator.func.attr in HTTP_METHODS:
                        is_endpoint = True
                        break

            # Check for direct router decorators (e.g., @auth.get)
            elif isinstance(decorator, ast.Attribute):
                if (
                    decorator.attr in HTTP_METHODS
                    and hasattr(decorator.value, "id")
                    and decorator.value.id in self.router_names
                ):
                    is_endpoint = True
                    break

        if is_endpoint:
            has_permission_checker = any(
                isinstance(d, ast.Call)
                and hasattr(d.func, "id")
                and d.func.id == "permission_checker"
                for d in node.decorator_list
            )
            is_public = any(
                isinstance(d, ast.Name) and d.id == "public_endpoint"
                for d in node.decorator_list
            )
            self.endpoints.append(
                {
                    "name": node.name,
                    "line_number": node.lineno,
                    "has_permission_checker": has_permission_checker,
                    "is_public": is_public,
                    "decorators": self.current_decorators,
                    "file_path": None,  # Will be set later
                },
            )

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.current_decorators.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            if hasattr(node.func.value, "id"):
                self.current_decorators.append(f"{node.func.value.id}.{node.func.attr}")


def analyze_file(file_path: str) -> List[dict]:
    with open(file_path, "r") as file:
        tree = ast.parse(file.read())
        visitor = EndpointVisitor()
        visitor.visit(tree)
        for endpoint in visitor.endpoints:
            endpoint["file_path"] = file_path
        return visitor.endpoints


def analyze_routers_directory(
    directory_path: str = "genai_engine/routers",
) -> List[Tuple[str, List[dict]]]:
    results = []

    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                file_path = os.path.join(root, file)
                try:
                    endpoints = analyze_file(file_path)
                    if endpoints:
                        relative_path = os.path.relpath(file_path, directory_path)
                        results.append((relative_path, endpoints))
                except Exception as e:
                    print(f"Error analyzing {file_path}: {str(e)}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Analyze endpoint security in router files.",
    )
    parser.add_argument(
        "--short",
        action="store_true",
        help="Print only unprotected endpoints",
    )
    parser.add_argument(
        "--files-summary",
        action="store_true",
        help="Print summary for each file",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, args.log_level.upper()),
    )

    results = analyze_routers_directory()

    total_endpoints = 0
    protected_endpoints = 0
    public_endpoints = 0
    unprotected_endpoints = []
    total_files = len(results)

    # Collect file-level statistics
    file_stats = []

    if not args.short and not args.files_summary:
        logging.debug("Endpoint Security Analysis Report")
        logging.debug("================================")

    for file_path, endpoints in sorted(results):
        file_total = len(endpoints)
        file_protected = sum(1 for e in endpoints if e["has_permission_checker"])
        file_public = sum(1 for e in endpoints if e["is_public"])
        file_unprotected = file_total - file_protected - file_public

        file_stats.append(
            {
                "path": file_path,
                "total": file_total,
                "protected": file_protected,
                "public": file_public,
                "unprotected": file_unprotected,
            },
        )

        if not args.short and not args.files_summary:
            logging.debug(f"\nFile: {file_path}")
            logging.debug("-" * (len(file_path) + 6))

        for endpoint in endpoints:
            total_endpoints += 1
            if endpoint["has_permission_checker"]:
                protected_endpoints += 1
            elif endpoint["is_public"]:
                public_endpoints += 1
            else:
                unprotected_endpoints.append((file_path, endpoint))

            if not args.short and not args.files_summary:
                if endpoint["has_permission_checker"]:
                    security_status = "✓ Protected"
                elif endpoint["is_public"]:
                    security_status = "○ Public (Intentional)"
                else:
                    security_status = "✗ Unprotected"
                logging.debug(f"Line {endpoint['line_number']}: {endpoint['name']}")
                logging.debug(f"Security: {security_status}")
                logging.debug(f"Decorators: {', '.join(endpoint['decorators'])}")
                logging.debug("")

    # Print appropriate summary based on arguments
    if args.files_summary:
        logging.info("File Summary")
        logging.info("============")
        for stats in file_stats:
            logging.info(f"\n{stats['path']}")
            logging.info(f"Total Endpoints:{stats['total']:>3}")
            logging.info(f"Protected:{stats['protected']:>9}")
            logging.info(f"Public:{stats['public']:>12}")
            logging.info(f"Unprotected:{stats['unprotected']:>7}")

    logging.info("Summary")
    logging.info("=======")
    logging.info(f"Files Scanned:{total_files:>11}")
    logging.info(f"Total Endpoints:{total_endpoints:>9}")
    logging.info(f"Protected Endpoints:{protected_endpoints:>5}")
    logging.info(f"Public Endpoints:{public_endpoints:>8}")
    logging.info(f"Unprotected Endpoints:{len(unprotected_endpoints):>3}")

    if unprotected_endpoints:
        logging.info(
            "\nUnprotected Endpoints (require @permission_checker or @public_endpoint):",
        )
        logging.info("================================================================")
        for file_path, endpoint in unprotected_endpoints:
            logging.info(f"{file_path}:{endpoint['line_number']} - {endpoint['name']}")
    else:
        logging.info(
            "\nAll endpoints are either protected or explicitly marked as public! 🎉",
        )

    # Exit with failure if there are unprotected endpoints
    if unprotected_endpoints:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
