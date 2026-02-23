from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='🏢 ООО'), KeyboardButton(text='👤 ИП')],
        [KeyboardButton(text='🧍 Физлицо')],
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
            InlineKeyboardButton(text='🔗 Связи', callback_data='sec:links'),
            InlineKeyboardButton(text='💰 Долги', callback_data='sec:debt'),
            InlineKeyboardButton(text='⚖️ Суды', callback_data='sec:court'),
            InlineKeyboardButton(text='➕ Ещё', callback_data='sec:more'),
        ],
    ]
)

MORE_SECTIONS_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text='🧬 Аффилированные', callback_data='sec:aff'),
            InlineKeyboardButton(text='📊 Финансы', callback_data='sec:fin'),
            InlineKeyboardButton(text='📄 Лицензии/документы', callback_data='sec:docs'),
        ],
        [
            InlineKeyboardButton(text='🏛 Органы', callback_data='sec:auth'),
            InlineKeyboardButton(text='🧾 ОКВЭД', callback_data='sec:okved'),
            InlineKeyboardButton(text='🧩 JSON', callback_data='sec:json'),
        ],
        [
            InlineKeyboardButton(text='⬅️ Назад', callback_data='nav:back'),
            InlineKeyboardButton(text='🆕 Новый поиск', callback_data='nav:new'),
        ],
    ]
)


def section_keyboard(back: str = 'nav:back') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='⬅️ Назад', callback_data=back),
                InlineKeyboardButton(text='🧩 JSON', callback_data='sec:json'),
            ],
            [InlineKeyboardButton(text='🆕 Новый поиск', callback_data='nav:new')],
        ]
    )

SIMPLE_RESULT_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='🔁 Другой ИНН', callback_data='check_another')],
    ]
)
