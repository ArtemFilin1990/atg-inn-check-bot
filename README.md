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

## РЕШЕНИЕ

Архитектура для множественных MCP серверов на Amvera.

## Шаги

**1. Раздели на структуры (monorepo)**

```bash
# Создай общий репозиторий
mkdir everest-mcp-hub
cd everest-mcp-hub
```

**Структура A — MCP серверы (`servers/`)**

```text
servers/
├── dadata/
│   ├── server.py
│   └── requirements.txt
├── bitrix24/
│   ├── server.py
│   └── requirements.txt
├── bearings-catalog/
│   ├── server.py
│   └── requirements.txt
└── telegram/
    ├── server.py
    └── requirements.txt
```

**Структура B — Gateway (`gateway/`)**

```text
gateway/
├── main.py      # API Gateway
└── router.py    # Роутинг запросов
```

**Структура C — Общие модули (`shared/`)**

```text
shared/
├── auth.py      # Общая авторизация
├── cache.py     # Redis кеш
└── logger.py    # Логирование
```

**Структура D — Корень репозитория**

```text
everest-mcp-hub/
├── servers/
├── gateway/
├── shared/
├── amvera.yml
├── requirements.txt
└── README.md
```

**2. API Gateway (main.py)**

```python
"""Единая точка входа для всех MCP серверов Эверест."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
import importlib

app = FastAPI(title="Everest MCP Hub")

# Реестр серверов
SERVERS = {
    "dadata": "servers.dadata.server",
    "bitrix24": "servers.bitrix24.server",
    "bearings": "servers.bearings_catalog.server",
    "telegram": "servers.telegram.server"
}


class MCPRequest(BaseModel):
    server: str  # dadata, bitrix24, bearings, telegram
    tool: str    # имя инструмента
    params: Dict[str, Any]


@app.post("/mcp/call")
async def call_mcp_tool(request: MCPRequest):
    """Роутинг запросов к нужному MCP серверу."""
    if request.server not in SERVERS:
        raise HTTPException(404, f"Server {request.server} not found")

    # Динамическая загрузка сервера
    module = importlib.import_module(SERVERS[request.server])

    # Вызов инструмента
    result = await module.call_tool(request.tool, request.params)

    return {
        "server": request.server,
        "tool": request.tool,
        "result": result
    }


@app.get("/mcp/servers")
async def list_servers():
    """Список доступных MCP серверов."""
    return {
        "servers": [
            {
                "name": "dadata",
                "description": "Проверка контрагентов по ИНН",
                "tools": ["find_by_inn", "suggest_party", "clean_address"]
            },
            {
                "name": "bitrix24",
                "description": "Интеграция с Bitrix24 CRM",
                "tools": ["create_deal", "update_company", "get_lead"]
            },
            {
                "name": "bearings",
                "description": "Каталог подшипников ГОСТ⇄ISO",
                "tools": ["find_analog", "get_specs", "search_bearing"]
            },
            {
                "name": "telegram",
                "description": "Управление Telegram ботами",
                "tools": ["send_message", "create_keyboard", "get_updates"]
            }
        ]
    }


@app.get("/health")
async def health():
    """Проверка работоспособности."""
    return {"status": "ok", "servers": len(SERVERS)}
```

**3. Конфиг Amvera (amvera.yml)**

```yaml
meta:
  environment: python
  toolchain:
    name: python
    version: 3.11

build:
  - pip install -r requirements.txt
  - pip install -r servers/dadata/requirements.txt
  - pip install -r servers/bitrix24/requirements.txt
  - pip install -r servers/bearings-catalog/requirements.txt

run:
  command: uvicorn gateway.main:app --host 0.0.0.0 --port 8080
  port: 8080

env:
  # DaData
  - DADATA_API_KEY
  - DADATA_SECRET_KEY

  # Bitrix24
  - BITRIX24_WEBHOOK_URL
  - BITRIX24_DOMAIN

  # Telegram
  - TELEGRAM_BOT_TOKEN

  # Общие
  - REDIS_URL
  - SECRET_KEY
```

