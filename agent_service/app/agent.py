import os
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from typing import Optional
from sqlalchemy import select
from datetime import datetime
from sqlalchemy.orm import selectinload, joinedload
from langgraph.checkpoint.memory import MemorySaver

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
        try:
            fecha = datetime.strptime(appointment_date, "%Y-%m-%d %H:%M")
        except ValueError:
            return "Formato de fecha inválido. Utiliza el formato: YYYY-MM-DD HH:MM"

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
async def cancel_appointment(appointment_id: int) -> str:
    """Cancelar una cita por ID."""
    async with AsyncSessionLocal() as session:
        stmt = select(AppointmentRegister).where(AppointmentRegister.id == appointment_id).options(joinedload(AppointmentRegister.doctor))
        result = await session.execute(stmt)
        appointment = result.scalar_one_or_none()

        if not appointment:
            return f"No existe la cita con ID {appointment_id}"

        if appointment.status == Status.CANCELLED:
            return f"La cita con ID {appointment_id} ya se encuentra cancelada"

        if appointment.status == Status.COMPLETED:
            return f"No se puede cancelar la cita con ID {appointment_id} porque ya se encuentra completada"
        
        doctor_name = appointment.doctor.name
        appointment.status = Status.CANCELLED
        await session.commit()
        await session.refresh(appointment)

        return f"Cita cancelada exitosamente: Paciente {appointment.patient_name} | Fecha {appointment.appointment_date} | Doctor {doctor_name}"


@tool 
async def reschedule_appointment(appointment_id: int, new_date: str) -> str:
    """Reagendar cita por ID y nueva fecha"""
    async with AsyncSessionLocal() as session:
        try:
            fecha = datetime.strptime(new_date, "%Y-%m-%d %H:%M")
        except ValueError:
            return "Formato de fecha inválido. Utiliza el formato: YYYY-MM-DD HH:MM"

        if fecha <= datetime.now():
            return f"No se puede reagendar la cita porque la nueva fecha es menor a la fecha actual, ingresa una fecha mayor a la fecha actual"

        stmt = select(AppointmentRegister).where(AppointmentRegister.id == appointment_id).options(joinedload(AppointmentRegister.doctor))
        result = await session.execute(stmt)
        appointment = result.scalar_one_or_none()

        if not appointment:
            return f"No existe la cita con ID {appointment_id}"

        if appointment.status == Status.CANCELLED:
            return f"No se puede reagendar la cita con ID {appointment_id} porque ya se encuentra cancelada"

        if appointment.status == Status.COMPLETED:
            return f"No se puede reagendar la cita con ID {appointment_id} porque ya se encuentra completada, agenda una nueva cita"
        
        doctor_name = appointment.doctor.name
        appointment.appointment_date = fecha
        await session.commit()
        await session.refresh(appointment)

        return f"Cita reagendada exitosamente: Paciente {appointment.patient_name} | Nueva Fecha {appointment.appointment_date} | Doctor {doctor_name}"


@tool 
async def update_appointments_notes(appointment_id: int, notes: str) -> str:
    """Actualizar notas de una cita por ID"""
    async with AsyncSessionLocal() as session:
        stmt = select(AppointmentRegister).where(AppointmentRegister.id == appointment_id)
        result = await session.execute(stmt)
        appointment = result.scalar_one_or_none()

        if not appointment:
            return f"No existe la cita con ID {appointment_id}"

        appointment.notes = notes
        await session.commit()
        await session.refresh(appointment)

        return f"Notas actualizadas exitosamente: Paciente {appointment.patient_name} | Notas {appointment.notes}"


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

memory = MemorySaver()

agent_executor = create_react_agent(
    model=llm,
    tools=tools,
    prompt=system_prompt,
    checkpointer=memory,
)


async def run_agent_chat(user_message: str, session_id: str = "default_session") -> str:
    """Procesa el mensaje del usuario con el agente y devuelve la respuesta final en texto."""
    inputs = {"messages": [("user", user_message)]}

    # Configuración obligatoria para que el MemorySaver sepa a qué chat pertenece
    config = {"configurable": {"thread_id": session_id}}

    # Invocamos el agente pasando el config y la memoria
    response = await agent_executor.ainvoke(inputs, config=config)

    # Extraemos el último mensaje generado por el asistente
    final_message = response["messages"][-1].content
    return final_message