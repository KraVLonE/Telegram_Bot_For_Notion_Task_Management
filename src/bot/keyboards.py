from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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
