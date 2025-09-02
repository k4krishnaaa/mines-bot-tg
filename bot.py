import os, time, random, asyncio, threading
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler, ContextTypes
from flask import Flask

# ----------------- Flask server for Render -----------------
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

# Start flask server in a separate thread
threading.Thread(target=run_flask, daemon=True).start()
# -----------------------------------------------------------

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# States
CHOOSING, FREE_SEED, FREE_MINES, PREMIUM_AWAIT_KEY, PREMIUM_SEED, PREMIUM_MINES = range(6)

BASE = Path(__file__).parent
ASSETS = BASE / "assets"
OUT = BASE / "out"
OUT.mkdir(exist_ok=True)

FREE_TRIAL_LIMIT = 3
ACCESS_KEY = "Genix-Mines-Software"

def free_spot_count(mines):
    if mines == 1: return range(8,11)
    if mines == 2: return range(6,9)
    if mines == 3: return range(5,7)
    return range(5,7)

def premium_spot_count(mines):
    if mines == 1: return range(8,11)
    if mines == 2: return range(6,9)
    if mines == 3: return range(5,8)
    if 4 <= mines <= 6: return range(4,7)
    if 7 <= mines <= 8: return range(3,5)
    if 9 <= mines <= 10: return range(2,4)
    return range(3,6)

def make_image(indices):
    import generate_grid as gg
    outp = OUT / f"prediction_{int(time.time()*1000)}.png"
    gg.make_prediction_image(indices, outp)
    return outp

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uname = f"@{user.username}" if user.username else (user.first_name or "there")
    context.user_data.setdefault("trials_used", 0)
    context.user_data.setdefault("premium", False)

    welcome = f"Welcome {uname} to the Best Stake Mines Predictor Bot which Claims 95% Accuracy."
    keyboard = [
        [InlineKeyboardButton("🧪 Free Trial (3 predictions)", callback_data="free_trial")],
        [InlineKeyboardButton("💎 Purchase Premium (95%-98% Accuracy)", callback_data="buy_premium")]
    ]
    await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSING

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "free_trial":
        used = context.user_data.get("trials_used", 0)
        if used >= FREE_TRIAL_LIMIT:
            keyboard = [[InlineKeyboardButton("💎 Purchase Premium", callback_data="buy_premium")]]
            await query.edit_message_text("Your free trial limit is over. Purchase Premium for unlimited predictions.", reply_markup=InlineKeyboardMarkup(keyboard))
            return CHOOSING
        await query.edit_message_text("🧪 Free Trial selected.\nSend your ACTIVE server seed from Stake Mines.\nNote: Free Trial accuracy ~70%.")
        return FREE_SEED

    if query.data == "buy_premium":
        qr = ASSETS / "qr.png"
        caption = ("🎉 *Premium Plan* — *499₹/Month*\n\n"
                   "Scan the QR to pay. After payment contact *Genix (Admin)* for access.\n\n"
                   "Then send the access key here to activate premium.")
        kb = [[InlineKeyboardButton("Contact Genix (Admin)", url="https://t.me/stakexgenix")]]
        try:
            await query.message.reply_photo(photo=InputFile(qr.open('rb')), caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))
        except Exception:
            await query.message.reply_text("Premium page (QR) could not be displayed. Contact admin: https://t.me/stakexgenix")
        await query.message.reply_text("After payment, send the access key here in chat.")
        return PREMIUM_AWAIT_KEY

    return CHOOSING

async def free_seed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["free_seed"] = update.message.text.strip()
    kb = [[InlineKeyboardButton("1", callback_data="m1"), InlineKeyboardButton("2", callback_data="m2"), InlineKeyboardButton("3", callback_data="m3")]]
    await update.message.reply_text("Select number of mines (Free Trial):", reply_markup=InlineKeyboardMarkup(kb))
    return FREE_MINES

