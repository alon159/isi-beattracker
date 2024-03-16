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
ARTIST_SEARCH, EVENT_SEARCH, FOLLOWING, ARTIST_INFO = range(4)
#Artist seach states
ARTIST_SEARCH_RESULTS = range(1)
#Ending conversation
FOLLOW, UNFOLLOW, START_OVER, END = range(4)

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
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Buscando al artista, por favor espera...")
    resp = tm_client.attractions.find(keyword=update.message.text).all()
    keyboard = []
    
    # Get the dictionary of followed artists, if it doesn't exist, create a new one
    followed_artists = context.user_data.get('followed_artists', {})

    for artist in resp:
        # Check if the artist is followed by the user
        if artist.id in followed_artists:
            heart_emoji = "❤️"  # Filled heart for followed artists
            action = UNFOLLOW
        else:
            heart_emoji = "♡"  # Empty heart for not followed artists
            action = FOLLOW

        keyboard.append([
            InlineKeyboardButton(artist.name, callback_data=str(ARTIST_INFO)+"_"+artist.id+"_"+artist.name),
            InlineKeyboardButton(f"{heart_emoji}", callback_data=str(action)+"_"+artist.id+"_"+artist.name)
        ])
    keyboard.append([InlineKeyboardButton("<-- Volver", callback_data=str(START_OVER))])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Selecciona un artista:", reply_markup=reply_markup)
    return END_ROUTES

async def seguir_artista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query
    await query.answer()
    data=query.data.split("_")
    artist_id = data[1]
    artist_name = data[2]

    # Get the dictionary of followed artists, if it doesn't exist, create a new one
    followed_artists = context.user_data.get('followed_artists', {})

    # Add the new artist to the dictionary
    followed_artists[artist_id] = artist_name

    # Save the updated dictionary in the persistence
    context.user_data['followed_artists'] = followed_artists
    keyboard=[]
    keyboard.append([InlineKeyboardButton("<-- Volver", callback_data=str(START_OVER))])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("<i>Artista <b>"+artist_name+"</b> seguido.</i>", reply_markup=reply_markup, parse_mode='HTML')

async def dejar_seguir_artista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query
    await query.answer()
    data=query.data.split("_")
    artist_id = data[1]
    artist_name = data[2]

    # Get the dictionary of followed artists, if it doesn't exist, create a new one
    followed_artists = context.user_data.get('followed_artists', {})

    # Remove the artist from the dictionary
    if artist_id in followed_artists:
        del followed_artists[artist_id]

    # Save the updated dictionary in the persistence
    context.user_data['followed_artists'] = followed_artists
    keyboard=[]
    keyboard.append([InlineKeyboardButton("<-- Volver", callback_data=str(START_OVER))])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("<i>Has dejado de seguir al artista <b>"+artist_name+"</b>.</i>", reply_markup=reply_markup, parse_mode='HTML')

async def buscar_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

async def artistas_siguiendo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Retrieve the data from the persistence
    followed_artists = context.user_data.get('followed_artists')

    if not followed_artists:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No estás siguiendo a ningún artista.")
        return

    # Create a list to hold the buttons
    keyboard = []

    # Search the artists by their IDs and show them
    for artist_id, artist_name in followed_artists.items():
        # Create a button for each artist and add it to the list
        keyboard.append([InlineKeyboardButton(artist_name, callback_data=str(ARTIST_INFO)+"_"+artist_id+"_"+artist_name)])
    
    keyboard.append([InlineKeyboardButton("<-- Volver", callback_data=str(START_OVER))])
    # Create the keyboard markup with the buttons
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the message with the buttons
    await update.callback_query.edit_message_text(text="Artistas que estás siguiendo:", reply_markup=reply_markup)
    return END_ROUTES

async def mostrar_info_artista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    artist_id = data[1]
    artist_name = data[2]
    
    if artist_name:
        # Fetch events for the artist
        events = tm_client.events.find(keyword=artist_name).all()
        
        # If there are no events, send a message indicating this
        if not events:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"No events found for {artist_name}.")
            return

        # Iterate over the events and send each one as a message
        for event in events:
            event_info = f"<b><i>{event.name}</i></b>\n\n"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=event_info, parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Artista no encontrado.")

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
                CallbackQueryHandler(mostrar_info_artista, pattern="^" + str(ARTIST_INFO)),
                CallbackQueryHandler(seguir_artista, pattern="^" + str(FOLLOW)),
                CallbackQueryHandler(dejar_seguir_artista, pattern="^" + str(UNFOLLOW)),
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