import starlette
from fastapi import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        # There are various operating system limitations that limit the max file path, the lowest seems to be mac at 255. Throw a 404 so we don't 500.
        if len(path) >= 255:
            raise HTTPException(status_code=404)
        try:
            return await super().get_response(path, scope)
        except starlette.middleware.exceptions.HTTPException as ex:
            if ex.status_code == 404:
                # Handle specific legacy routes
                if path in [
                    "chat",
                    "login",
                    "logout",
                    "inferences",
                    "admin/inference-deep-dive",
                    "admin/tasks",
                    "admin/index.tsx",
                ]:
                    return await super().get_response("index.html", scope)
                # Handle React SPA routes - any route starting with tasks or root
                elif path.startswith("tasks") or path == "":
                    return await super().get_response("index.html", scope)
                else:
                    raise ex
            else:
                raise ex
