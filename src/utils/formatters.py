import re

def clean_json(text):
    """Remove markdown wrapping if Gemini adds it"""
    text = re.sub(r"```json|```", "", text).strip()
    return text

def format_task_details(page):
    """Format Notion page properties into a readable string"""
    props = page["properties"]
    
    title = ""
    if props.get("Name") and props["Name"].get("title"):
        # Handle cases where title list might be empty
        title_list = props["Name"]["title"]
        if title_list:
            title = title_list[0]["text"]["content"]
        else:
            title = "Untitled"
    
    status = "Unknown"
    if props.get("Status") and props["Status"].get("select"):
        status = props["Status"]["select"]["name"]
        
    priority = "Unknown"
    if props.get("Priority") and props["Priority"].get("select"):
        priority = props["Priority"]["select"]["name"]
        
    due_date = "No Date"
    if props.get("Due Date") and props["Due Date"].get("date"):
        due_date = props["Due Date"]["date"]["start"]

    # Extract Unique ID
    unique_id = "N/A"
    if props.get("ID") and props["ID"].get("unique_id"):
        uid_props = props["ID"]["unique_id"]
        prefix = uid_props.get("prefix")
        number = uid_props.get("number")
        if prefix:
            unique_id = f"{prefix}-{number}"
        else:
            unique_id = f"{number}"

    return f"📌 *{title}* (ID: {unique_id})\nStatus: {status}\nPriority: {priority}\nDue: {due_date}"
