import os
import json
import re
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from notion_client import Client as NotionClient
from google import genai
from datetime import datetime, timedelta
import requests
import time

# load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
NOTION_KEY = os.getenv("NOTION_KEY")
DATABASE_ID = os.getenv("DATABASE_ID")
GEMINI_KEY = os.getenv("GEMINI_KEY")

AUTHORIZED_USER_ID = int(os.getenv("TELEGRAM_USERID"))


# Setup Gemini
client = genai.Client(api_key=GEMINI_KEY)

# Setup Notion
notion = NotionClient(auth=NOTION_KEY)


def clean_json(text):
    # Remove markdown wrapping if Gemini adds it
    text = re.sub(r"```json|```", "", text).strip()
    return text

def format_task_details(page):
    props = page["properties"]
    
    title = ""
    if props.get("Name") and props["Name"].get("title"):
        title = props["Name"]["title"][0]["text"]["content"]
    
    status = "Unknown"
    if props.get("Status") and props["Status"].get("select"):
        status = props["Status"]["select"]["name"]
        
    priority = "Unknown"
    if props.get("Priority") and props["Priority"].get("select"):
        priority = props["Priority"]["select"]["name"]
        
    due_date = "No Date"
    if props.get("Due Date") and props["Due Date"].get("date"):
        due_date = props["Due Date"]["date"]["start"]

    return f"📌 *{title}*\nStatus: {status}\nPriority: {priority}\nDue: {due_date}"

def get_pending_tasks():
    """Fetch all tasks that are not marked as Done"""
    try:
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        
        headers = {
            "Authorization": f"Bearer {NOTION_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        body = {
            "filter": {
                "property": "Status",
                "select": {
                    "does_not_equal": "Done"
                }
            }
        }
        
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        data = response.json()
        tasks = data.get("results", [])
        
        return tasks
        
    except Exception as e:
        print(f"Error fetching pending tasks: {e}")
        print(f"Response: {response.text if 'response' in locals() else 'No response'}")
        return []

def find_task_by_name(name):
    """Search for a task by name using the Notion API"""
    try:
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        
        headers = {
            "Authorization": f"Bearer {NOTION_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        body = {
            "filter": {
                "property": "Name",
                "title": {
                    "contains": name
                }
            }
        }
        
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            return None
        
        # Return the first match for simplicity
        return results[0]
        
    except Exception as e:
        print(f"Error finding task '{name}': {e}")
        print(f"Response: {response.text if 'response' in locals() else 'No response'}")
        return None

def get_task_by_id(page_id):
    """Fetch a single task by its page ID"""
    try:
        page = notion.pages.retrieve(page_id=page_id)
        return page
    except Exception as e:
        print(f"Error fetching task by ID: {e}")
        return None

def update_notion_task(page_id, updates):
    """Update a task using the Notion SDK"""
    properties = {}
    
    if "status" in updates and updates["status"]:
        properties["Status"] = {"select": {"name": updates["status"]}}
    
    if "priority" in updates and updates["priority"]:
        properties["Priority"] = {"select": {"name": updates["priority"]}}

    if "due_date" in updates and updates['due_date']:
        properties["Due Date"] = {"date": {"start": updates["due_date"]}}

    if "new_title" in updates and updates["new_title"]:
        properties["Name"] = {"title": [{"text": {"content": updates["new_title"]}}]}

    try:
        # Use the SDK's pages.update method
        updated_page = notion.pages.update(page_id=page_id, properties=properties)
        return format_task_details(updated_page)
    except Exception as e:
        print(f"Error updating task: {e}")
        return None

def delete_notion_task(page_id):
    """Archive (delete) a task using the Notion SDK"""
    try:
        # Use the SDK's pages.update method to archive
        notion.pages.update(page_id=page_id, archived=True)
        return True
    except Exception as e:
        print(f"Error deleting task: {e}")
        return False

