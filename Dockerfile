# Usa la imagen base de Python
FROM python:3.9-slim

# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia el archivo pyproject.toml al directorio de trabajo
COPY pyproject.toml .

# Instala las dependencias del proyecto
RUN pip install --no-cache-dir -r pyproject.toml

# Copia todo el contenido del directorio actual al directorio de trabajo
COPY . .

# Ejecuta el bot cuando se inicie el contenedor
CMD ["python", "bot.py"]
