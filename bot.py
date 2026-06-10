import os
import asyncio
import logging
import json
import re
import httpx
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN        = os.environ.get("BOT_TOKEN", "")
CHAT_ID          = int(os.environ.get("CHAT_ID", "0"))
OPENROUTER_KEY   = os.environ.get("OPENROUTER_KEY", "")
SCAN_INTERVAL_HOURS = 1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── ICT Prompt ────────────────────────────────────────────────────────────────
ICT_PROMPT = """You are an expert ICT (Inner Circle Trader) crypto analyst.

Analyze the current crypto market and select 10 coins with the STRONGEST ICT setups right now.

ICT scoring (0-100):
- Order Block (OB) near price: +25pts
- Fair Value Gap (FVG): +20pts
- Liquidity Sweep: +20pts
- Break of Structure/CHoCH: +20pts
- Volume confirmation: +15pts

Include variety: BTC, ETH + mid caps + high momentum alts.

Return ONLY this exact JSON (no markdown, no extra text):
{"coins":[{"symbol":"BTC","name":"Bitcoin","price":105000,"change24h":2.1,"score":88,"bias":"bullish","signals":["OB BOUNCE","FVG+","LIQ SWEEP"],"analysis":"تحلیل فارسی: وضعیت ICT در تایم‌فریم ۵ و ۱۵ دقیقه","entry":104800,"tp":107500,"sl":103500}],"market_summary":"خلاصه وضعیت کلی بازار به فارسی در ۲ جمله","top_news":["خبر مهم اول","خبر مهم دوم","خبر مهم سوم"]}

Rules:
- Exactly 10 coins sorted by score descending
- analysis field MUST be in Persian (Farsi)
- market_summary MUST be in Persian
- top_news: 3 items in Persian about current crypto market
- Use realistic current prices (approximate)
- Return ONLY the JSON object"""

# ── OpenRouter call ───────────────────────────────────────────────────────────
MODELS = [
    "mistralai/mistral-7b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-4b-it:free",
]

async def run_ict_scan() -> dict | None:
    for model in MODELS:
        try:
            logger.info(f"Trying model: {model}")
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/ict-bot",
                        "X-Title": "ICT Scanner Bot"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": ICT_PROMPT}],
                        "max_tokens": 3000,
                        "temperature": 0.7
                    }
                )

                data = resp.json()
                logger.info(f"OpenRouter status: {resp.status_code} | model: {model}")

                # بررسی خطای API
                if resp.status_code != 200:
                    logger.error(f"API error {resp.status_code}: {data}")
                    continue

                if "choices" not in data:
                    logger.error(f"No choices in response: {data}")
                    continue

                text = data["choices"][0]["message"]["content"].strip()
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    result = json.loads(match.group())
                    if result.get("coins"):
                        logger.info(f"Success with model: {model}")
                        return result
                    else:
                        logger.error(f"Empty coins in response, trying next model")
                        continue

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error with {model}: {e}")
            continue
        except Exception as e:
            logger.error(f"Error with model {model}: {e}")
            continue

    logger.error("All models failed!")
    return None

# ── Format message ────────────────────────────────────────────────────────────
def format_scan_message(data: dict) -> str:
    now = datetime.now().strftime("%H:%M - %Y/%m/%d")
    msg = f"🔍 *اسکن ICT — {now}*\n"
    msg += "━━━━━━━━━━━━━━━━━━━\n\n"

    if data.get("market_summary"):
        msg += f"📊 *وضعیت بازار:*\n{data['market_summary']}\n\n"

    if data.get("top_news"):
        msg += "📰 *اخبار مهم:*\n"
        for news in data["top_news"]:
            msg += f"• {news}\n"
        msg += "\n"

    msg += "━━━━━━━━━━━━━━━━━━━\n"
    msg += "🏆 *۱۰ سیگنال برتر ICT:*\n\n"

    for i, coin in enumerate(data.get("coins", [])[:10], 1):
        score = coin.get("score", 0)
        bias  = coin.get("bias", "neutral")
        score_emoji = "🟢" if score >= 80 else "🟡" if score >= 65 else "🔴"
        bias_emoji  = "📈" if bias == "bullish" else "📉" if bias == "bearish" else "➡️"
        change = coin.get("change24h", 0)
        change_str   = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
        change_emoji = "⬆️" if change >= 0 else "⬇️"

        msg += f"{i}. *{coin.get('symbol','?')}* — {coin.get('name','')}\n"
        msg += f"   💵 ${coin.get('price',0):,} {change_emoji} {change_str}\n"
        msg += f"   {score_emoji} امتیاز: *{score}/100* {bias_emoji}\n"
        signals = coin.get("signals", [])
        if signals:
            msg += f"   🎯 {' | '.join(signals)}\n"
        msg += f"   📝 {coin.get('analysis','')}\n"
        msg += f"   ✅ ورود: `${coin.get('entry',0):,}` | 🎯 هدف: `${coin.get('tp',0):,}` | ❌ حد ضرر: `${coin.get('sl',0):,}`\n\n"

    msg += "━━━━━━━━━━━━━━━━━━━\n"
    msg += "⚡️ _اسکنر هوشمند ICT_ | @Altman07\\_bot"
    return msg

