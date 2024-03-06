import logging
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, PicklePersistence, ContextTypes, 
                          ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler,
                          filters)
import ticketpy
import os
from dotenv import load_dotenv
load_dotenv('token.env')

#Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

#Filter warnings
filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

#Ticketmaster API
ticketmaster_token = os.getenv('API_TICKETMASTER_TOKEN')
if ticketmaster_token is None:
    raise ValueError('API_TICKETMASTER_TOKEN is not set')
tm_client = ticketpy.ApiClient(ticketmaster_token)

#Telegram API
telegram_token = os.getenv('API_TELEGRAM_TOKEN')
if telegram_token is None:
    raise ValueError('API_TELEGRAM_TOKEN is not set')

#States
START_ROUTES, END_ROUTES = range(2)
#Callback data
ARTIST_SEARCH, EVENT_SEARCH, FOLLOWING = range(3)
#Artist seach states
ARTIST_SEARCH_RESULTS = range(1)
#Ending conversation
FOLLOW, START_OVER, END = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)

    keyboard = [
        [InlineKeyboardButton("Buscar artista", callback_data=str(ARTIST_SEARCH)),
         InlineKeyboardButton("Buscar evento", callback_data=str(EVENT_SEARCH)),
         InlineKeyboardButton("Artistas que sigo", callback_data=str(FOLLOWING))]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Elige una opción", reply_markup=reply_markup)
    return START_ROUTES

async def start_over(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Buscar artista", callback_data=str(ARTIST_SEARCH)),
         InlineKeyboardButton("Buscar evento", callback_data=str(EVENT_SEARCH)),
         InlineKeyboardButton("Artistas que sigo", callback_data=str(FOLLOWING))]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("Elige una opción", reply_markup=reply_markup)
    return START_ROUTES

async def buscar_artista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Dime el artista que quieres buscar")
    return ARTIST_SEARCH_RESULTS

async def artist_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resp = tm_client.attractions.find(keyword=update.message.text).all()
    keyboard = []
    keyboard.append([InlineKeyboardButton("<-- Volver", callback_data=str(START_OVER))])
    for artist in resp:
        keyboard.append([InlineKeyboardButton(artist.name, callback_data=str(FOLLOW)+"_"+artist.id+"_"+artist.name)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona un artista:", reply_markup=reply_markup)
    return END_ROUTES

async def seguir_artista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query
    await query.answer()
    data=query.data.split("_")
    artist_id = data[1]
    artist_name = data[2]
    # Obtiene la lista de artistas seguidos, si no existe, crea una nueva lista
    followed_artists = context.user_data.get('artist_id', [])

    # Añade el nuevo artista a la lista
    followed_artists.append(artist_id)

    # Guarda la lista actualizada en la persistencia
    context.user_data['artist_id'] = followed_artists
    context.user_data['artist_name'] = artist_name
    keyboard=[]
    keyboard.append([InlineKeyboardButton("<-- Volver", callback_data=str(START_OVER))])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Artista "+artist_name+" ("+artist_id+ ") "+" seguido", reply_markup=reply_markup)


async def buscar_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

async def artistas_siguiendo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Recupera los datos de la persistencia
    artist_ids = context.user_data.get('artist_id')

    if not artist_ids:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No estás siguiendo a ningún artista.")
        return

    # Busca los artistas por sus IDs y los muestra
    for artist_id in artist_ids:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=artist_id)

async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

def main():
    persistence = PicklePersistence(filepath='conversationbot.pickle')
    application = ApplicationBuilder().token(telegram_token).persistence(persistence).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            START_ROUTES: [
                CallbackQueryHandler(buscar_artista, pattern="^" + str(ARTIST_SEARCH) + "$"),
                CallbackQueryHandler(buscar_evento, pattern="^" + str(EVENT_SEARCH) + "$"),
                CallbackQueryHandler(artistas_siguiendo, pattern="^" + str(FOLLOWING) + "$"),
            ],
            ARTIST_SEARCH_RESULTS: [
                MessageHandler(filters.TEXT, artist_button),
            ],
            END_ROUTES: [
                CallbackQueryHandler(seguir_artista, pattern="^" + str(FOLLOW)),
                CallbackQueryHandler(start_over, pattern="^" + str(START_OVER) + "$"),
                CallbackQueryHandler(end, pattern="^" + str(END) + "$"),
            ]
        },
        fallbacks=[CommandHandler('start', start)]
    )

    # Add ConversationHandler to application that will be used for handling updates
    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()