**4. Общий requirements.txt**

```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
httpx>=0.27.0
pydantic>=2.0.0
redis>=5.0.0
python-dotenv>=1.0.0
```

**5. Claude Desktop конфиг**

```json
{
  "mcpServers": {
    "everest-hub": {
      "command": "python",
      "args": ["-m", "everest_mcp_client"],
      "env": {
        "EVEREST_MCP_URL": "https://api.ewerest.ru"
      }
    }
  }
}
```

**6. Клиент для Claude (everest_mcp_client.py)**

```python
"""Клиент для подключения Claude к Everest MCP Hub."""

import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("everest_hub")
hub_url = os.getenv("EVEREST_MCP_URL", "https://api.ewerest.ru")

# Динамическая регистрация всех инструментов
async def init_tools():
    """Получить список инструментов с сервера."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{hub_url}/mcp/servers")
        servers = response.json()["servers"]

        for server in servers:
            for tool_name in server["tools"]:
                register_tool(server["name"], tool_name)


def register_tool(server: str, tool: str):
    """Регистрация инструмента в MCP."""

    @mcp.tool(name=f"{server}_{tool}")
    async def dynamic_tool(**params):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{hub_url}/mcp/call",
                json={
                    "server": server,
                    "tool": tool,
                    "params": params
                }
            )
            return response.json()["result"]
```

## Эффект

**Централизация:**
- Один домен: api.ewerest.ru
- Один деплой: все серверы сразу
- Одна точка мониторинга

**Масштабируемость:**
- Добавление нового MCP: 1 файл в servers/
- Нет изменений в Claude Desktop
- Автоматическая регистрация инструментов

**Переиспользование:**
```python
# Общий кеш для всех серверов
from shared.cache import cache

@cache.memoize(ttl=3600)
async def find_by_inn(inn: str):
    # Кеш работает для всех серверов
    ...
```

## Риски

**Если один сервер упал:**
→ Не влияет на остальные (изолированные модули)

**Если превышен лимит памяти:**
→ Разделить на несколько Amvera проектов:
```text
dadata.ewerest.ru  → только DaData
bitrix.ewerest.ru  → только Bitrix24
api.ewerest.ru     → gateway (роутинг)
```

**Если сложная зависимость:**
→ Отдельный контейнер для тяжелых серверов

## Альтернативы

**Вместо monorepo:**
- Отдельный репозиторий для каждого MCP
- Поддомены: dadata.ewerest.ru, bitrix.ewerest.ru
- Независимый деплой

**Вместо API Gateway:**
- Прямое подключение к каждому серверу
- Claude Desktop знает все endpoints
- Больше гибкости, сложнее управление

## Неизвестно

**Список будущих MCP серверов:**
→ [[TBD: какие еще интеграции планируются?]]
→ 1С? Почта? Склад? Аналитика?

**Нагрузка на систему:**
→ [[TBD: сколько запросов/день?]]
→ Нужен ли Redis или достаточно in-memory?

**Приоритет разработки:**
→ [[TBD: какой MCP делать следующим?]]
→ DaData → Bitrix24 → Bearings → Telegram?

## Следующие MCP для Эверест

**Приоритет 1 (критичные):**
1. ✓ DaData (проверка контрагентов)
2. Bitrix24 (CRM операции)
3. Bearings Catalog (поиск аналогов ГОСТ⇄ISO)

**Приоритет 2 (полезные):**
4. Telegram Manager (управление ботами)
5. Email (отправка КП, счетов)
6. 1С Integration (выгрузка заказов)

**Приоритет 3 (оптимизация):**
7. Analytics (отчеты, метрики)
8. Warehouse (остатки на складе)
9. Delivery (расчет доставки)

Какой MCP создать следующим?

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
