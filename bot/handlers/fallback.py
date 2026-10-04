from aiogram import Router
from aiogram.types import CallbackQuery

from bot import texts

# Подключается последним: ловит кнопки, для которых диалог уже закончился
# (например, «Готово» в старом сообщении после /cancel или рестарта бота).
router = Router(name="fallback")


@router.callback_query()
async def stale_button(query: CallbackQuery) -> None:
    await query.answer(texts.STALE_BUTTON)
