from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from app.models import Status


class AppointmentRegisterBase(BaseModel):
    patient_name: str
    appointment_date: datetime
    status: Status = Status.SCHEDULED
    notes: Optional[str] = None

class AppointmentRegisterCreate(AppointmentRegisterBase):
    doctor_id: int

class AppointmentRegisterResponse(AppointmentRegisterBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DoctorBase(BaseModel):
    name: str
    specialty: str

class DoctorCreate(DoctorBase):
    pass

class DoctorResponse(DoctorBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class DoctorWithAppointmentResponse(DoctorResponse):
    appointments: List[AppointmentRegisterResponse] = []


# --- Esquemas para el Agente de IA / Chat ---
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
