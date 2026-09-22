from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# 1. URL de conexión a la base de datos (SQLite Asíncrono)
DATABASE_URL = "sqlite+aiosqlite:///./doctor_appointments.db"

# 2. Creación del motor de base de datos asíncrono
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Muestra en consola las consultas SQL generadas (excelente para depurar)
)

# 3. Fábrica de sesiones asíncronas (AsyncSession)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Evita recargar objetos tras hacer commit
)


# 4. Inyector de dependencias (Dependency Injection para FastAPI)
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Generador que abre una sesión de BD por cada petición y la cierra al terminar."""
    async with AsyncSessionLocal() as session:
        yield session
