from aiogram import Router

from bot.handlers import common, habits_add, habits_list, stats, today


def get_root_router() -> Router:
    router = Router()
    # common первым: /cancel должен срабатывать в любом состоянии диалога
    router.include_routers(
        common.router, habits_add.router, today.router, habits_list.router, stats.router
    )
    return router
