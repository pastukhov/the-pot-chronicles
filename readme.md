# Хроники Кастрюли

Автоматическое извлечение рецептов из истории чат-диалогов через OpenAI Threads API, генерация иллюстраций и публикация статического сайта на Hugo.

## Структура
- `scripts/` — Python-скрипты: импорт рецептов из экспортов ChatGPT, извлечение рецептов, генерация изображений, пересборка меню.
- `raw_threads/` — кэшированные JSON тредов.
- `recipes/` — Markdown-рецепты (генерируются автоматически).
- `images/` — сгенерированные иллюстрации.
- `site/` — Hugo-сайт, монтирует `recipes/` и `images/`.
- `.github/workflows/` — CI: обновление рецептов и деплой.

## Локальный запуск
Требуется Python 3.12+ и `OPENAI_API_KEY`. Для импорта нужен файл `export/conversations.json` (экспорт из ChatGPT).

```bash
pip install -r scripts/requirements.txt
python scripts/import_conversations.py
python scripts/generate_images.py
python scripts/rebuild_menu.py
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
