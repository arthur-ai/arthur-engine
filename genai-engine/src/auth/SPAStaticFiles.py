import starlette
from fastapi import HTTPException
from starlette.staticfiles import StaticFiles


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        # There are various operating system limitations that limit the max file path, the lowest seems to be mac at 255. Throw a 404 so we don't 500.
        if len(path) >= 255:
            raise HTTPException(status_code=404)
        try:
            return await super().get_response(path, scope)
        except starlette.middleware.exceptions.HTTPException as ex:
            if ex.status_code == 404 and (path in [
                    "chat",
                    "login",
                    "logout",
                    "inferences",
                    "admin/inference-deep-dive",
                    "admin/tasks",
                    "admin/index.tsx",
                ] or path.startswith("tasks/")):
                return await super().get_response("index.html", scope)
            else:
                raise ex
