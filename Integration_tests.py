import os
import unittest
from unittest.mock import MagicMock, AsyncMock
from unittest.mock import patch
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import ticketpy
from bot import (ARTIST_INFO, ARTIST_SEARCH_RESULTS, START_ROUTES, generate_buttons, main, start, start_over, buscar_artista, artist_button,
                         buscar_evento, event_button, mostrar_info_evento,
                         artistas_siguiendo, mostrar_info_artista,
                         seguir_dejar_seguir_artista, showCreators)

class TestIntegration(unittest.IsolatedAsyncioTestCase):
    """
    Prueba la función de inicio.

    Esta prueba verifica que la función de inicio envía uel logo de la aplicación con los argumentos correctos,
    devuelve las rutas correctas y crea el número correcto de objetos InlineKeyboardButton.
    """
    async def test_start(self):
        update_mock = MagicMock()
        context_mock = MagicMock()
        context_mock.bot = AsyncMock()
        
        result = await start(update_mock, context_mock)

        self.assertEqual(result, START_ROUTES)

        context_mock.bot.send_photo.assert_called_once()
        call_args = context_mock.bot.send_photo.call_args
        self.assertEqual(call_args.kwargs['chat_id'], update_mock.effective_chat.id)
        self.assertEqual(call_args.kwargs['photo'].name, 'Resources/Bot-beatTracker-Logo.jpg')  # Compare file names
        self.assertEqual(call_args.kwargs['caption'], "Te damos la bienvenida a <b>BeatTracker</b>🎶\n\nEmpieza tu aventura gracias a <i>Ticketmaster</i> 🎫, selecciona una opción:")
        self.assertEqual(call_args.kwargs['parse_mode'], 'HTML')

        NUMBER_OF_BUTTONS = 4
        
        reply_markup = call_args.kwargs['reply_markup']
        self.assertIsInstance(reply_markup, InlineKeyboardMarkup)
        button_count = sum(len(row) for row in reply_markup.inline_keyboard)
        self.assertEqual(button_count, NUMBER_OF_BUTTONS) 
        for row in reply_markup.inline_keyboard:
            for button in row:
                self.assertIsInstance(button, InlineKeyboardButton)

    """
    Prueba la carga de variables de entorno y la inicialización del ApiClient.

    Esta prueba verifica que las variables de entorno 'API_TICKETMASTER_TOKEN' y 'API_TELEGRAM_TOKEN'
    se cargan correctamente y que el ApiClient se inicializa con el token correcto.
    """
    class TestEnvironmentVariables(unittest.TestCase):
        @patch.object(os, 'getenv')
        @patch.object(ticketpy, 'ApiClient')
        def test_environment_variables(self, MockApiClient, mock_getenv):
            mock_getenv.side_effect = lambda x: 'test_token' if x in ['API_TICKETMASTER_TOKEN', 'API_TELEGRAM_TOKEN'] else None
            from bot import ticketmaster_token, telegram_token, tm_client

            mock_getenv.assert_any_call('API_TICKETMASTER_TOKEN')
            mock_getenv.assert_any_call('API_TELEGRAM_TOKEN')

            MockApiClient.assert_called_once_with('test_token')

            self.assertEqual(ticketmaster_token, 'test_token')
            self.assertEqual(telegram_token, 'test_token')
    
    """
    Prueba la función buscar_artista.

    Esta prueba verifica que la función buscar_artista envía un mensaje con el texto correcto
    y devuelve el valor correcto de ARTIST_SEARCH_RESULTS.
    """
    async def test_buscar_artista(self):
        update_mock = MagicMock()
        context_mock = MagicMock()
        context_mock.bot = AsyncMock()

        result = await buscar_artista(update_mock, context_mock)

        context_mock.bot.send_message.assert_called_once_with(chat_id=update_mock.effective_chat.id, text="Escribe el artista que quieres buscar:")

        self.assertEqual(result, ARTIST_SEARCH_RESULTS)
    
    @patch('bot.tm_client')
    async def test_artist_button(self, tm_client_mock):
        """
        Prueba la función artist_button.

        Esta prueba verifica que la función artist_button envía un mensaje con el texto correcto,
        llama a tm_client.attractions.find con el texto del mensaje de actualización como argumento,
        y devuelve el valor correcto de generate_buttons.
        """
        update_mock = MagicMock()
        context_mock = MagicMock()
        context_mock.bot = AsyncMock()

        mock_attraction = MagicMock()
        mock_attraction.id = 'test_id'

        tm_client_mock.attractions.find.return_value.all.return_value = [mock_attraction]

        result = await artist_button(update_mock, context_mock)

        context_mock.bot.send_message.assert_any_call(chat_id=update_mock.effective_chat.id, text="Buscando al artista, por favor espera...")

        tm_client_mock.attractions.find.assert_called_once_with(keyword=update_mock.message.text)

        self.assertEqual(result, await generate_buttons([mock_attraction], ARTIST_INFO, update_mock, context_mock, "artista", include_follow=True))

    @patch('bot.InlineKeyboardButton')
    @patch('bot.InlineKeyboardMarkup')
    @patch('bot.Update')
    @patch('bot.ContextTypes.DEFAULT_TYPE')
    async def test_seguir_dejar_seguir_artista(self, context_mock, update_mock, inline_keyboard_markup_mock, inline_keyboard_button_mock):
        """
        Prueba la función seguir_dejar_seguir_artista.

        Esta prueba verifica si la función sigue y deja de seguir a un artista correctamente.
        Utiliza objetos simulados para las clases Update, Context, InlineKeyboardMarkup e InlineKeyboardButton.
        La prueba primero llama a la función con 'follow' establecido en True y verifica si el artista fue seguido.
        Luego llama a la función con 'follow' establecido en False y verifica si se dejó de seguir al artista.
        """
        query_mock = AsyncMock()
        update_mock.callback_query = query_mock
        query_mock.data = 'command_test_test'
        context_mock.user_data = {'followed_artists': {}}

        # Call the function with 'follow' set to True
        await seguir_dejar_seguir_artista(update_mock, context_mock, True)

        # Check that the artist was followed
        self.assertEqual(context_mock.user_data['followed_artists'], {'test': 'test'})

        # Call the function with 'follow' set to False
        await seguir_dejar_seguir_artista(update_mock, context_mock, False)

        # Check that the artist was unfollowed
        self.assertEqual(context_mock.user_data['followed_artists'], {})        
        
if __name__ == '__main__':
    unittest.main()
