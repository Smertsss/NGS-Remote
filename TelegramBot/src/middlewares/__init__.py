from .auth import AuthMiddleware

async def register_middlewares(dp):
    """Регистрация всех мидлварей"""
    dp.update.middleware(AuthMiddleware())