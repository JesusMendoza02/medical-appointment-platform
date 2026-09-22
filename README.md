# Doctor Appointments — AI Agent API

Sistema de gestión de citas médicas con agente de IA conversacional, construido con **FastAPI**, **LangGraph**, **Ollama** y **SQLAlchemy async**.

---

## 🗂️ Estructura del proyecto

```
doctor_appointments/
├── agent_service/          # Servicio del agente de IA
│   ├── app/
│   │   ├── main.py         # Entrypoint de FastAPI
│   │   ├── database.py     # Configuración de SQLAlchemy async
│   │   ├── models.py       # Modelos ORM (Doctor, AppointmentRegister)
│   │   ├── schemas.py      # Schemas Pydantic
│   │   └── agent.py        # Agente LangGraph + herramientas
│   ├── scripts/
│   │   └── seed.py         # Script para poblar la BD con datos de prueba
│   ├── .env                # Variables de entorno (no subir a git)
│   ├── .env.example        # Plantilla de variables de entorno
│   └── requirements.txt    # Dependencias del proyecto
│
└── gateway_service/        # API Gateway (en desarrollo)
```

---

## ⚙️ Requisitos

- Python 3.11+
- [Ollama](https://ollama.com/) instalado y corriendo localmente
- Modelo `llama3.2` descargado en Ollama

```bash
ollama pull llama3.2
```

---

## 🚀 Instalación y ejecución

```bash
# 1. Entrar al servicio del agente
cd agent_service

# 2. Crear y activar el entorno virtual
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env

# 5. (Opcional) Poblar la BD con datos de prueba
python -m scripts.seed

# 6. Correr el servidor
uvicorn app.main:app --reload
```

El servidor estará disponible en: http://localhost:8000

Documentación interactiva (Swagger): http://localhost:8000/docs

---

## 💬 Uso del agente

Envía un `POST` a `/chat` con un mensaje en lenguaje natural:

```json
{
  "message": "¿Qué citas tiene el Dr. García?"
}
```

### Herramientas disponibles del agente

| Herramienta | Descripción |
|---|---|
| `get_appointments_by_patient_name` | Busca citas por nombre de paciente |
| `get_doctor_appointments` | Busca todas las citas de un doctor |
| `get_doctors_by_specialty` | Lista doctores por especialidad |
| `get_appointments_by_status` | Filtra citas por estado (SCHEDULED/COMPLETED/CANCELLED) |

---

## 🛠️ Stack tecnológico

- **FastAPI** — Framework web asíncrono
- **LangGraph + LangChain** — Orquestación del agente de IA
- **Ollama (llama3.2)** — LLM local open-source
- **SQLAlchemy 2.0 async** — ORM con soporte asíncrono
- **SQLite + aiosqlite** — Base de datos ligera y asíncrona
- **Pydantic v2** — Validación de datos