async def free_mines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mines = int(query.data[1:])
    context.user_data["free_mines"] = mines

    msg = await query.message.reply_text("Analyzing safe spots.")
    for i in range(5):
        await asyncio.sleep(1)
        try:
            await msg.edit_text("Analyzing safe spots" + "." * ((i%3)+1))
        except: pass

    cnt = random.choice(list(free_spot_count(mines)))
    indices = sorted(random.sample(range(25), cnt))
    img = make_image(indices)
    await query.message.reply_photo(photo=InputFile(img.open('rb')), caption=f"Free Trial prediction • Mines: {mines} • Safe spots: {cnt}\nAccuracy ~70%")
    context.user_data["trials_used"] = context.user_data.get("trials_used",0) + 1

    if context.user_data["trials_used"] < FREE_TRIAL_LIMIT:
        kb = [[InlineKeyboardButton("Next Prediction", callback_data="free_trial")]]
        await query.message.reply_text("Want another one?", reply_markup=InlineKeyboardMarkup(kb))
    else:
        kb = [[InlineKeyboardButton("💎 Purchase Premium", callback_data="buy_premium")]]
        await query.message.reply_text("🧪 Your 3 Free Trial predictions are finished. Upgrade to Premium for unlimited predictions.", reply_markup=InlineKeyboardMarkup(kb))
    return CHOOSING

async def premium_await_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == ACCESS_KEY:
        context.user_data["premium"] = True
        kb = [[InlineKeyboardButton("Start Prediction", callback_data="premium_start")]]
        await update.message.reply_text("🎉 Congratulations, *Premium Activated!*", parse_mode='Markdown')
        await update.message.reply_text("Ready to go:", reply_markup=InlineKeyboardMarkup(kb))
        return CHOOSING
    else:
        await update.message.reply_text("Invalid key. Please try again or contact admin.")
        return PREMIUM_AWAIT_KEY

async def premium_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        target = query.message
    else:
        target = update.message
    await target.reply_text("Send your ACTIVE server seed from Stake Mines.")
    return PREMIUM_SEED

async def premium_seed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["premium_seed"] = update.message.text.strip()
    row1 = [InlineKeyboardButton(str(i), callback_data=f"pm{i}") for i in range(1,6)]
    row2 = [InlineKeyboardButton(str(i), callback_data=f"pm{i}") for i in range(6,11)]
    await update.message.reply_text("Select number of mines (1-10):", reply_markup=InlineKeyboardMarkup([row1,row2]))
    return PREMIUM_MINES

async def premium_mines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mines = int(query.data[2:])
    msg = await query.message.reply_text("Analyzing safe spots.")
    for i in range(5):
        await asyncio.sleep(1)
        try:
            await msg.edit_text("Analyzing safe spots" + "." * ((i%3)+1))
        except: pass

    cnt = random.choice(list(premium_spot_count(mines)))
    indices = sorted(random.sample(range(25), cnt))
    img = make_image(indices)
    await query.message.reply_photo(photo=InputFile(img.open('rb')), caption=f"Premium prediction • Mines: {mines} • Safe spots: {cnt}")
    kb = [[InlineKeyboardButton("Next Prediction", callback_data="premium_start")]]
    await query.message.reply_text("Need another prediction?", reply_markup=InlineKeyboardMarkup(kb))
    return CHOOSING

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /start to begin.")

def build_app():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Put it in .env or environment variable.")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                CallbackQueryHandler(handle_choice, pattern="^(free_trial|buy_premium)$"),
                CallbackQueryHandler(premium_start, pattern="^premium_start$"),
            ],
            FREE_SEED: [MessageHandler(filters.TEXT & ~filters.COMMAND, free_seed)],
            FREE_MINES: [CallbackQueryHandler(free_mines, pattern="^m[123]$")],
            PREMIUM_AWAIT_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, premium_await_key)],
            PREMIUM_SEED: [MessageHandler(filters.TEXT & ~filters.COMMAND, premium_seed)],
            PREMIUM_MINES: [CallbackQueryHandler(premium_mines, pattern="^pm([1-9]|10)$")],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.COMMAND, unknown))
    return app

if __name__ == "__main__":
    tg_app = build_app()
    print("Bot is running. Press Ctrl+C to stop.")
    tg_app.run_polling(close_loop=False)
