from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def start_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начать анализ", callback_data="start_analysis")],
        [InlineKeyboardButton(text="Помощь", callback_data="show_help")]
    ])
    return kb

def registration_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, зарегистрироваться", callback_data="reg_confirm")],
        [InlineKeyboardButton(text="❌ Нет, позже", callback_data="reg_cancel")]
    ])
    return kb

def tool_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("QIIME2", callback_data="tool:QIIME2"),
         InlineKeyboardButton("DADA2", callback_data="tool:DADA2")],
        [InlineKeyboardButton("USEARCH", callback_data="tool:USEARCH")],
        [InlineKeyboardButton("Отменить", callback_data="run_cancel")]
    ])
    return kb

def reference_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("SILVA", callback_data="ref:SILVA"),
         InlineKeyboardButton("Greengenes", callback_data="ref:Greengenes")],
        [InlineKeyboardButton("Отменить", callback_data="run_cancel")]
    ])
    return kb

def clustering_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("OTU", callback_data="cluster:OTU"),
         InlineKeyboardButton("ASV", callback_data="cluster:ASV")],
        [InlineKeyboardButton("Отменить", callback_data="run_cancel")]
    ])
    return kb

def confirm_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Запустить анализ", callback_data="confirm_run")],
        [InlineKeyboardButton("Отменить", callback_data="run_cancel")]
    ])
    return kb