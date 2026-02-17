import httpx
from notion_client import AsyncClient
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class NotionService:
    def __init__(self):
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {Config.NOTION_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        self.database_id = Config.DATABASE_ID
        self.timeout = 30.0
        # Initialize SDK Client for CRUD operations
        self.client = AsyncClient(auth=Config.NOTION_KEY)

    async def _request(self, method, endpoint, body=None):
        url = f"{self.base_url}/{endpoint}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                if method == "GET":
                    response = await client.get(url, headers=self.headers)
                elif method == "POST":
                    response = await client.post(url, headers=self.headers, json=body)
                elif method == "PATCH":
                    response = await client.patch(url, headers=self.headers, json=body)
                elif method == "DELETE":
                    # Notion uses PATCH/archived for delete, but if we ever need DELETE method
                    response = await client.delete(url, headers=self.headers)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP Error {e.response.status_code}: {e.response.text}")
                raise e
            except Exception as e:
                logger.error(f"Request Error: {e}")
                raise e

    async def get_pending_tasks(self):
        """Fetch all tasks that are not marked as Done"""
        # Kept using httpx because SDK had issues with query
        try:
            body = {
                "filter": {
                    "property": "Status",
                    "select": {
                        "does_not_equal": "Done"
                    }
                }
            }
            response = await self._request("POST", f"databases/{self.database_id}/query", body)
            return response.get("results", [])
        except Exception as e:
            logger.error(f"Error fetching pending tasks: {e}")
            raise e

    async def find_task_by_name(self, name):
        """Search for a task by name"""
        # Kept using httpx because SDK had issues with query
        try:
            body = {
                "filter": {
                    "property": "Name",
                    "title": {
                        "contains": name
                    }
                }
            }
            response = await self._request("POST", f"databases/{self.database_id}/query", body)
            results = response.get("results", [])
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error finding task '{name}': {e}")
            raise e

    async def find_task_by_custom_id(self, task_id: int):
        """Search for a task by its Unique ID number"""
        try:
            body = {
                "filter": {
                    "property": "ID",
                    "unique_id": {
                        "equals": task_id
                    }
                }
            }
            response = await self._request("POST", f"databases/{self.database_id}/query", body)
            results = response.get("results", [])
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error finding task by ID {task_id}: {e}")
            raise e

    async def get_task_by_id(self, page_id):
        """Fetch a single task by its page ID"""
        try:
            return await self.client.pages.retrieve(page_id=page_id)
        except Exception as e:
            logger.error(f"Error fetching task by ID: {e}")
            raise e

    async def update_task(self, page_id, updates):
        """Update a task's properties"""
        properties = {}
        
        if "status" in updates and updates["status"]:
            properties["Status"] = {"select": {"name": updates["status"]}}
        
        if "priority" in updates and updates["priority"]:
            properties["Priority"] = {"select": {"name": updates["priority"]}}

        if "due_date" in updates:
            if updates["due_date"]:
                properties["Due Date"] = {"date": {"start": updates["due_date"]}}

        if "new_title" in updates and updates["new_title"]:
            properties["Name"] = {"title": [{"text": {"content": updates["new_title"]}}]}

        try:
            return await self.client.pages.update(page_id=page_id, properties=properties)
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            raise e

    async def create_task(self, title, status="Pending", priority="Medium", description=None, due_date=None):
        """Create a new task"""
        properties = {
            "Name": {"title": [{"text": {"content": title}}]},
            "Status": {"select": {"name": status}},
            "Priority": {"select": {"name": priority}},
        }
        
        if description:
            properties["Description"] = {"rich_text": [{"text": {"content": description}}]}
        
        if due_date:
            properties["Due Date"] = {"date": {"start": due_date}}

        try:
            return await self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise e

    async def delete_task(self, page_id):
        """Archive (delete) a task"""
        try:
            await self.client.pages.update(page_id=page_id, archived=True)
            return True
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            raise e
