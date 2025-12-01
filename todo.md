# **Автоматическое извлечение рецептов из истории чатов и генерация сайта**

## ***Инструкция для Codex (в Markdown)***

## **Цель**

Настроить автоматизированный процесс:

1. получения истории диалогов через OpenAI Threads API,

2. извлечения кулинарных рецептов,

3. генерации Markdown-файлов,

4. автоматического создания иллюстраций для рецептов,

5. публикации сайта со всеми рецептами через GitHub Actions.

Система должна работать полностью без ручного вмешательства.

---

## **Архитектура проекта**

Репозиторий должен содержать следующую структуру:

```bash
/recipes/          # Markdown-файлы с рецептами
/images/           # Сгенерированные иллюстрации
/raw_threads/      # Сырые JSON тредов OpenAI
/scripts/          # Python-скрипты
/site/             # Hugo/Jekyll/Zola
.github/workflows/ # GitHub Actions
```

---

## **Формат Markdown-рецепта**

Каждый рецепт создаётся в файле:

`recipes/YYYY/MM/DD-slug.md`

Где `slug` — нормализованный заголовок (lowercase, без пробелов).

Структура файла:

```markdown
---
title: "<название>"
date: "<ISO timestamp>"
tags: ["recipe"]
source_thread: "<openai_thread_id>"
source_message_id: "<openai_message_id>"
image: "/images/YYYY/MM/DD-slug.jpg"
temperature: "<если есть>"
time: "<если есть>"
---

## Ингредиенты
<список>

## Шаги
<шаги>

## Примечания
<дополнительная информация>
```

Если поля отсутствуют — они не включаются.

---

## **Скрипты**

### **1. `scripts/fetch_chats.py`**

Назначение:

* загрузка списка тредов из Threads API;

* загрузка всех сообщений каждого треда;

* сохранение данных в `raw_threads/<thread_id>.json`;

* избегание дублирования по timestamp или message\_id.

Использует переменную окружения:
 `OPENAI_API_KEY`.

---

### **2. `scripts/extract_recipes.py`**

Функции:

1. загрузить JSON из `/raw_threads/`;

2. классифицировать каждое сообщение: `"recipe"` или `"not_recipe"`;

3. для `"recipe"` — вызвать LLM для извлечения структуры;

4. получить JSON:

```json
{
  "title": "",
  "ingredients": [],
  "steps": [],
  "time": "",
  "temperature": "",
  "notes": ""
}
```

5. создать Markdown-файл по шаблону;

6. не перезаписывать существующие файлы.

---

### **3\. `scripts/generate_images.py`**

Функции:

1. просканировать `recipes/**/*.md`;

2. найти те, где нет фронтматтера `image:`;

3. извлечь заголовок, ингредиенты и короткое описание;

4. сформировать промпт:

```text
Generate a food photography image of the finished dish.
Style: minimalistic, soft natural lighting, shallow depth-of-field.
Subject: final plated dish.
Recipe: <title>
Ingredients: <список>
```

5. вызвать OpenAI Images API (например, DALL-E);

6. сохранить JPEG в:

 `images/YYYY/MM/DD-slug.jpg`

7. вставить путь в фронтматтер Markdown;

8. не генерировать, если файл уже существует.

---

## **Промпты для LLM**

### **Классификация рецептов**

```txt
You are a classifier. Determine if the following text contains a cooking recipe.
Output only "recipe" or "not_recipe".
```

### **Извлечение структуры рецепта**

```txt
Extract a structured cooking recipe from the text.
Output strictly in the following JSON format:

{
  "title": "",
  "ingredients": [],
  "steps": [],
  "time": "",
  "temperature": "",
  "notes": ""
}
```

---

## **GitHub Actions**

### **Workflow 1: обновление рецептов \+ генерация изображений**

Файл: `.github/workflows/update.yml`

```yaml
name: Update Recipes

on:
  schedule:
    - cron: "0 */6 * * *"
  workflow_dispatch: {}

jobs:
  update:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install -r scripts/requirements.txt

      - name: Fetch new chats
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: python scripts/fetch_chats.py

      - name: Extract recipes
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: python scripts/extract_recipes.py

      - name: Generate images
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: python scripts/generate_images.py

      - name: Commit changes
        run: |
          git config user.name "RecipeBot"
          git config user.email "recipebot@users.noreply.github.com"
          git add recipes/ images/
          git commit -m "Auto-update recipes and images" || echo "No changes"
          git push
```

---

### **Workflow 2: сборка и деплой сайта**

Файл: `.github/workflows/deploy.yml`

```yaml
name: Deploy Site

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: peaceiris/actions-hugo@v3
        with:
          hugo-version: "latest"

      - name: Build
        run: hugo -s site/

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./site/public
```

---

## **Требования к стабильности**

* повторные запуски не создают дубликатов рецептов или изображений;
* ошибки API логируются, но не прерывают полный цикл;
* все операции должны быть идемпотентными;
* workflows корректно работают без новых данных.

---

## **Результат**

После настройки:

* рецепты автоматически извлекаются из истории ChatGPT;
* каждый рецепт превращается в структурированный Markdown;
* к каждому рецепту автоматически создаётся иллюстрация;
* сайт обновляется и деплоится без участия человека.
