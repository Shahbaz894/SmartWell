docker build -t shahbaz/smartwell:v1 . && 
docker tag shahbaz/smartwell:v1 shahbazzulfiqar/smartwell:latest && 
docker push shahbazzulfiqar/smartwell:latest

# IoT Tube Well Management System Backend

A production-ready backend for an **IoT based Tube Well Motor Control System**.  
The system allows users to remotely control a tube well motor, schedule automatic motor operation, and maintain customer **Khata (accounting records)**.

The backend is built using **FastAPI**, **PostgreSQL**, and **MQTT** for reliable communication with ESP32 devices.

---

# Features

## Motor Control
- Start / Stop motor from mobile app
- Near real-time control
- Motor state logging
- Track run duration automatically

## Smart Scheduling
Supports advanced automation:

- Monthly pattern scheduling  
  Example:
  - 7 days ON
  - 3 days OFF
  - 5 days ON

- Daily time slots  
  Example:
  - 08:00 → 12:00
  - 14:00 → 16:00

Background scheduler automatically triggers motor based on these rules.

---

## Khata (Customer Accounting)

Tracks motor usage and billing.

Each record stores:

- Customer name
- Motor run hours
- Price per hour
- Total bill
- Cash received
- Remaining balance
- Payment cleared status

Users can:

- Add entry
- Edit entry
- Delete entry

---

# Technology Stack

Backend framework  
- FastAPI

Database  
- PostgreSQL

ORM  
- SQLAlchemy

Validation  
- Pydantic

IoT communication  
- MQTT

Authentication  
- JWT

Device hardware  
- ESP32 + SIM800L

Package manager  
- uv

---

# Project Architecture

The project follows **Clean Architecture** with separation of responsibilities.


app/
│
├── core/
│ ├── config.py
│ ├── logger.py
│ └── exceptions.py
│
├── db/
│ ├── session.py
│ └── migrations/
│
├── models/
│ ├── user.py
│ ├── device.py
│ ├── motor_log.py
│ ├── schedule.py
│ ├── customer.py
│ └── khata_entry.py
│
├── schemas/
│ ├── user_schema.py
│ ├── device_schema.py
│ ├── motor_schema.py
│ ├── schedule_schema.py
│ ├── customer_schema.py
│ └── khata_schema.py
│
├── repositories/
│ ├── user_repo.py
│ ├── device_repo.py
│ ├── motor_repo.py
│ ├── schedule_repo.py
│ ├── customer_repo.py
│ └── khata_repo.py
│
├── services/
│ ├── auth_service.py
│ ├── device_service.py
│ ├── motor_service.py
│ ├── schedule_service.py
│ └── khata_service.py
│
├── api/
│ ├── auth_routes.py
│ ├── device_routes.py
│ ├── motor_routes.py
│ ├── schedule_routes.py
│ └── khata_routes.py
│
├── workers/
│ └── scheduler_worker.py
│
└── mqtt/
└── mqtt_client.py


---

# System Architecture


Flutter Mobile App
│
│ REST API
▼
FastAPI Backend
│
├── PostgreSQL Database
│
├── MQTT Broker
│ │
│ ▼
│ ESP32 Device
│
└── Background Scheduler


---

# Installation

## Clone the repository


git clone https://github.com/your-repo/iot-tubewell-backend.git

cd iot-tubewell-backend


---

## Create virtual environment

Using **uv**


uv venv


Activate environment

Linux / Mac


source .venv/bin/activate


Windows


.venv\Scripts\activate


---

## Install dependencies


uv pip install -r requirements.txt


---

# Environment Variables

Create `.env`


DATABASE_URL=postgresql://user:password@localhost/tubewell

JWT_SECRET=your_secret_key

MQTT_BROKER=localhost

MQTT_PORT=1883


---

# Run the Server


uvicorn app.main:app --reload


API will run at


http://localhost:8000


Swagger documentation


http://localhost:8000/docs


---

# Running the Scheduler

The scheduler checks automation rules every minute.


python -m app.workers.scheduler_worker


---

# MQTT Communication

ESP32 subscribes to:


tubewell/{device_uid}/motor


Example message


{
"command": "ON"
}


or


{
"command": "OFF"
}


---

# API Endpoints

## Authentication


POST /auth/register
POST /auth/login


## Devices


POST /devices
GET /devices


## Motor


POST /motor/start
POST /motor/stop


## Schedule


POST /schedule
GET /schedule/{device_id}


## Khata


POST /khata
DELETE /khata/{id}


---

# Logging

All system activity is logged:

- motor start
- motor stop
- schedule execution
- errors

Logs help monitor the IoT system.

---

# Security

- JWT authentication
- User data isolation
- Device ownership verification
- Secure API endpoints

---

# Scalability

Designed to support:

- 10,000+ users
- multiple devices per user
- large motor log datasets

Can be deployed on:

- Railway
- DigitalOcean
- AWS
- VPS servers

---

# Future Improvements

Possible upgrades:

- Redis caching
- WebSocket real-time updates
- Advanced analytics dashboard
- SMS alerts
- AI irrigation optimization

---

# License

MIT License

---

# Author

Developed by:

**Shahbaz**

IoT + Embedded Systems Engineer