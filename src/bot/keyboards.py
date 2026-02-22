from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='🏢 1) Всё об организации'), KeyboardButton(text='🧑‍💼 2) Всё об ИП')],
        [KeyboardButton(text='🪪 3) Физлицо'), KeyboardButton(text='🔎 Проверить ИНН')],
        [KeyboardButton(text='📧 По email'), KeyboardButton(text='🔍 Самозанятый')],
    ],
    resize_keyboard=True,
)

NAV_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='◀️ Назад'), KeyboardButton(text='🏠 Домой')],
    ],
    resize_keyboard=True,
)

ORG_RESULT_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text='⚠️ Риски', callback_data='risks'),
            InlineKeyboardButton(text='📎 Связи', callback_data='connections'),
            InlineKeyboardButton(text='🔁 Другой ИНН', callback_data='check_another'),
        ],
    ]
)

SIMPLE_RESULT_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='🔁 Другой ИНН', callback_data='check_another')],
    ]
)
