# Хроники Кастрюли

Автоматическое извлечение рецептов из истории чат-диалогов через OpenAI Threads API, генерация иллюстраций и публикация статического сайта на Hugo.

## Структура
- `scripts/` — Python-скрипты: загрузка тредов, извлечение рецептов, генерация изображений, пересборка меню.
- `raw_threads/` — кэшированные JSON тредов.
- `recipes/` — Markdown-рецепты (генерируются автоматически).
- `images/` — сгенерированные иллюстрации.
- `site/` — Hugo-сайт, монтирует `recipes/` и `images/`.
- `.github/workflows/` — CI: обновление рецептов и деплой.

## Локальный запуск
Требуется Python 3.12+, `OPENAI_API_KEY` и `ASSISTANT_ID` (ID ассистента "Pot Chronicles Recipe Assistant").

```bash
pip install -r scripts/requirements.txt
python scripts/fetch_threads.py
python scripts/extract_recipes.py
python scripts/generate_images.py
python scripts/rebuild_menu.py
```

Для предпросмотра сайта:

```bash
cd site
hugo server
```

## CI/CD
- `.github/workflows/update.yml` — каждые 6 часов (и вручную) тянет треды, извлекает рецепты, генерирует иллюстрации, обновляет меню и пушит изменения.
- `.github/workflows/hugo.yml` — сборка и публикация Hugo на GitHub Pages.

## Нотсы
- Генерация идемпотентна: повторные запуски не перезаписывают существующие рецепты и картинки.
- Конфиг Hugo хранится в `site/config.yaml`; меню пересобирается на основе `categories` в фронтматтере рецептов.
