import logging
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, ContextTypes, CommandHandler, filters, 
                          CallbackQueryHandler, ConversationHandler, MessageHandler, PicklePersistence)
import ticketpy
from dotenv import load_dotenv
load_dotenv()
import os

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

ticketmaster_token = os.getenv('API_TICKETMASTER_TOKEN')
if ticketmaster_token is None:
    raise ValueError('API_TICKETMASTER_TOKEN is not set')
tm_client = ticketpy.Api(ticketmaster_token)

telegram_token = os.getenv('API_TELEGRAM_TOKEN')
if telegram_token is None:
    raise ValueError('API_TELEGRAM_TOKEN is not set')

#ESTADOS
SELECT_OPTION, ARTIST_SEARCH, EVENT_SEARCH, FOLLOWING, START_OVER = range(5)

# Función para enviar un mensaje con botones
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)

    keyboard = [
        [InlineKeyboardButton("Buscar artista", callback_data='buscar_artista'),
         InlineKeyboardButton("Buscar evento", callback_data='buscar_evento'),
         InlineKeyboardButton("Artistas que sigo", callback_data='followed_artists')],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Elige una opción", reply_markup=reply_markup)
    return SELECT_OPTION

async def start_over(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query
    keyboard = [
        [InlineKeyboardButton("Buscar artista", callback_data='buscar_artista'),
         InlineKeyboardButton("Buscar evento", callback_data='buscar_evento'),
         InlineKeyboardButton("Artistas que sigo", callback_data='followed_artists')],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("Elige una opción", reply_markup=reply_markup)
    return SELECT_OPTION

# Función para manejar las respuestas de los botones
async def option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == 'buscar_artista':
        await query.message.reply_text('Por favor, introduce el nombre del artista:')
        return ARTIST_SEARCH
    elif query.data == 'buscar_evento':
        await query.message.reply_text('Por favor, introduce el nombre del evento:')
        return EVENT_SEARCH

async def buscar_artista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resp = tm_client.attractions.find(keyword=update.message.text).all()
    if resp is not None:
        context.user_data['artista'] = resp
    keyboard = []
    keyboard.append([InlineKeyboardButton("<-- Volver", callback_data="volver")])
    for artist in resp:
        keyboard.append([InlineKeyboardButton(artist.name, callback_data=artist.id)])
    #    await context.bot.send_message(chat_id=update.effective_chat.id, text=artist.name)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona un artista:", reply_markup=reply_markup)
    return START_OVER

async def artist_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    artist_id = query.data
    context.user_data['artist_id'] = artist_id
    await query.answer()
    return ConversationHandler.END

# Buscar un evento
async def buscar_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resp = tm_client.events.find(keyword=update.message.text).all()
    keyboard = []
    for event in resp:
        keyboard.append([InlineKeyboardButton(event.name, callback_data=event.id)])
    #    await context.bot.send_message(chat_id=update.effective_chat.id, text=artist.name)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona un evento:", reply_markup=reply_markup)
    return ConversationHandler.END

async def following(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('artista'):
        reply_text = (
            f"Your artista? I already know the following about that: {context.user_data['artista']}"
        )
    await update.message.reply_text(reply_text)
    

async def cancel(update: Update, context):
    """Cancelar la conversación"""
    await update.message.reply_text('Conversación cancelada.')
    return ConversationHandler.END

def main():
    persistence = PicklePersistence(filepath='conversationbot')
    application = ApplicationBuilder().token(telegram_token).persistence(persistence).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_OPTION: [CallbackQueryHandler(option)],
            ARTIST_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, buscar_artista),
                                CallbackQueryHandler(artist_button)],
            EVENT_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, buscar_evento)],
            FOLLOWING: [MessageHandler(filters.TEXT & ~filters.COMMAND, following)],
            START_OVER: [CallbackQueryHandler(start_over)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name='my_conversation',
        persistent=True
    )

    application.add_handler(conv_handler)
    
    application.run_polling()

if __name__ == '__main__':
    main()