from google import genai
from datetime import datetime
import json
import time
from src.config import Config
from src.utils.formatters import clean_json
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class AIService:
    def __init__(self):
        self.client = genai.Client(api_key=Config.GEMINI_KEY)

    def parse_intent(self, user_text):
        """Parse natural language input into intent and data"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        prompt = f"""
        Today's date is: {today}

        You are a task management assistant. Your job is to extract the intent and relevant data from the user's natural language input.

        Available Intents:
        - "create": Create a new task.
        - "read": Read/List pending tasks.
        - "update": Update an existing task (change status, priority, due date, or rename).
        - "delete": Delete/Archive a task.

        Rules for "create":
        - Extract "title", "status" (default: "Pending"), "priority" (default: "Medium"), "due_date" (YYYY-MM-DD or null), "description".

        Rules for "read":
        - No extra data needed. Just set intent to "read".

        Rules for "update":
        - Extract "target_task_name" (exact task name if present).
        - Extract "target_task_id" (number if the user provides the ID, e.g. "task 12", "id 45").
        - Extract fields to update: "status", "priority", "due_date", "new_title".
        - Only include fields that are explicitly mentioned to be changed.

        Rules for "delete":
        - Extract "target_task_name" OR "target_task_id".

        Allowed Values:
        Status: ["Pending", "In Progress", "Done"]
        Priority: ["Low", "Medium", "High"]

        Return STRICT JSON only:
        {{
          "intent": "create|read|update|delete",
          "data": {{
              "title": "...",           // For create
              "status": "...",          // For create/update
              "priority": "...",        // For create/update
              "due_date": "...",        // For create/update
              "description": "...",     // For create
              "target_task_name": "...",// For update/delete (if name used)
              "target_task_id": 123,    // For update/delete (if ID used, int)
              "new_title": "..."        // For update (renaming)
          }}
        }}

        User input:
        {user_text}
        """
        
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json"
                    }
                )
                content = clean_json(response.text)
                return json.loads(content)
            except Exception as e:
                logger.warning(f"AI Attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    logger.error(f"Failed to process with AI after 3 attempts: {e}")
                    raise e
                time.sleep(1)
        
        return None
