from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
import asyncio

from src.config import Config
from src.utils.logger import setup_logger
from src.utils.formatters import format_task_details
from src.bot.keyboards import (
    create_task_keyboard,
    create_edit_keyboard,
    create_status_keyboard,
    create_priority_keyboard
)

logger = setup_logger(__name__)

async def send_tasks_with_buttons(update_or_query, tasks):
    """Send tasks with inline action buttons"""
    # Determine if this is from a message or callback query
    if isinstance(update_or_query, Update):
        send_func = update_or_query.message.reply_text
    else:
        # It's a callback query
        send_func = update_or_query.message.reply_text
    
    if not tasks:
        await send_func("No pending tasks found!")
        return
    
    await send_func(f"*Pending Tasks:* ({len(tasks)} total)\n", parse_mode="Markdown")
    
    for task in tasks:
        task_text = format_task_details(task)
        keyboard = create_task_keyboard(task["id"])
        await send_func(task_text, reply_markup=keyboard, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != Config.AUTHORIZED_USER_ID:
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    user_text = update.message.text
    ai_service = context.bot_data["ai_service"]
    notion_service = context.bot_data["notion_service"]

    # Run AI parsing in a thread to avoid blocking
    try:
        parsed_result = await asyncio.to_thread(ai_service.parse_intent, user_text)
    except Exception as e:
        await update.message.reply_text(f"Failed to process with AI: {e}")
        return

    if not parsed_result:
        await update.message.reply_text("Failed to parse intent from AI.")
        return

    intent = parsed_result.get("intent")
    data = parsed_result.get("data", {})

    logger.info(f"User intent: {intent}, Data: {data}")

    if intent == "read":
        try:
            tasks = await notion_service.get_pending_tasks()
            await send_tasks_with_buttons(update, tasks)
        except Exception as e:
            await update.message.reply_text(f"Error fetching tasks: {e}")
        return

    elif intent == "create":
        try:
            # Default values if missing
            title = data.get("title") or "Untitled Task"
            status = data.get("status") or "Pending"
            priority = data.get("priority") or "Medium"
            description = data.get("description") or ""
            due_date = data.get("due_date")

            new_page = await notion_service.create_task(
                title, status, priority, description, due_date
            )
            
            # Show created task with action buttons
            confirm_msg = f"Task Created!\n\n{format_task_details(new_page)}"
            keyboard = create_task_keyboard(new_page["id"])
            await update.message.reply_text(confirm_msg, reply_markup=keyboard, parse_mode="Markdown")
        
        except Exception as e:
            await update.message.reply_text(f"Failed to create task in Notion: {e}")
            logger.error(f"Create error details: {e}")
        return

    elif intent == "update":
        target_name = data.get("target_task_name")
        target_id = data.get("target_task_id")
        
        if not target_name and not target_id:
            await update.message.reply_text("I need a task name or ID to update.")
            return

        try:
            task_page = None
            if target_id:
                task_page = await notion_service.find_task_by_custom_id(target_id)
                if not task_page:
                    await update.message.reply_text(f"Could not find task with ID {target_id}.")
                    return
            elif target_name:
                task_page = await notion_service.find_task_by_name(target_name)
                if not task_page:
                    await update.message.reply_text(f"Could not find task matching '{target_name}'.")
                    return
            
            # Prepare updates
            updates = {}
            if data.get("status"): updates["status"] = data["status"]
            if data.get("priority"): updates["priority"] = data["priority"]
            if data.get("due_date"): updates["due_date"] = data["due_date"]
            if data.get("new_title"): updates["new_title"] = data["new_title"]

            if not updates:
                await update.message.reply_text("No updates detected.")
                return

            result = await notion_service.update_task(task_page["id"], updates)
            await update.message.reply_text(f"Task Updated!\n\n{format_task_details(result)}", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"Failed to update task: {e}")
        return

    elif intent == "delete":
        target_name = data.get("target_task_name")
        target_id = data.get("target_task_id")
        
        if not target_name and not target_id:
            await update.message.reply_text("I need a task name or ID to delete.")
            return

        try:
            task_page = None
            if target_id:
                task_page = await notion_service.find_task_by_custom_id(target_id)
                if not task_page:
                    await update.message.reply_text(f"Could not find task with ID {target_id}.")
                    return
            elif target_name:
                task_page = await notion_service.find_task_by_name(target_name)
                if not task_page:
                    await update.message.reply_text(f"Could not find task matching '{target_name}'.")
                    return

            await notion_service.delete_task(task_page["id"])
            await update.message.reply_text(f"Task deleted (archived).")
        except Exception as e:
            await update.message.reply_text(f"Failed to delete task: {e}")
        return

    else:
        await update.message.reply_text("❓ Unknown intent.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    notion_service = context.bot_data["notion_service"]
    
    try:
        # Handle different button actions
        if data.startswith("done_"):
            page_id = data.replace("done_", "")
            result = await notion_service.update_task(page_id, {"status": "Done"})
            await query.edit_message_text(f"Task marked as Done!\n\n{format_task_details(result)}", parse_mode="Markdown")
        
        elif data.startswith("delete_"):
            page_id = data.replace("delete_", "")
            await notion_service.delete_task(page_id)
            await query.edit_message_text("Task deleted (archived).")
        
        elif data.startswith("snooze_"):
            page_id = data.replace("snooze_", "")
            task = await notion_service.get_task_by_id(page_id)
            if task:
                props = task["properties"]
                current_date = None
                
                if props.get("Due Date") and props["Due Date"].get("date"):
                    current_date = props["Due Date"]["date"]["start"]
                
                if not current_date:
                    new_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                else:
                    current = datetime.strptime(current_date, "%Y-%m-%d")
                    new_date = (current + timedelta(days=1)).strftime("%Y-%m-%d")
                
                result = await notion_service.update_task(page_id, {"due_date": new_date})
                await query.edit_message_text(f"Task postponed by 1 day!\n\n{format_task_details(result)}", parse_mode="Markdown")
            else:
                await query.edit_message_text("Task not found.")
        
        elif data.startswith("edit_"):
            if data.startswith("edit_status_"):
                page_id = data.replace("edit_status_", "")
                task = await notion_service.get_task_by_id(page_id)
                if task:
                    await query.edit_message_text(
                        f"{format_task_details(task)}\n\n Select new status:",
                        reply_markup=create_status_keyboard(page_id),
                        parse_mode="Markdown"
                    )
            
            elif data.startswith("edit_priority_"):
                page_id = data.replace("edit_priority_", "")
                task = await notion_service.get_task_by_id(page_id)
                if task:
                    await query.edit_message_text(
                        f"{format_task_details(task)}\n\n Select new priority:",
                        reply_markup=create_priority_keyboard(page_id),
                        parse_mode="Markdown"
                    )
            
            elif data.startswith("edit_date_"):
                # page_id = data.replace("edit_date_", "") # Not used
                await query.edit_message_text(
                    "To change the due date, please type:\n\n"
                    "`change due date of [task name] to YYYY-MM-DD`\n\n"
                    "Example: change due date of Buy groceries to 2026-02-20",
                    parse_mode="Markdown"
                )
            
            elif data.startswith("edit_name_"):
                # page_id = data.replace("edit_name_", "") # Not used
                await query.edit_message_text(
                    "✏️ To rename the task, please type:\n\n"
                    "`rename [old task name] to [new name]`\n\n"
                    "Example: rename Buy groceries to Buy groceries and medicine",
                    parse_mode="Markdown"
                )
            
            else:
                # Main edit menu
                page_id = data.replace("edit_", "")
                task = await notion_service.get_task_by_id(page_id)
                if task:
                    await query.edit_message_text(
                        f"{format_task_details(task)}\n\nWhat would you like to edit?",
                        reply_markup=create_edit_keyboard(page_id),
                        parse_mode="Markdown"
                    )
        
        elif data.startswith("status_"):
            parts = data.split("_")
            status = parts[1]
            page_id = "_".join(parts[2:])
            
            result = await notion_service.update_task(page_id, {"status": status})
            await query.edit_message_text(f"Status updated!\n\n{format_task_details(result)}", parse_mode="Markdown")
        
        elif data.startswith("priority_"):
            parts = data.split("_")
            priority = parts[1]
            page_id = "_".join(parts[2:])
            
            result = await notion_service.update_task(page_id, {"priority": priority})
            await query.edit_message_text(f"Priority updated!\n\n{format_task_details(result)}", parse_mode="Markdown")
        
        elif data.startswith("back_"):
            page_id = data.replace("back_", "")
            task = await notion_service.get_task_by_id(page_id)
            if task:
                await query.edit_message_text(
                    format_task_details(task),
                    reply_markup=create_task_keyboard(page_id),
                    parse_mode="Markdown"
                )

    except Exception as e:
        logger.error(f"Callback error: {e}")
        await query.edit_message_text(f"Error performing action: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)
