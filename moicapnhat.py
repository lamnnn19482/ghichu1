import logging
import os
import json
import datetime
import pytz
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram import BotCommand

# Cấu hình
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = "8039316281:AAFTbneqvBSePbcQE9250_HLRTcCVrOGiD8"

# File lưu trữ
NOTES_FILE = "notes.json"
BACKUP_FILE = "notes_backup.json"   

# States
MAIN_MENU = range(1)

# Dữ liệu ghi chú
notes_data = {"pending": [], "completed": []}

def load_notes():
    """Tải dữ liệu ghi chú"""
    global notes_data
    try:
        with open(NOTES_FILE, 'r', encoding='utf-8') as f:
            notes_data = json.load(f)
    except FileNotFoundError:
        notes_data = {"pending": [], "completed": []}
        save_notes()

def save_notes():
    """Lưu dữ liệu - có backup để tránh mất"""
    try:
        # Backup file cũ trước khi ghi mới
        if os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        # Ghi file mới
        with open(NOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(notes_data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logging.error(f"Lỗi khi lưu file: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return MAIN_MENU
    load_notes()
    quote = (
        
        "đi xe lửa một mình,\n"
        "xuống dòng ở chung vợ chồng tây ở hội an một mình,\n"
        "bán kẹo cho tình nhân,\n"
        "bản linh với gái gú 1 2 3 làm,\n"
        "ở chung nhà ở bình dương ban đêm khu rừng cao xu ngủ ngoài sân,\n"
        "ở nhà ma đà lạt"
    )
    await update.message.reply_text(
        quote,
    )
    return MAIN_MENU

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return MAIN_MENU
    text = update.message.text
    if text == "Start":
        quote = "Vượt qua giới hạn vùng an toàn lúc ở chung cặp vợ chồng tây mua nước nắm nấu canh chua cho họ ăn"
        decorated_quote = f"\n——— {quote} ———\n"
        await update.message.reply_text(
            decorated_quote,
        )
        return MAIN_MENU
    elif text == "Diễn ra":
        await show_pending_notes(update, context)
        return MAIN_MENU
    elif text == "Hoàn thành":
        await show_completed_notes(update, context)
        return MAIN_MENU
    else:
        # Tự động tạo ghi chú mới với ngày hiện tại
        note_text = text.strip()
        current_date = get_current_vietnam_date()
        note = {
            "id": len(notes_data["pending"]) + len(notes_data["completed"]) + 1,
            "text": note_text,
            "created_at": current_date,
            "created_date": current_date
        }
        notes_data["pending"].append(note)
        save_notes()
        # Không gửi bất kỳ tin nhắn nào ở đây!
        await show_pending_notes(update, context)
        return MAIN_MENU

async def show_pending_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = getattr(update, 'message', None)
    chat_id = None
    if message is None and hasattr(update, 'effective_chat') and update.effective_chat:
        chat_id = update.effective_chat.id
    elif message is not None and hasattr(message, 'chat') and message.chat:
        chat_id = message.chat.id

    pending = notes_data["pending"]
    if not pending:
        text = "Không có ghi chú nào đang diễn ra."
        if message:
            await message.reply_text(text)
        elif chat_id:
            await context.bot.send_message(chat_id=chat_id, text=text)
        return

    for note in sorted(pending, key=lambda x: x["created_at"], reverse=True):
        display_text = note["text"]
        date = note["created_date"] if "created_date" in note else note["created_at"][:10]
        msg = f"{display_text}\n{date}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Xong", callback_data=f"complete_{note['id']}")]
        ])
        if message:
            await message.reply_text(msg, reply_markup=keyboard)
        elif chat_id:
            await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=keyboard)

async def show_completed_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    completed = notes_data["completed"]
    if not completed:
        await update.message.reply_text("Chưa có ghi chú nào hoàn thành.")
        return
    msg = ""
    for note in sorted(completed, key=lambda x: x["completed_at"], reverse=True)[:15]:
        display_text = note["text"]
        created = note["created_date"] if "created_date" in note else note["created_at"][:10]
        msg += f"{display_text}\n{created}\n\n"
    await update.message.reply_text(msg.strip())

async def handle_complete_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi người dùng bấm nút 'Hoàn thành'"""
    query = update.callback_query
    if not query or not query.data or not query.data.startswith("complete_"):
        return
    await query.answer()
    note_id = int(query.data.split("_")[1])
    # Tìm ghi chú trong danh sách pending
    note_to_complete = None
    for i, note in enumerate(notes_data["pending"]):
        if note["id"] == note_id:
            note_to_complete = notes_data["pending"].pop(i)
            break
    if note_to_complete:
        # Thêm thời gian hoàn thành
        note_to_complete["completed_at"] = get_current_vietnam_date()
        notes_data["completed"].append(note_to_complete)
        save_notes()
        await query.edit_message_text(
            f"——— HOÀN THÀNH ———\n{note_to_complete['text']}\n{note_to_complete['completed_at']}\n"
        )
        # Gửi lại danh sách pending mới
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Danh sách cập nhật:"
            )
            await show_pending_notes(update, context)
    else:
        await query.edit_message_text(
            "Không tìm thấy ghi chú để hoàn thành."
            # Không truyền reply_markup ở đây
        )

async def waitting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_pending_notes(update, context)

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_completed_notes(update, context)

def get_current_vietnam_time():
    """Lấy thời gian hiện tại theo múi giờ Việt Nam"""
    vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now = datetime.datetime.now(vietnam_tz)
    return now.strftime("%Y-%m-%d %H:%M:%S")

def get_current_vietnam_date():
    vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now = datetime.datetime.now(vietnam_tz)
    return now.strftime("%Y-%m-%d")

def create_pending_notes_keyboard():
    if not notes_data["pending"]:
        return None
    keyboard = []
    for note in notes_data["pending"]:
        keyboard.append([
            InlineKeyboardButton(
                "Xong",
                callback_data=f"complete_{note['id']}"
            )
        ])
    return InlineKeyboardMarkup(keyboard)

async def set_commands(application):
    commands = [
        BotCommand("start", "Bắt đầu"),
        BotCommand("dienra", "Xem ghi chú đang diễn ra"),
        BotCommand("hoanthanh", "Xem ghi chú hoàn thành"),
    ]
    await application.bot.set_my_commands(commands)

import asyncio
# Xoá dòng này vì "app" chưa được định nghĩa ở đây, nên sẽ lỗi. Hãy gọi set_commands trong hàm main sau khi app đã được tạo.

def main():
    load_notes()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("waitting", waitting))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CallbackQueryHandler(handle_complete_note))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu))
    
    print("Bot Ghi Chú đang chạy...")
    app.run_polling()

if __name__ == '__main__':
    main()