# ── Scan & send ───────────────────────────────────────────────────────────────
async def scan_and_send(context: ContextTypes.DEFAULT_TYPE, chat_id: int = None):
    target = chat_id or CHAT_ID
    loading_msg = await context.bot.send_message(
        chat_id=target,
        text="⏳ *در حال اسکن بازار...*\nلطفاً صبر کنید (تا ۶۰ ثانیه)...",
        parse_mode="Markdown"
    )
    data = await run_ict_scan()

    try:
        await context.bot.delete_message(chat_id=target, message_id=loading_msg.message_id)
    except Exception:
        pass

    if not data or not data.get("coins"):
        await context.bot.send_message(
            chat_id=target,
            text="❌ *خطا در دریافت داده*\nسرویس AI موقتاً در دسترس نیست.\nلطفاً چند دقیقه صبر کنید و دوباره تلاش کنید: /scan",
            parse_mode="Markdown"
        )
        return

    text = format_scan_message(data)
    keyboard = [[
        InlineKeyboardButton("🔄 اسکن مجدد", callback_data="rescan"),
        InlineKeyboardButton("ℹ️ راهنما", callback_data="help")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for j, chunk in enumerate(chunks):
            if j == len(chunks) - 1:
                await context.bot.send_message(chat_id=target, text=chunk, parse_mode="Markdown", reply_markup=reply_markup)
            else:
                await context.bot.send_message(chat_id=target, text=chunk, parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=target, text=text, parse_mode="Markdown", reply_markup=reply_markup)

# ── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != CHAT_ID:
        return
    keyboard = [[InlineKeyboardButton("🔍 شروع اسکن", callback_data="rescan")]]
    await update.message.reply_text(
        "🤖 *ICT Scanner Bot*\n\n"
        "اسکنر هوشمند بازار کریپتو با استراتژی ICT\n\n"
        "دستورات:\n• /scan — اسکن فوری\n• /status — وضعیت\n• /help — راهنما\n\n"
        "⏰ اسکن خودکار: هر ۱ ساعت",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != CHAT_ID:
        return
    await scan_and_send(context, update.effective_chat.id)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != CHAT_ID:
        return
    jobs = context.job_queue.get_jobs_by_name("auto_scan")
    status = "✅ فعال" if jobs else "❌ غیرفعال"
    await update.message.reply_text(
        f"🤖 *وضعیت ربات*\n\n• اسکن خودکار: {status}\n• فاصله: هر {SCAN_INTERVAL_HOURS} ساعت\n• مدل AI: Auto Fallback\n• زمان: {datetime.now().strftime('%H:%M:%S')}",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != CHAT_ID:
        return
    await update.message.reply_text(
        "📖 *راهنمای ICT Scanner*\n\n"
        "🟢 ۸۰+ قوی | 🟡 ۶۵-۷۹ متوسط | 🔴 زیر ۶۵ ضعیف\n\n"
        "• OB — Order Block\n• FVG — Fair Value Gap\n"
        "• LIQ SWEEP — Liquidity Sweep\n• BOS — Break of Structure\n\n"
        "⚠️ _صرفاً جنبه آموزشی دارد_",
        parse_mode="Markdown"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != CHAT_ID:
        return
    await query.answer()
    if query.data == "rescan":
        await scan_and_send(context, query.message.chat_id)
    elif query.data == "help":
        await query.message.reply_text(
            "📖 *راهنما:*\n🟢 ۸۰+ قوی | 🟡 ۶۵-۷۹ متوسط | 🔴 زیر ۶۵ ضعیف\nOB=Order Block | FVG=Fair Value Gap",
            parse_mode="Markdown"
        )

async def auto_scan_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Auto scan triggered")
    await scan_and_send(context)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("scan",   scan_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("help",   help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.job_queue.run_repeating(auto_scan_job, interval=SCAN_INTERVAL_HOURS * 3600, first=10, name="auto_scan")
    logger.info("ICT Scanner Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
logger.error(f"FULL RESPONSE: {resp.status_code} - {data}")
