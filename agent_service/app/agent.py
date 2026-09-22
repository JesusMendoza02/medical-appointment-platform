import os
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from typing import Optional
from sqlalchemy import select
from datetime import datetime
from sqlalchemy.orm import selectinload, joinedload

# Importamos la sesión de base de datos y los modelos
from app.database import AsyncSessionLocal
from app.models import Doctor, AppointmentRegister, Status

load_dotenv()


@tool
async def get_appointments_by_patient_name(patient_name: str) -> str:
    """Busca las citas por el nombre del paciente y devuelve todos sus detalles."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(AppointmentRegister)
            .options(joinedload(AppointmentRegister.doctor))
            .where(AppointmentRegister.patient_name.ilike(f"%{patient_name}%"))
        )
        result = await session.execute(stmt)
        appointments = result.scalars().all()

        if not appointments:
            return f"No hay citas para el paciente '{patient_name}'"

        appointments_list = [
            f"- Paciente: '{a.patient_name}' | Día de la Cita: '{a.appointment_date}' | Estatus: '{a.status.value}' | Notas: '{a.notes or 'Sin notas'}' | Doctor: '{a.doctor.name}'"
            for a in appointments
        ]

        return f"Las citas del paciente '{patient_name}':\n" + "\n".join(appointments_list)


@tool
async def get_doctor_appointments(doctor_name: str) -> str:
    """Busca el doctor por su nombre y devuelve todas sus citas con todos sus detalles."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Doctor)
            .options(selectinload(Doctor.appointments))
            .where(Doctor.name.ilike(f"%{doctor_name}%"))
        )
        result = await session.execute(stmt)
        doctors = result.scalars().all()

        if not doctors:
            return f"No hay doctor con el nombre '{doctor_name}'"

        response_lines = []
        for doc in doctors:
            if not doc.appointments:
                response_lines.append(f"El doctor '{doc.name}' no tiene citas agendadas")
            else:
                appointments_list = [
                    f"- Paciente: '{a.patient_name}' | Día de la Cita: '{a.appointment_date}' | Estatus: '{a.status.value}' | Notas: '{a.notes or 'Sin notas'}'"
                    for a in doc.appointments
                ]
                response_lines.append(f"Citas para el Dr. {doc.name}:\n" + "\n".join(appointments_list))

        return "\n\n".join(response_lines)


@tool
async def get_doctors_by_specialty(specialty: str) -> str:
    """Busca doctores por especialidad y devuelve todos sus datos."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Doctor).where(Doctor.specialty.ilike(f"%{specialty}%"))
        )
        result = await session.execute(stmt)
        doctors = result.scalars().all()

        if not doctors:
            return f"No hay doctores con la especialidad '{specialty}'"

        doctors_list = [
            f"- Nombre: {d.name}, Especialidad: {d.specialty}"
            for d in doctors
        ]

        return f"Doctores con la especialidad '{specialty}':\n" + "\n".join(doctors_list)


@tool
async def get_appointments_by_status(status: str) -> str:
    """Busca citas por su estatus (SCHEDULED, COMPLETED, CANCELLED) y devuelve todos sus datos."""
    async with AsyncSessionLocal() as session:
        status_upper = status.upper()

        try:
            status_enum = Status[status_upper]
        except KeyError:
            return f"Estatus no válido: '{status}'. Los valores permitidos son: SCHEDULED, COMPLETED, CANCELLED."

        stmt = (
            select(AppointmentRegister)
            .options(joinedload(AppointmentRegister.doctor))
            .where(AppointmentRegister.status == status_enum)
        )
        result = await session.execute(stmt)
        appointments = result.scalars().all()

        if not appointments:
            return f"No hay citas con el estado '{status}'"

        appointments_list = [
            f"- Paciente: {a.patient_name} | Día de la Cita: {a.appointment_date} | Notas: {a.notes or 'Sin notas'} | Doctor: {a.doctor.name}"
            for a in appointments
        ]

        return f"Citas con el estado '{status}':\n" + "\n".join(appointments_list)

@tool
async def create_appointment(patient_name: str, doctor_id: int, appointment_date: str, notes: Optional[str] = None) -> str:
    """Agendar nuevas citas y valida que no existan citas dobles y que la fecha no sea menor a la fecha actual."""
    async with AsyncSessionLocal() as session:
        fecha = datetime.strptime(appointment_date, "%Y-%m-%d %H:%M")

        stmt = select(Doctor).where(Doctor.id == doctor_id)
        result = await session.execute(stmt)
        doctor = result.scalar_one_or_none()

        stmt = select(AppointmentRegister).where((
            AppointmentRegister.appointment_date == fecha) & (AppointmentRegister.doctor_id == doctor_id))                       
        result = await session.execute(stmt)
        fecha_ocupada = result.scalar_one_or_none()

        if not doctor:
            return f"No existe el doctor con ID {doctor_id}"

        if fecha_ocupada:
            return f"Ya existe una cita para el doctor {doctor.name} el {appointment_date}"
        
        if fecha <= datetime.now():
            return f"No se pueden crear citas en fechas pasadas"

        new_appointment = AppointmentRegister(
            patient_name=patient_name,
            doctor_id=doctor_id,
            appointment_date=fecha,
            notes=notes
        )

        session.add(new_appointment)
        await session.commit()
        await session.refresh(new_appointment)

        return f"Cita creada exitosamente: Paciente {patient_name} | Fecha {appointment_date} | Doctor {doctor.name}"



@tool 
async def cancel_appointment() -> str:
    pass

@tool 
async def reschedule_appointment() -> str:
    pass

@tool 
async def update_appointments_notes() -> str:
    pass

# --- Configuración del agente ---

tools = [
    get_appointments_by_patient_name,
    get_appointments_by_status,
    get_doctor_appointments,
    get_doctors_by_specialty,
    create_appointment,
    cancel_appointment,
    reschedule_appointment,
    update_appointments_notes,
]

llm = ChatOllama(
    model="llama3.2",
    temperature=0,
)

system_prompt = (
    "Eres un asistente de la base de datos de citas médicas. "
    "Tu función es consultar la base de datos y reportar ÚNICAMENTE la información real encontrada.\n\n"
    "MAPEO DE ESTADOS EN LA BASE DE DATOS:\n"
    "- 'Citas activas', 'programadas' o 'pendientes' equivalen a status = 'SCHEDULED'\n"
    "- 'Citas completadas' o 'atendidas' equivalen a status = 'COMPLETED'\n"
    "- 'Citas canceladas' equivalen a status = 'CANCELLED'\n\n"
    "REGLAS OBLIGATORIAS:\n"
    "1. NUNCA digas 'Lo siento' ni 'No tengo acceso a la base de datos'.\n"
    "2. Si la consulta no devuelve resultados, indica que no existen registros.\n"
    "3. Ordena los resultados por fecha según lo solicite el usuario."
)

agent_executor = create_react_agent(
    model=llm,
    tools=tools,
    prompt=system_prompt,
)


async def run_agent_chat(user_message: str) -> str:
    """Procesa el mensaje del usuario con el agente y devuelve la respuesta final en texto."""
    inputs = {"messages": [("user", user_message)]}

    # Invocamos el agente de forma asíncrona
    response = await agent_executor.ainvoke(inputs)

    # Extraemos el último mensaje generado por el asistente
    final_message = response["messages"][-1].content
    return final_message
