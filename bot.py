import datetime
import functools
import hashlib
import logging
import sys
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from telegram import CallbackQuery, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, PicklePersistence, ContextTypes, 
                          ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler,
                          filters)
import ticketpy
import pytz
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

# States
START_ROUTES, END_ROUTES = 0, 1
# Callback data
ARTIST_SEARCH, EVENT_SEARCH, FOLLOWING, ARTIST_INFO, EVENT_INFO = range(2, 7)
# Artist search states
ARTIST_SEARCH_RESULTS, EVENT_SEARCH_RESULTS = 7, 8
# Ending conversation
FOLLOW, UNFOLLOW, START_OVER, END = range(9, 13)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)

    keyboard = [
        [InlineKeyboardButton("🔍 Buscar artista", callback_data=str(ARTIST_SEARCH)),
         InlineKeyboardButton("📅 Buscar evento", callback_data=str(EVENT_SEARCH)),
         InlineKeyboardButton("❤️ Siguiendo", callback_data=str(FOLLOWING))]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open('Resources/Bot-beatTracker-Logo.jpg', 'rb'), caption="Te damos la bienvenida a <b>BeatTracker</b>🎶\n\nEmpieza tu aventura gracias a <i>Ticketmaster</i> 🎫, selecciona una opción:", reply_markup=reply_markup, parse_mode='HTML')
    return START_ROUTES

async def start_over(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🔍 Buscar artista", callback_data=str(ARTIST_SEARCH)),
         InlineKeyboardButton("📅 Buscar evento", callback_data=str(EVENT_SEARCH)),
         InlineKeyboardButton("❤️ Siguiendo", callback_data=str(FOLLOWING))]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open('Resources/Bot-beatTracker-Logo.jpg', 'rb'), caption="Te damos la bienvenida a <b>BeatTracker</b>🎶\n\nEmpieza tu aventura gracias a <i>Ticketmaster</i> 🎫, selecciona una opción:", reply_markup=reply_markup, parse_mode='HTML')
    return START_ROUTES

async def buscar_artista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Escribe el artista que quieres buscar:")
    
    return ARTIST_SEARCH_RESULTS

async def artist_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Buscando al artista, por favor espera...")
    resp = tm_client.attractions.find(keyword=update.message.text).all()
    return await generate_buttons(resp, ARTIST_INFO, update, context, "artista", include_follow=True)

