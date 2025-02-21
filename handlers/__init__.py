from aiogram import Router


def get_routers():
    from . import (
        admin_orders,
        admin_assortment,
        chat_handlers,
        message_handling,
        start_and_admin,
        user_interaction,
    )

    router = Router()
    router.include_routers(
        admin_orders.router,
        admin_assortment.router,
        chat_handlers.router,
        message_handling.router,
        start_and_admin.router,
        user_interaction.router,
    )
    return router
