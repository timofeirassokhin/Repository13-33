# Расширенный LiteLLM-образ с поддержкой SOCKS5-прокси для outbound через WARP.
# Базовый образ доступа к Anthropic/OpenAI с RU-хостинга не имеет socksio.

FROM ghcr.io/berriai/litellm:main-latest

RUN pip install --no-cache-dir socksio "httpx[socks]"