def create_task_keyboard(page_id):
    """Create inline keyboard with action buttons for a task"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Done", callback_data=f"done_{page_id}"),
            InlineKeyboardButton("📝 Edit", callback_data=f"edit_{page_id}"),
        ],
        [
            InlineKeyboardButton("⏰ +1 Day", callback_data=f"snooze_{page_id}"),
            InlineKeyboardButton("🗑 Delete", callback_data=f"delete_{page_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_edit_keyboard(page_id):
    """Create keyboard for edit options"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Status", callback_data=f"edit_status_{page_id}"),
            InlineKeyboardButton("🔺 Priority", callback_data=f"edit_priority_{page_id}"),
        ],
        [
            InlineKeyboardButton("📅 Due Date", callback_data=f"edit_date_{page_id}"),
            InlineKeyboardButton("✏️ Rename", callback_data=f"edit_name_{page_id}"),
        ],
        [
            InlineKeyboardButton("◀️ Back", callback_data=f"back_{page_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_status_keyboard(page_id):
    """Create keyboard for status selection"""
    keyboard = [
        [InlineKeyboardButton("⏳ Pending", callback_data=f"status_Pending_{page_id}")],
        [InlineKeyboardButton("▶️ In Progress", callback_data=f"status_In Progress_{page_id}")],
        [InlineKeyboardButton("✅ Done", callback_data=f"status_Done_{page_id}")],
        [InlineKeyboardButton("◀️ Back", callback_data=f"back_{page_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)

def create_priority_keyboard(page_id):
    """Create keyboard for priority selection"""
    keyboard = [
        [InlineKeyboardButton("🔴 High", callback_data=f"priority_High_{page_id}")],
        [InlineKeyboardButton("🟡 Medium", callback_data=f"priority_Medium_{page_id}")],
        [InlineKeyboardButton("🟢 Low", callback_data=f"priority_Low_{page_id}")],
        [InlineKeyboardButton("◀️ Back", callback_data=f"back_{page_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_tasks_with_buttons(update_or_query, tasks):
    """Send tasks with inline action buttons"""
    
    # Determine if this is from a message or callback query
    if isinstance(update_or_query, Update):
        send_func = update_or_query.message.reply_text
    else:
        # It's a callback query
        send_func = update_or_query.message.reply_text
    
    if not tasks:
        await send_func("✅ No pending tasks found!")
        return
    
    await send_func(f"📝 *Pending Tasks:* ({len(tasks)} total)\n", parse_mode="Markdown")
    
    for task in tasks:
        task_text = format_task_details(task)
        keyboard = create_task_keyboard(task["id"])
        await send_func(task_text, reply_markup=keyboard, parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data
    data = query.data
    
    # Handle different button actions
    if data.startswith("done_"):
        page_id = data.replace("done_", "")
        result = update_notion_task(page_id, {"status": "Done"})
        if result:
            await query.edit_message_text(f"✅ Task marked as Done!\n\n{result}", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ Failed to update task.")
    
    elif data.startswith("delete_"):
        page_id = data.replace("delete_", "")
        success = delete_notion_task(page_id)
        if success:
            await query.edit_message_text("🗑️ Task deleted (archived).")
        else:
            await query.edit_message_text("❌ Failed to delete task.")
    
    elif data.startswith("snooze_"):
        page_id = data.replace("snooze_", "")
        # Get current task to find due date
        task = get_task_by_id(page_id)
        if task:
            props = task["properties"]
            current_date = None
            
            if props.get("Due Date") and props["Due Date"].get("date"):
                current_date = props["Due Date"]["date"]["start"]
            
            # If no date, use today
            if not current_date:
                new_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                # Add 1 day to current date
                current = datetime.strptime(current_date, "%Y-%m-%d")
                new_date = (current + timedelta(days=1)).strftime("%Y-%m-%d")
            
            result = update_notion_task(page_id, {"due_date": new_date})
            if result:
                await query.edit_message_text(f"⏰ Task postponed by 1 day!\n\n{result}", parse_mode="Markdown")
            else:
                await query.edit_message_text("❌ Failed to snooze task.")
        else:
            await query.edit_message_text("❌ Task not found.")
    
    elif data.startswith("edit_"):
        if data.startswith("edit_status_"):
            page_id = data.replace("edit_status_", "")
            task = get_task_by_id(page_id)
            if task:
                await query.edit_message_text(
                    f"{format_task_details(task)}\n\n📊 Select new status:",
                    reply_markup=create_status_keyboard(page_id),
                    parse_mode="Markdown"
                )
        
        elif data.startswith("edit_priority_"):
            page_id = data.replace("edit_priority_", "")
            task = get_task_by_id(page_id)
            if task:
                await query.edit_message_text(
                    f"{format_task_details(task)}\n\n🔺 Select new priority:",
                    reply_markup=create_priority_keyboard(page_id),
                    parse_mode="Markdown"
                )
        
        elif data.startswith("edit_date_"):
            page_id = data.replace("edit_date_", "")
            await query.edit_message_text(
                "📅 To change the due date, please type:\n\n"
                "`change due date of [task name] to YYYY-MM-DD`\n\n"
                "Example: change due date of Buy groceries to 2026-02-20",
                parse_mode="Markdown"
            )
        
        elif data.startswith("edit_name_"):
            page_id = data.replace("edit_name_", "")
            await query.edit_message_text(
                "✏️ To rename the task, please type:\n\n"
                "`rename [old task name] to [new name]`\n\n"
                "Example: rename Buy groceries to Buy groceries and medicine",
                parse_mode="Markdown"
            )
        
        else:
            # Main edit menu
            page_id = data.replace("edit_", "")
            task = get_task_by_id(page_id)
            if task:
                await query.edit_message_text(
                    f"{format_task_details(task)}\n\n📝 What would you like to edit?",
                    reply_markup=create_edit_keyboard(page_id),
                    parse_mode="Markdown"
                )
    
    elif data.startswith("status_"):
        parts = data.split("_")
        status = parts[1]
        page_id = "_".join(parts[2:])
        
        result = update_notion_task(page_id, {"status": status})
        if result:
            await query.edit_message_text(f"✅ Status updated!\n\n{result}", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ Failed to update status.")
    
    elif data.startswith("priority_"):
        parts = data.split("_")
        priority = parts[1]
        page_id = "_".join(parts[2:])
        
        result = update_notion_task(page_id, {"priority": priority})
        if result:
            await query.edit_message_text(f"✅ Priority updated!\n\n{result}", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ Failed to update priority.")
    
    elif data.startswith("back_"):
        page_id = data.replace("back_", "")
        task = get_task_by_id(page_id)
        if task:
            await query.edit_message_text(
                format_task_details(task),
                reply_markup=create_task_keyboard(page_id),
                parse_mode="Markdown"
            )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if user_id != AUTHORIZED_USER_ID:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    
    user_text = update.message.text
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
    - Extract "target_task_name" (the name of the task to find).
    - Extract fields to update: "status", "priority", "due_date", "new_title".
    - Only include fields that are explicitly mentioned to be changed.

    Rules for "delete":
    - Extract "target_task_name".

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
          "target_task_name": "...",// For update/delete
          "new_title": "..."        // For update (renaming)
      }}
    }}

    User input:
    {user_text}
    """
    
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )
            break
        except Exception as e:
            if attempt == 2:
                await update.message.reply_text(f"❌ Failed to process with AI: {e}")
                return
            time.sleep(2)

    content = clean_json(response.text)
    try:
        parsed_result = json.loads(content)
        intent = parsed_result.get("intent")
        data = parsed_result.get("data", {})
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to parse intent: {e}")
        return

    # HANDLE INTENTS
    if intent == "read":
        tasks = get_pending_tasks()
        await send_tasks_with_buttons(update, tasks)
        return

    elif intent == "create":
        try:
            # Default values if missing
            title = data.get("title") or "Untitled Task"
            status = data.get("status") or "Pending"
            priority = data.get("priority") or "Medium"
            description = data.get("description") or ""
            due_date = data.get("due_date")

            notion_props = {
                "Name": {"title": [{"text": {"content": title}}]},
                "Status": {"select": {"name": status}},
                "Priority": {"select": {"name": priority}},
            }
            
            # Only add Description if your database has this property
            if description:
                notion_props["Description"] = {"rich_text": [{"text": {"content": description}}]}
            
            if due_date:
                notion_props["Due Date"] = {"date": {"start": due_date}}

            new_page = notion.pages.create(
                parent={"database_id": DATABASE_ID},
                properties=notion_props
            )
            
            # Show created task with action buttons
            confirm_msg = f"✅ Task Created!\n\n{format_task_details(new_page)}"
            keyboard = create_task_keyboard(new_page["id"])
            await update.message.reply_text(confirm_msg, reply_markup=keyboard, parse_mode="Markdown")
        
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to create task in Notion: {e}")
            print(f"Create error details: {e}")
        return

    elif intent == "update":
        target_name = data.get("target_task_name")
        if not target_name:
            await update.message.reply_text("❌ I need a task name to update.")
            return

        task_page = find_task_by_name(target_name)
        if not task_page:
            await update.message.reply_text(f"❌ Could not find task matching '{target_name}'.")
            return
        
        # Prepare updates
        updates = {}
        if data.get("status"): updates["status"] = data["status"]
        if data.get("priority"): updates["priority"] = data["priority"]
        if data.get("due_date"): updates["due_date"] = data["due_date"]
        if data.get("new_title"): updates["new_title"] = data["new_title"]

        if not updates:
            await update.message.reply_text("⚠️ No updates detected.")
            return

        result = update_notion_task(task_page["id"], updates)
        if result:
            await update.message.reply_text(f"✅ Task Updated!\n\n{result}", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Failed to update task.")
        return

    elif intent == "delete":
        target_name = data.get("target_task_name")
        if not target_name:
            await update.message.reply_text("❌ I need a task name to delete.")
            return

        task_page = find_task_by_name(target_name)
        if not task_page:
            await update.message.reply_text(f"❌ Could not find task matching '{target_name}'.")
            return

        success = delete_notion_task(task_page["id"])
        if success:
            await update.message.reply_text(f"🗑️ Task '{target_name}' deleted (archived).")
        else:
            await update.message.reply_text("❌ Failed to delete task.")
        return

    else:
        await update.message.reply_text("❓ Unknown intent.")


async def error_handler(update, context):
    print("Exception:", context.error)



app = (
    ApplicationBuilder()
    .token(TELEGRAM_TOKEN)
    .get_updates_connect_timeout(30)
    .get_updates_read_timeout(30)
    .read_timeout(30)
    .write_timeout(30)
    .connect_timeout(30)
    .build()
)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_callback))  # NEW: Handle button clicks
app.add_error_handler(error_handler)
if __name__ == "__main__":
    app.run_polling()
