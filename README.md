# BeatTracker 🎵

![BeatTracker Logo](https://github.com/alon159/isi-beattracker/assets/100356318/38e97309-066c-41b3-9e44-dfdc6fc15c13)

## Descripción General 📋

BeatTracker es un bot de Telegram diseñado para ayudar a los usuarios a seguir a sus artistas y eventos favoritos. El bot utiliza la API de Ticketmaster para proporcionar información en tiempo real sobre eventos y artistas, permitiendo a los usuarios seguir artistas, buscar eventos y recibir notificaciones sobre nuevos eventos.

## Estructura del Proyecto 🗂️

El proyecto consta de los siguientes archivos y directorios principales:

- `bot.py`: La implementación principal del bot, que contiene todas las funcionalidades y manejadores de comandos del bot.
- `Integration_tests.py`: Contiene pruebas de integración para las funcionalidades del bot para asegurar que todo funcione como se espera.
- `Dockerfile`: Define la imagen de Docker para el bot, especificando el entorno y las dependencias.
- `pyproject.toml`: Administra las dependencias y configuraciones del proyecto.
- `README.md`: Proporciona una descripción general y documentación del proyecto.
- `Resources/`: Contiene recursos utilizados por el bot, como imágenes.

## Tecnologías Utilizadas 🛠️

- **Python**: El lenguaje de programación principal utilizado para la implementación del bot.
- **Telegram Bot API**: Utilizada para interactuar con Telegram y manejar comandos y mensajes de los usuarios.
- **Ticketmaster API**: Proporciona información sobre eventos y artistas.
- **Asyncio**: Utilizado para programación asíncrona para manejar múltiples tareas concurrentemente.
- **Docker**: Utilizado para contenerizar la aplicación para facilitar su despliegue y escalabilidad.
- **unittest**: El marco de pruebas integrado de Python utilizado para escribir y ejecutar pruebas.
- **dotenv**: Utilizado para cargar variables de entorno desde un archivo `.env`.
- **logging**: Utilizado para registrar información y errores.

## Funcionalidades Principales ✨

- **Búsqueda de Artistas**: Los usuarios pueden buscar artistas y obtener información sobre ellos.
- **Búsqueda de Eventos**: Los usuarios pueden buscar eventos y obtener detalles como fecha, hora y ubicación.
- **Seguir Artistas**: Los usuarios pueden seguir a sus artistas favoritos y recibir notificaciones sobre nuevos eventos.
- **Notificaciones**: El bot envía notificaciones sobre nuevos eventos de los artistas seguidos.
- **Botones Inline**: El bot utiliza botones inline para facilitar la navegación e interacción.

## Cómo Ejecutar 🚀

1. **Clonar el repositorio**:
    ```sh
    git clone https://github.com/alon159/isi-beattracker.git
    cd isi-beattracker
    ```

2. **Configurar las variables de entorno**:
    Crear un archivo `.env` en el directorio raíz y agregar tus tokens de API:
    ```env
    API_TMASTER_TOKEN=tu_token_de_ticketmaster
    API_TELEGRAM_TOKEN=tu_token_de_telegram
    ```

3. **Construir y ejecutar el contenedor Docker**:
    ```sh
    docker build -t beattracker .
    docker run -d --name beattracker-container beattracker
    ```

4. **Ejecutar el bot localmente** (opcional):
    ```sh
    python bot.py
    ```

## Pruebas ✅

Para ejecutar las pruebas de integración, utiliza el siguiente comando:
```sh
python -m unittest [Integration_tests.py](http://_vscodecontentref_/0)
