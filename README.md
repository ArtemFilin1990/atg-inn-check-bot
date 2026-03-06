# atg-inn-check-bot

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)
![aiogram 3.x](https://img.shields.io/badge/aiogram-3.x-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688)

Telegram-бот на **aiogram v3** для быстрой и удобной проверки юридических лиц и ИП по ИНН через **DaData API**.  
Оптимизирован для деплоя на **Amvera** (режим webhook, на базе **FastAPI + uvicorn**).

---

## Что умеет бот

### 🔍 Карточка компании

По ИНН бот запрашивает данные через DaData API методом `findById/party` и выводит короткую карточку:

- **Название** — краткое с ОПФ
- **ИНН / ОГРН / КПП** — в формате для копирования
- **Статус** — текущее состояние (ACTIVE, LIQUIDATED и др.)
- **Дата регистрации**
- **Адрес** — полный адрес регистрации; отмечается ⚠️, если требует проверки
- **Руководитель** — ФИО и должность
- **ОКВЭД** — основной код и до 3 дополнительных
- **Количество сотрудников**
- **📊 Финансы** *(требует тарифа с финансовой отчётностью)*: год, выручка, доход, расходы
- **👥 Учредители** *(требует расширенного тарифа)*: до 5 учредителей с долями; если их больше — указывается остаток
- **⚠️ Недостоверные сведения** — флаг, если в ЕГРЮЛ есть отметка о недостоверности

### 🧩 Разделы по кнопкам

- **⚖️ Суды** — статус и юридические сигналы из DaData; полные списки дел требуют внешнего провайдера
- **💰 Оборот** — `finance.year/revenue/income/expense` из DaData
- **🧾 Долги** — `finance.debt` из DaData (при наличии в тарифе)
- **⚠️ Штрафы** — `finance.penalty` из DaData (при наличии в тарифе)
- **📄 Реквизиты** — готовый блок для копирования
- **📞 Контакты** — телефоны и email
- **👥 Учредители** — список учредителей и доли

### 📋 Подробности (legacy-кнопка, совместимость)

- **ФНС** — орган регистрации
- **ИФНС** — налоговый орган по месту учёта
- **ПФР** — пенсионный фонд
- **Свидетельство** — серия, номер, дата выдачи
- **📞 Телефоны** *(требует расширенного тарифа)*: до 3 номеров
- **✉️ Email** *(требует расширенного тарифа)*: до 3 адресов

### 📋 Реквизиты (кнопка «Скопировать реквизиты»)

Текстовый блок в формате для копирования:
```
Наименование: ...
ИНН: ...
ОГРН: ...
КПП: ...
Адрес: ...
Руководитель: ...
```

### 🏢 Филиалы (кнопка «Филиалы (N)»)

- Список до 50 филиалов, по 5 на странице
- Для каждого: название, КПП, адрес
- Навигация кнопками ◀️ / ▶️

### ⚡ Технические возможности

- **Прямой ввод ИНН** — можно отправить 10 или 12 цифр без нажатия кнопки
- **Кеширование** — ответы DaData кешируются на 15 минут (до 512 записей)
- **Rate limit** — защита от спама: не чаще 1 запроса в 0,5 сек на пользователя
- **Валидация** — проверяет длину и формат ИНН, выводит понятные ошибки

---

> **Примечание по тарифам DaData:**  
> Базовые данные (название, ИНН, ОГРН, адрес, руководитель, ОКВЭД) доступны на бесплатном тарифе.  
> Финансы, учредители, телефоны и email требуют платного расширенного тарифа DaData.

---

## Переменные окружения

| Переменная          | Обязательна | Описание                                      |
|---------------------|-------------|-----------------------------------------------|
| `TELEGRAM_BOT_TOKEN`| ✅           | Токен Telegram-бота (от @BotFather)           |
| `DADATA_API_KEY`    | ✅           | API-ключ DaData                               |
| `WEBHOOK_URL`       | ⚠️           | Базовый URL сервиса (без `/tg/webhook`), обязателен для Telegram webhook; может быть пустым для локального smoke `/health` |
| `POSTGRES_HOST`     | ❌           | Хост PostgreSQL (включает логирование запросов в БД) |
| `POSTGRES_PORT`     | ❌           | Порт PostgreSQL (по умолчанию `5432`)         |
| `POSTGRES_DB`       | ❌           | Имя базы данных PostgreSQL                     |
| `POSTGRES_USER`     | ❌           | Пользователь PostgreSQL                        |
| `POSTGRES_PASSWORD` | ❌           | Пароль PostgreSQL                              |
| `PORT`              | ❌           | Порт сервера (по умолчанию `3000`)            |

---

## Запуск локально

### Быстрый старт (рекомендуется)

```bash
# 1. Bootstrap: создать venv и установить зависимости
bash scripts/bootstrap.sh

# 2. Настроить переменные окружения
cp .env.example .env
# Отредактируйте .env и заполните TELEGRAM_BOT_TOKEN, DADATA_API_KEY, WEBHOOK_URL

# 3. Запустить тесты
bash scripts/test.sh -q

# 4. Запустить сервер (считывает .env автоматически)
bash scripts/run.sh
```

### Вручную (без скриптов)

```bash
# 1. Создайте и активируйте виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# 2. Установите зависимости
pip install --upgrade pip
pip install -r requirements.txt

# 3. Задайте переменные окружения
export TELEGRAM_BOT_TOKEN=<ваш токен>
export DADATA_API_KEY=<ваш ключ>
export WEBHOOK_URL=https://your-ngrok-or-domain.example.com
export PORT=3000

# 4. Запустите тесты
pytest -q

# 5. Запустите сервер
uvicorn app.main:app --host 0.0.0.0 --port 3000
```

Для локального тестирования webhook можно использовать [ngrok](https://ngrok.com/):

```bash
ngrok http 3000
# Скопируйте HTTPS URL и установите его в WEBHOOK_URL (в .env или export)
```

---


## Проверенный локальный запуск (smoke)

Для smoke-проверки сервиса (endpoint `/health`) можно запускать приложение с тестовыми значениями ENV:

```bash
export TELEGRAM_BOT_TOKEN=123456:ABCdefGhIkl-zyx57W2v1u123ew11
export DADATA_API_KEY=dummy
export WEBHOOK_URL=
uvicorn app.main:app --host 127.0.0.1 --port 3000
```

Проверка:

```bash
curl http://127.0.0.1:3000/health
# {"status":"ok"}
```

> Важно: даже для локального запуска `TELEGRAM_BOT_TOKEN` должен иметь корректный формат токена Telegram,
> иначе приложение завершится на старте из-за валидации aiogram.

### Типичные ошибки ENV / webhook

- `WEBHOOK_URL` пустой — приложение стартует, но webhook не регистрируется (это ожидаемо для локального smoke).
- `WEBHOOK_URL` невалидный (без `http(s)://...`) — в логах WARNING, `setWebhook` пропускается.
- `TELEGRAM_BOT_TOKEN` пустой — `POST /tg/webhook` возвращает `503`, `/health` продолжает работать.
- Ошибка `401` при запросах в DaData — неверный `DADATA_API_KEY`.
- Ошибка `403`/`429` в DaData — лимиты тарифа/частоты запросов.

## Деплой на Amvera

1. Создайте проект в [Amvera](https://amvera.ru/), выберите тип **«Веб-сервис»**.
2. Добавьте переменные окружения (Secrets) в настройках проекта:
   - `TELEGRAM_BOT_TOKEN`
   - `DADATA_API_KEY`
   - `WEBHOOK_URL` — укажите публичный URL вашего сервиса, например `https://my-bot.amvera.io`
3. Задеплойте код — Amvera автоматически соберёт Docker-образ и запустит:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

Webhook Telegram регистрируется автоматически при старте приложения на endpoint `POST /tg/webhook`.  
Healthcheck доступен по `GET /health`.

---

## Решение: деплой DaData MCP на Amvera под домен ewerest.ru

## Шаги

**1. Подготовка репозитория**

```bash
# Распакуй архив
tar -xzf dadata-mcp-server.tar.gz
cd dadata-mcp

# Инициализируй Git
git init
git add .
git commit -m "DaData MCP server"
```

**2. Создай конфиг Amvera**

```bash
cat > amvera.yml << 'EOF'
meta:
  environment: python
  toolchain:
    name: python
    version: 3.11

build:
  - pip install -r requirements.txt

run:
  command: python dadata_mcp.py
  port: 8080

env:
  - DADATA_API_KEY
  - DADATA_SECRET_KEY
EOF

git add amvera.yml
git commit -m "Add Amvera config"
```

**3. Создай проект на Amvera**

1. Зайди на <https://amvera.ru>
2. Новый проект → Python
3. Подключи Git репозиторий
4. Домен: `dadata.ewerest.ru` или `api.ewerest.ru/dadata`

**4. Настрой переменные окружения**

В настройках Amvera → Environment Variables:

```text
DADATA_API_KEY = твой_api_key
DADATA_SECRET_KEY = твой_secret_key
```

**5. Деплой**

```bash
git push amvera main
```

**6. Настрой DNS**

В REG.RU (ewerest.ru):

```text
Тип: CNAME
Имя: dadata (или api)
Значение: [домен_из_Amvera].amvera.app
```

**7. Обнови конфиг Claude Desktop**

```json
{
  "mcpServers": {
    "dadata": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "https://dadata.ewerest.ru/tools/call",
        "-H", "Content-Type: application/json",
        "-d", "@-"
      ]
    }
  }
}
```

## Эффект

**Доступ:**
- Claude Desktop (Артём) ✓
- Telegram бот ✓
- Bitrix24 webhook ✓
- Сайт ewerest.ru ✓
- Вся команда ✓

**Endpoint:**
```text
https://dadata.ewerest.ru/api/find-by-inn
https://dadata.ewerest.ru/api/suggest-party
https://dadata.ewerest.ru/api/clean-address
```

**Масштабирование:**
- 100+ запросов/сек
- Автоматические рестарты
- SSL из коробки

## Риски

**Если домен занят:**
→ Использовать поддомен api.ewerest.ru/dadata

**Если превышен лимит Amvera:**
→ Бесплатный тариф: 512MB RAM, может не хватить
→ Перейти на платный: 200₽/мес

**Если MCP не поддерживает HTTP:**
→ Claude Desktop работает только со stdio/SSE
→ Нужен wrapper или использовать для Telegram/Bitrix24

## Альтернативы

**Вместо HTTP endpoint:**
SSE (Server-Sent Events) для Claude Desktop:

```python
# Добавить в dadata_mcp.py
from mcp.server.sse import SseServerTransport

async def main():
    async with mcp.run_sse() as streams:
        # SSE endpoint
        pass
```

**Вместо Amvera:**
- Railway (аналогично, но дороже)
- Render (бесплатный tier, но медленнее)
- VPS (Timeweb, 200₽/мес, больше контроля)

## Неизвестно

**Claude Desktop поддержка HTTP MCP:**
→ [[TBD: проверить документацию MCP]]
→ Возможно нужен stdio transport локально
→ HTTP только для внешних интеграций

**Лимиты Amvera бесплатного плана:**
→ [[TBD: уточнить на amvera.ru/pricing]]
→ Может потребоваться платный тариф

**Настройки ewerest.ru DNS:**
→ [[TBD: доступ к панели REG.RU]]
→ Время пропагации: до 24 часов

## Рекомендация

**Для Claude Desktop:**
Оставить локально (stdio transport)

**Для команды:**
Деплой на Amvera (HTTP API)

**Гибридная схема:**
```text
Claude Desktop (локально)
  └─ stdio: dadata_mcp.py

Команда (удаленно)
  └─ HTTP: https://dadata.ewerest.ru
      ├─ Telegram Bot
      ├─ Bitrix24
      └─ Website
```

Нужен ли HTTP endpoint для Claude или только для интеграций?

---

## Методы DaData

Подтверждённые в коде проекта методы и параметры DaData (включая соответствие логике страницы `api/find-party` и примечание по `dadata-py`) вынесены в отдельный документ: `docs/dadata_methods.md`.

## Структура проекта

```text
app/
  main.py           # FastAPI приложение + webhook wiring + setWebhook
  bot.py            # Handlers, keyboards, FSM states (aiogram v3)
  config.py         # Конфигурация ENV (Telegram, DaData, PostgreSQL)
  dadata_client.py  # Async httpx клиент DaData + TTLCache 15 мин
  db.py             # asyncpg pool + init таблицы + логирование запросов
  formatters.py     # Форматирование карточки / деталей / реквизитов / филиалов
tests/
  test_validation.py  # Unit-тесты валидации ИНН
  test_formatters.py  # Unit-тесты форматирования карточки
requirements.txt
Dockerfile
```
