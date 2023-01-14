import logging, os
from telegram import *
from telegram.ext import *
from readwise import ReadWise
from datetime import datetime
import logging
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

#get bot token from env
BOT_TOKEN = os.getenv('BOT_TOKEN')
# initialize class for Readwise api
WISE = ReadWise(os.getenv('READWISE_TOKEN'))
# restrict access to our bot to avoid spam
ADMIN = os.getenv('ADMIN_USER_ID')

logging.FileHandler("info_telewise_bot.txt", mode='a', encoding=None, delay=False)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

FORWARD = range(1)

def restricted(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id == ADMIN:
            print(f"Unauthorized access denied for {user_id}.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped
    

def url_extracter(entities):
    for ent in entities:
        txt = entities[ent]
        if ent.type == ent.TEXT_LINK:
            # Text with embedded URL  
            return str(ent.url)
        elif ent.type == ent.URL:
            # Plain URL
            return str(txt)

@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Bot for integration with ReadWise api and Telegram. Forward me posts and I will send them to your ReadWise. For more go to https://github.com/ixnet/telewise_bot")
@restricted
async def send_to_readwise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print ("[+][+][+][+][+] Message from " + str(update.effective_user.id))
    # link for the telegram post
    telegram_link = "<a href='https://t.me/" + str(update.message.forward_from_chat.username) + "/" + str(update.message.forward_from_message_id) + "'>Telegram Link</a>"
    
    #default note text
    note_txt ="from Telegram bot"
        
    # if the message contains only text, it will have text_html property, but if the message contains media the text of the message would be in the caption_html property    
    text = update.message.text_html if update.message.caption_html is None else update.message.caption_html
    # applend telegram link to the post
    text = text + "\n\n" + "<a href='https://t.me/" + str(update.message.forward_from_chat.username) + "/" + str(update.message.forward_from_message_id) + "'>Telegram Link</a>"
    # getting only one link (first link in the post would be here) from the post itself.
    post_link = url_extracter(update.message.parse_entities())
    # getting chat or channel name from the original telegram post
    from_who=str(update.message.forward_from_chat.username)
    # check token for Readwise API before sending highlight
    WISE.check_token()
    #send post as Readwise highlight
    WISE.highlight(text=text,
        title=from_who,
        source_url=telegram_link,
        highlight_url=post_link,
        note=note_txt,
        highlighted_at=str(datetime.now().isoformat())
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Message from %s was highlighted with note: %s" % (from_who, note_txt))

@restricted
async def prepare_reader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sending data to Readwise Reader...")
    return FORWARD

@restricted
async def send_to_reader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # link for the telegram post
    telegram_link = "https://t.me/" + str(update.message.forward_from_chat.username) + "/" + str(update.message.forward_from_message_id)
   
    # if the message contains only text, it will have text_html property, but if the message contains media the text of the message would be in the caption_html property    
    text = update.message.text_html if update.message.caption_html is None else update.message.caption_html
   
    WISE.check_token()
    #send post as Readwise highlight
    WISE.save(url=telegram_link,
        html=text,
        title = str(update.message.forward_from_chat.username) + " " + str(datetime.now().isoformat()),
        summary = text[:128])
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Working with Reader API...")
    return ConversationHandler.END
@restricted
async def cancel(update: Update, context: CallbackContext):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Oops...")
    return ConversationHandler.END

if __name__ == '__main__':
    #start app
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    #register commands

    conv_handler_reader = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^r$"), prepare_reader)],
        states={
            FORWARD: [MessageHandler((filters.TEXT | filters.ATTACHMENT | filters.PHOTO) & ~filters.COMMAND, send_to_reader)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    
    application.add_handler(conv_handler_reader)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler((filters.TEXT | filters.ATTACHMENT | filters.PHOTO) & ~filters.COMMAND, send_to_readwise))
    
    #run bot
    application.run_polling()
