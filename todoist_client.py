import os
from contextlib import asynccontextmanager
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

MCP_URL = "https://ai.todoist.net/mcp"


class TodoistClient:
    def __init__(self, session: ClientSession):
        self._session = session

    async def fetch_tasks(self, project_id: str, limit: int = 100) -> list[dict]:
        result = await self._session.call_tool(
            "find-tasks", {"projectId": project_id, "limit": limit}
        )
        return result.structuredContent["tasks"]

    async def update_task_due(self, task_id: str, due_string: str) -> None:
        await self._session.call_tool(
            "update-tasks", {"tasks": [{"id": task_id, "dueString": due_string}]}
        )


@asynccontextmanager
async def create_client_session():
    headers = {"Authorization": f"Bearer {os.environ.get('TODOIST_API_TOKEN')}"}
    async with streamablehttp_client(MCP_URL, headers=headers) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            yield TodoistClient(session)