async def seguir_dejar_seguir_artista(update: Update, context: ContextTypes.DEFAULT_TYPE, follow: bool):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    artist_id = data[1]
    artist_name = data[2]

    # Get the dictionary of followed artists, if it doesn't exist, create a new one
    followed_artists = context.user_data.get('followed_artists', {})

    # Follow or unfollow the artist based on the 'follow' parameter
    if follow:
        followed_artists[artist_id] = artist_name
        message_text = f"<i>Artista <b>{artist_name}</b> seguido.</i>"
    else:
        if artist_id in followed_artists:
            del followed_artists[artist_id]
        message_text = f"<i>Has dejado de seguir al artista <b>{artist_name}</b>.</i>"

    # Save the updated dictionary in the persistence
    context.user_data['followed_artists'] = followed_artists
    
    keyboard = [[InlineKeyboardButton("<-- Volver", callback_data=str(START_OVER))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='HTML')

async def buscar_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Escribe el evento que quieres buscar:")
    return EVENT_SEARCH_RESULTS

async def event_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Buscando el evento, por favor espera...")
    try:
        resp = tm_client.events.find(keyword=update.message.text).all()
        return await generate_buttons(resp, EVENT_INFO, update, context, "evento")
    except KeyError as e:
        logging.error(f"KeyError: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Ocurrió un error al procesar la búsqueda ⚠️. Prueba una búsqueda diferente.")

async def mostrar_info_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    event_id = data[1]
    event_name = data[2]
    
    if event_name:
        # Fetch info for the event
        event_search = tm_client.events.find(keyword=event_name).all()
        
        # If there is no event, send a message indicating this
        if not event_search:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Sin información para el evento <b>{event_name}</b>.", parse_mode='HTML')
            return
        
        for index, event in enumerate(event_search):
            event_info = f"<b><i>{event.name}</i></b>\n\n"
            
            if event.status.lower() == 'onsale':
                event_info += f"🟢 <b>En venta</b>\n"
            else:
                event_info += f"🟠 <b>{event.status}</b>\n"
            
            if event.price_ranges:
                min_price = event.price_ranges[0]['min']
                max_price = event.price_ranges[0]['max']
                event_info += f"Desde <b>{min_price}€</b> hasta <b>{max_price}€</b>\n\n"
            else:
                event_info += "<b>Rango de precios no disponible</b>\n\n"

            try:
                if event.utc_datetime:
                    utc_datetime = event.utc_datetime.replace(tzinfo=pytz.utc)
                    spain_datetime = utc_datetime.astimezone(pytz.timezone('Europe/Madrid'))
                elif event.local_datetime:
                    spain_datetime = event.local_datetime
                spain_date_str = spain_datetime.strftime('%d-%m-%Y')
                spain_time_str = spain_datetime.strftime('%H:%M')
            except AttributeError:
                spain_date_str = 'No disponible'
                spain_time_str = 'No disponible'

            event_info += f"<b>Fecha (España):</b> {spain_date_str}\n"
            event_info += f"<b>Hora (España):</b> {spain_time_str}\n\n"
            event_info += f"<b>Lugar:</b> {', '.join([f'{venue.name}, {venue.city}' for venue in event.venues])}\n"

            # TODO: EVENT LINKS STILL NOT WORKING
            event_info += "<b>Links:</b>\n"
            
            # Extract base URL from one of the provided relative URLs
            base_url = "https://www.ticketmaster.com"

            # Iterate over the links and create full URLs
            for link_type, links in event.links.items():
                event_info += f"<b>{link_type.capitalize()}:</b>\n"
                if isinstance(links, list):
                    for link in links:
                        href = link['href']
                        full_url = f"{base_url}{href}"
                        event_info += f"<a href='{full_url}'>{full_url}</a>\n"
                else:
                    href = links
                    full_url = f"{base_url}{href}"
                    event_info += f"<a href='{full_url}'>{full_url}</a>\n"
                    
            # Check if it's the last event
            if index == len(event_search) - 1:
                # Create a "Go back" button
                keyboard = [[InlineKeyboardButton("<-- Volver", callback_data=str(START_OVER))]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(chat_id=update.effective_chat.id, text=event_info, parse_mode='HTML', reply_markup=reply_markup)
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=event_info, parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Event not found.")

async def artistas_siguiendo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Retrieve the data from the persistence
    followed_artists = context.user_data.get('followed_artists')

    if not followed_artists:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No estás siguiendo a ningún artista.")
        return

    # Convert followed artists dictionary into a list of tuples for generating buttons
    followed_artists_list = [(artist_id, artist_name) for artist_id, artist_name in followed_artists.items()]

    # Generate buttons using the modified function
    await generate_buttons(followed_artists_list, ARTIST_INFO, update, context, "artista", include_follow=True)

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
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Sin eventos para el artista <b>{artist_name}</b>.", parse_mode='HTML')
            return

        return await generate_buttons(events, EVENT_INFO, query, context, "evento")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Artista no encontrado.")

async def generate_buttons(items, callback_prefix, update, context, item_type, chat_id=None, include_follow=False):
    keyboard = []
    seen_items = set()

    # Get the dictionary of followed items, if it doesn't exist, create a new one
    followed_items = context.user_data.get('followed_artists', {})

    for item in items:
        if isinstance(item, tuple):
            item_id, item_name = item
        else:
            item_id = item.id
            item_name = item.name

        # Ensure each item is unique (avoid duplicates)
        if item_name in seen_items:
            continue
        seen_items.add(item_name)

        item_id_hash = hashlib.sha1(str(item_id).encode()).hexdigest()

        # Check byte length and truncate if necessary
        base_length = len(f"{callback_prefix}_{item_id_hash}_".encode('utf-8'))
        if base_length + len(item_name.encode('utf-8')) > 64:
            remaining_space = 64 - base_length
            # Calculate the number of characters that fit within the remaining space
            i = 0
            while len(item_name[:i].encode('utf-8')) <= remaining_space:
                i += 1
            item_name = item_name[:i-1]

        buttons_row = [InlineKeyboardButton(item_name, callback_data=f"{callback_prefix}_{item_id_hash}_{item_name}")]

        if include_follow:
            # Check if the item is followed by the user
            if item_id in followed_items:
                heart_emoji = "❤️"  # Filled heart for followed items
                action = UNFOLLOW
            else:
                heart_emoji = "♡"  # Empty heart for not followed items
                action = FOLLOW
            
            buttons_row.append(InlineKeyboardButton(heart_emoji, callback_data=f"{action}_{item_id}_{item_name}"))

        keyboard.append(buttons_row)

        # Check if maximum number of buttons is reached
        if len(seen_items) >= 20:
            break

    # Add a button to go back
    keyboard.append([InlineKeyboardButton("<-- Volver", callback_data=str(START_OVER))])

    # Create the keyboard markup with the buttons
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the message with the buttons
    if chat_id is None:
        if isinstance(update, Update):
            chat_id = update.effective_chat.id
        elif isinstance(update, CallbackQuery):
            chat_id = update.message.chat_id

    if item_type == "artista":
        await context.bot.send_message(chat_id=chat_id, text=f"Selecciona un {item_type}:", reply_markup=reply_markup)
    elif item_type == "evento":
        await context.bot.send_message(chat_id=chat_id, text=f"Selecciona un {item_type}:", reply_markup=reply_markup)

    return END_ROUTES


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
                MessageHandler(filters.TEXT, artist_button),  # Use artist_button here
            ],
            EVENT_SEARCH_RESULTS: [
                MessageHandler(filters.TEXT, event_button),
            ],
            END_ROUTES: [
                CallbackQueryHandler(mostrar_info_artista, pattern="^" + str(ARTIST_INFO)),
                CallbackQueryHandler(mostrar_info_evento, pattern="^" + str(EVENT_INFO)),
                CallbackQueryHandler(functools.partial(seguir_dejar_seguir_artista, follow=True), pattern="^" + str(FOLLOW)),
                CallbackQueryHandler(functools.partial(seguir_dejar_seguir_artista, follow=False), pattern="^" + str(UNFOLLOW)),
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