import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select

from app.database import AsyncSessionLocal, engine
import app.models as models


async def seed_data():
    # 1. Crear las tablas si aún no existen
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

    # 2. Insertar registros de prueba
    async with AsyncSessionLocal() as session:
        # Verificar si ya existen datos de doctores para evitar duplicados
        result = await session.execute(select(models.Doctor))
        if result.scalars().first():
            print("⚠️  La base de datos ya contiene información.")
            return

        print("🌱 Insertando datos de prueba...")

        # Doctores
        doctor1 = models.Doctor(name="Dr. García", specialty="Cardiología")
        doctor2 = models.Doctor(name="Dra. López", specialty="Pediatría")
        doctor3 = models.Doctor(name="Dr. Martínez", specialty="Medicina General")

        session.add_all([doctor1, doctor2, doctor3])
        await session.flush()  # Obtener IDs generados

        # Citas
        now = datetime.now()
        citas = [
            models.AppointmentRegister(
                patient_name="Carlos Gómez",
                appointment_date=now + timedelta(days=1, hours=2),
                status="SCHEDULED",
                notes="Chequeo cardiovascular de rutina",
                doctor_id=doctor1.id,
            ),
            models.AppointmentRegister(
                patient_name="Ana Hernández",
                appointment_date=now + timedelta(days=2, hours=4),
                status="SCHEDULED",
                notes="Revisión mensual pediatría",
                doctor_id=doctor2.id,
            ),
            models.AppointmentRegister(
                patient_name="Roberto Sánchez",
                appointment_date=now - timedelta(days=1),
                status="COMPLETED",
                notes="Consulta general por tos y fiebre",
                doctor_id=doctor3.id,
            ),
            models.AppointmentRegister(
                patient_name="Mariana Torres",
                appointment_date=now + timedelta(days=3),
                status="CANCELLED",
                notes="Cancelado por el paciente",
                doctor_id=doctor1.id,
            ),
        ]

        session.add_all(citas)
        await session.commit()
        print("✅ Base de datos poblada exitosamente con doctores y citas.")


if __name__ == "__main__":
    asyncio.run(seed_data())
