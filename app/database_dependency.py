from app.database_registry import get_sessionmaker


async def get_db():
    session_maker = get_sessionmaker()
    async with session_maker() as session:
        try:
            yield session
            # clean exit → commit
            if session.is_active:
                await session.commit()
        except Exception:
            # any error → rollback
            await session.rollback()
            raise
