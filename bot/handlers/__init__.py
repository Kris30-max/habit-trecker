from aiogram import Router

from bot.handlers import common


def get_root_router() -> Router:
    router = Router()
    router.include_router(common.router)
    return router
