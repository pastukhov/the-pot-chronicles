# Хроники Кастрюли

Автоматическое извлечение рецептов из истории чат-диалогов через OpenAI Threads API, генерация иллюстраций и публикация статического сайта на Hugo.

## Структура
- `scripts/` — Python-скрипты: загрузка тредов ассистента, извлечение рецептов, генерация изображений, пересборка меню; отдельный импорт из `export/conversations.json` для локального запуска.
- `raw_threads/` — кэшированные JSON тредов.
- `recipes/` — Markdown-рецепты (генерируются автоматически).
- `images/` — сгенерированные иллюстрации.
- `site/` — Hugo-сайт, монтирует `recipes/` и `images/`.
- `.github/workflows/` — CI: обновление рецептов и деплой.

## Локальный запуск
Требуется Python 3.12+ и `OPENAI_API_KEY`. Для автоматического обновления через ассистента также нужны `ASSISTANT_ID` (и опционально `OPENAI_PROJECT`).

```bash
pip install -r scripts/requirements.txt
python scripts/fetch_threads.py
python scripts/extract_recipes.py
python scripts/generate_images.py
python scripts/rebuild_menu.py
```

### Импорт из экспорта ChatGPT (локально, не в CI)
Поместите `export/conversations.json`, затем:
```bash
python scripts/import_conversations.py
```

Для предпросмотра сайта:

```bash
cd site
hugo server
```

## CI/CD
- `.github/workflows/update.yml` — каждые 6 часов (и вручную) импортирует рецепты из `export/conversations.json`, генерирует иллюстрации, обновляет меню и пушит изменения.
- `.github/workflows/hugo.yml` — сборка и публикация Hugo на GitHub Pages.

## Нотсы
- Генерация идемпотентна: повторные запуски не перезаписывают существующие рецепты и картинки.
- Конфиг Hugo хранится в `site/config.yaml`; меню пересобирается на основе `categories` в фронтматтере рецептов.
