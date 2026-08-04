from aiogram import Router

from . import admin, browse, common, create, exchange, my_trade, premium, reports


def setup_routers() -> Router:
    router = Router(name="root")
    router.include_router(common.router)
    router.include_router(admin.router)
    router.include_router(premium.router)
    router.include_router(create.router)
    router.include_router(my_trade.router)
    router.include_router(browse.router)
    router.include_router(exchange.router)
    router.include_router(reports.router)
    router.include_router(common.fallback_router)
    return router
