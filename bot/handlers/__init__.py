from aiogram import Router

from bot.handlers import (
    common,
    fallback,
    habits_add,
    habits_edit,
    habits_list,
    settings,
    stats,
    today,
)


def get_root_router() -> Router:
    router = Router()
    # common первым: /cancel должен срабатывать в любом состоянии диалога;
    # fallback последним: ловит устаревшие кнопки, которые никто не обработал
    router.include_routers(
        common.router,
        habits_add.router,
        habits_edit.router,
        today.router,
        habits_list.router,
        stats.router,
        settings.router,
        fallback.router,
    )
    return router
