

docker build -t shahbazzulfiqar/smartwell:latest .
docker build --no-cache -t shahbazzulfiqar/smartwell:v1.0.0 -t shahbazzulfiqar/smartwell:latest .
# IoT Tube Well Management System Backend

A production-ready backend for an **IoT-based Tube Well Motor Control System**.

This system allows users to:

- Remotely start and stop a tube well motor
- Schedule automatic motor operation
- Manage customer **Khata** records
- Track motor activity and usage logs
- Communicate with ESP32 devices over MQTT

The backend is built with:

- **FastAPI**
- **PostgreSQL**
- **MQTT**
- **Docker**
- **DigitalOcean Droplet**

---

# Table of Contents

- [Overview](#overview)
- [Main Features](#main-features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [System Architecture](#system-architecture)
- [Environment Variables](#environment-variables)
- [Local Development Setup](#local-development-setup)
- [Docker Build and Push](#docker-build-and-push)
- [DigitalOcean Production Deployment](#digitalocean-production-deployment)
- [Full Production Setup Commands](#full-production-setup-commands)
- [How to Update Code and Deploy New Version](#how-to-update-code-and-deploy-new-version)
- [How to Stop, Remove, and Recreate Containers](#how-to-stop-remove-and-recreate-containers)
- [Useful Docker Commands](#useful-docker-commands)
- [API Endpoints](#api-endpoints)
- [MQTT Communication](#mqtt-communication)
- [Health Check and Docs](#health-check-and-docs)
- [Logging](#logging)
- [Security](#security)
- [Scalability](#scalability)
- [Troubleshooting](#troubleshooting)
- [Author](#author)
- [License](#license)

---

# Overview

The **IoT Tube Well Management System Backend** is designed for remote motor control and automation in tube well systems.

It supports:

- direct motor start and stop from a mobile application
- smart time-based and pattern-based scheduling
- MQTT messaging with ESP32 devices
- customer billing and Khata record management
- usage monitoring and motor activity logs

This backend is suitable for deployment on a **DigitalOcean droplet** using Docker containers.

---

# Main Features

## 1. Motor Control

- Start motor remotely
- Stop motor remotely
- Track motor running state
- Save motor activity logs
- Calculate run duration automatically

## 2. Smart Scheduling

Supports advanced motor automation, including:

- monthly pattern scheduling
- daily time-slot scheduling
- automatic scheduler execution
- repeated ON and OFF cycle control

### Example scheduling patterns

- 7 days ON, 3 days OFF
- 5 days ON, 2 days OFF

### Example daily time slots

- 08:00 to 12:00
- 14:00 to 16:00

## 3. Khata Management

Tracks customer usage and billing details.

Each record can include:

- customer name
- motor run hours
- price per hour
- total bill
- cash received
- remaining balance
- payment cleared status

Users can:

- add records
- update records
- delete records
- view account history

## 4. IoT Integration

- communicates with ESP32 devices
- sends motor control commands over MQTT
- supports reliable message delivery through broker-based communication

---

# Technology Stack

## Backend

- FastAPI
- SQLAlchemy
- Pydantic
- Uvicorn

## Database

- PostgreSQL

## Communication

- MQTT
- Eclipse Mosquitto

## Authentication

- JWT

## Package Management

- uv

## Containerization

- Docker
- Docker Hub

## Deployment

- DigitalOcean Droplet

## Hardware

- ESP32
- SIM800L

---

# Project Structure

```text
app/
├── api/
│   ├── auth_routes.py
│   ├── device_routes.py
│   ├── khata_routes.py
│   ├── motor_routes.py
│   └── schedule_routes.py
│
├── core/
│   ├── config.py
│   ├── exceptions.py
│   └── logger.py
│
├── db/
│   ├── session.py
│   └── migrations/
│
├── models/
│   ├── customer.py
│   ├── device.py
│   ├── khata_entry.py
│   ├── motor_log.py
│   ├── schedule.py
│   └── user.py
│
├── mqtt/
│   └── mqtt_client.py
│
├── repositories/
│   ├── customer_repo.py
│   ├── device_repo.py
│   ├── khata_repo.py
│   ├── motor_repo.py
│   ├── schedule_repo.py
│   └── user_repo.py
│
├── schemas/
│   ├── customer_schema.py
│   ├── device_schema.py
│   ├── khata_schema.py
│   ├── motor_schema.py
│   ├── schedule_schema.py
│   └── user_schema.py
│
├── services/
│   ├── auth_service.py
│   ├── device_service.py
│   ├── khata_service.py
│   ├── motor_service.py
│   └── schedule_service.py
│
├── workers/
│   └── scheduler_worker.py
│
└── main.py
Root-Level Files
.
├── app/
├── .env
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── README.md
└── .gitignore
System Architecture
Flutter Mobile App
        │
        │ REST API
        ▼
FastAPI Backend
        │
        ├── PostgreSQL Database
        │
        ├── MQTT Broker (Mosquitto)
        │         │
        │         ▼
        │      ESP32 Device
        │
        └── Background Scheduler
Environment Variables

Create a .env file in the project root.

Example .env
DATABASE_URL=postgresql://shahbaz_admin:shahbaz_password@db:5432/smartwell_db
JWT_SECRET=your_secret_key
MQTT_BROKER=iot_project_mosquitto_1
MQTT_PORT=1883
Important Note

In Docker production, the database hostname must match the actual running container name on the Docker network.

For example, if PostgreSQL container name is:

db

Then DATABASE_URL must use:

@db:5432

Do not use:

localhost
127.0.0.1
old container names like iot_project_db_1
Local Development Setup
1. Clone the repository
git clone https://github.com/your-repo/iot-tubewell-backend.git
cd iot-tubewell-backend
2. Create virtual environment
uv venv
3. Activate virtual environment
Linux or Mac
source .venv/bin/activate
Windows
.venv\Scripts\activate
4. Install dependencies
uv pip install -r requirements.txt
5. Run the FastAPI server
uvicorn app.main:app --reload
6. Open in browser

API base URL:

http://localhost:8000

Swagger docs:

http://localhost:8000/docs
Docker Build and Push

When you update your Python code and want to deploy the latest version, first build a new Docker image and push it to Docker Hub.

Build image locally
docker build -t shahbaz/smartwell:v1 .
docker build -t shahbazzulfiqar/smartwell:v1.0.17 .
docker push shahbazzulfiqar/smartwell:v1.0.17
Tag image for Docker Hub
docker tag shahbaz/smartwell:v1 shahbazzulfiqar/smartwell:latest
Push image to Docker Hub
docker push shahbazzulfiqar/smartwell:latest
DigitalOcean Production Deployment



//////////////////////////////////////////
log check karne k lye


tail -n 100 app_source/logs/app.log | grep -i "error"

This section explains the exact production workflow on a DigitalOcean droplet.
mosquitto_sub -h curl -X GET "http://157.245.55.83/telemetry/ESP32_002_TW/latest"-t "tubewell/#" -v // backend par check karna h h data base say kaya data aa raha 
1. Connect to droplet using SSH
ssh root@157.245.55.83
2. Go to project directory
cd /root/iot_project

If the project folder does not exist yet:

mkdir -p /root/iot_project
cd /root/iot_project

Full Production Setup Commands

Use these commands when setting up the project from scratch on the droplet.

1. Create Docker network
docker network create iot_project_smartwell_net

If the network already exists, Docker will show an error. That is okay.

//////////////////////////////////////////////////////////////////////////////////

for push and pull to docker hub
docker build -t shahb
docker push shahbazzulfiqar/smartwell:

for droplet code used for droplet code to fetch docker container
ssh root@157.245.55.83

docker pull shahbazzulfiqar/smartwell:latest
docker rm -f iot_project_backend_1


//////////////////////////////////////////////////////////////////////////

2. Run PostgreSQL container
docker run -d --name db \
  --restart unless-stopped \
  --network iot_project_smartwell_net \
  -v iot_project_postgres_data:/var/lib/postgresql/data \
  -e POSTGRES_USER=shahbaz_admin \
  -e POSTGRES_PASSWORD=shahbaz_password \
  -e POSTGRES_DB=smartwell_db \
  postgres:15
3. Run Mosquitto container
docker run -d --name iot_project_mosquitto_1 \
  --restart unless-stopped \latest
  --network iot_project_smartwell_net \
  -p 1883:1883 \
  eclipse-mosquitto
4. Create .env file
nano /root/iot_project/.envlatest

Paste:

DATABASE_URL=postgresql://shahbaz_admin:shahbaz_password@db:5432/smartwell_db
JWT_SECRET=your_secret_key
MQTT_BROKER=iot_project_mosquitto_1
MQTT_PORT=1883

Save and exit.

5. Pull latest backend image from Docker Hub
docker pull shahbazzulfiqar/smartwell:latest
6. Run backend container
docker run -d --name iot_project_backend_1 \
  --restart unless-stopped \
  --network iot_project_smartwell_net \
  -p 80:8080 \
  --env-file /root/iot_project/.env \
  shahbazzulfiqar/smartwell:latest

6.1 
  docker run -d --name iot_project_backend_1 \
  --restart unless-stopped \
  --network iot_project_smartwell_net \
  -p 80:8080 \
  --env-file /root/iot_project/.env \
  shahbazzulfiqar/smartwell:v1.0.0

  6.2 app.log check karne k lye 
  docker exec -it iot_project_backend_1 tail -n 20 /app/logs/app.log
7. Check running containers
docker ps
8. Check backend logs
docker logs -f iot_project_backend_1
9. Check database logs
docker logs db
10. Verify restart policies
docker inspect -f '{{ .HostConfig.RestartPolicy.Name }}' db
docker inspect -f '{{ .HostConfig.RestartPolicy.Name }}' iot_project_backend_1
docker inspect -f '{{ .HostConfig.RestartPolicy.Name }}' iot_project_mosquitto_1

Expected output:

unless-stopped
How to Update Code and Deploy New Version

Whenever you change your Python code, follow this process.

Step 1. Make code changes locally

Update your FastAPI code on your development machine.

Step 2. Build a new Docker image
docker build -t shahbaz/smartwell:v1 .

You can also use version tags:

docker build -t shahbaz/smartwell:v2 .
Step 3. Tag the image for Docker Hub
docker tag shahbaz/smartwell:v1 shahbazzulfiqar/smartwell:latest


Or with versioned tag:

docker tag shahbaz/smartwell:v2 shahbazzulfiqar/smartwell:v2
docker tag shahbaz/smartwell:v2 shahbazzulfiqar/smartwell:latest
Step 4. Push image to Docker Hub
docker push shahbazzulfiqar/smartwell:latest

If using version tags:
abdulA1ziz

docker push shahbazzulfiqar/smartwell:v2
docker push shahbazzulfiqar/smartwell:latest
Step 5. Connect to DigitalOcean droplet
ssh root@157.245.55.83
Step 6. Pull the latest image on droplet
docker pull shahbazzulfiqar/smartwell:latest
Step 7. Remove old backend container
docker rm -f iot_project_backend_1
Step 8. Start backend again with latest image
docker run -d --name iot_project_backend_1 \
  --restart unless-stopped \
  --network iot_project_smartwell_net \
  -p 80:8080 \
  --env-file /root/iot_project/.env \
  shahbazzulfiqar/smartwell:latest
Step 9. Watch logs
docker logs -f iot_project_backend_1
How to Stop, Remove, and Recreate Containers
Stop a container
docker stop iot_project_backend_1
Start a stopped container
docker start iot_project_backend_1
Remove a container forcefully
docker rm -f iot_project_backend_1
Remove database container
docker rm -f db
Remove mosquitto container
docker rm -f iot_project_mosquitto_1
Remove all three containers
docker rm -f iot_project_backend_1 db iot_project_mosquitto_1
Remove image
docker rmi shahbazzulfiqar/smartwell:latest
Remove volume
docker volume rm iot_project_postgres_data



nano ~/iot_project/docker-compose.yml
Your DB and Mosquitto containers have different names now:

1406e53817ed_iot_project_db_1
9a9b0e277ed3_iot_project_mosquitto_1

Start them with these exact commands:

docker start 1406e53817ed_iot_project_db_1
docker start 9a9b0e277ed3_iot_project_mosquitto_1




Warning: removing the PostgreSQL volume deletes all database data permanently.

Clean Re-Deployment From Scratch

Use this when you want to erase everything and start fresh.

1. Remove backend, database, and broker containers
docker rm -f iot_project_backend_1 db iot_project_mosquitto_1
2. Remove PostgreSQL volume
docker volume rm iot_project_postgres_data
3. Remove backend image if needed
docker rmi shahbazzulfiqar/smartwell:latest
4. Pull latest image again
docker pull shahbazzulfiqar/smartwell:latest
5. Recreate containers
Database
docker run -d --name db \
  --restart unless-stopped \
  --network iot_project_smartwell_net \
  -v iot_project_postgres_data:/var/lib/postgresql/data \
  -e POSTGRES_USER=shahbaz_admin \
  -e POSTGRES_PASSWORD=shahbaz_password \
  -e POSTGRES_DB=smartwell_db \
  postgres:15
MQTT broker
docker run -d --name iot_project_mosquitto_1 \
  --restart unless-stopped \
  --network iot_project_smartwell_net \
  -p 1883:1883 \
  eclipse-mosquitto
Backend
docker run -d --name iot_project_backend_1 \
  --restart unless-stopped \
  --network iot_project_smartwell_net \
  -p 80:8080 \
  --env-file /root/iot_project/.env \
  shahbazzulfiqar/smartwell:latest
Docker Compose Workflow

If you prefer Docker Compose, use the following commands.

Stop and wipe everything
docker-compose down -v
Rebuild backend with no cache
docker-compose build --no-cache backend
Start services
docker-compose up -d

Use this method only if you are actually managing the project with docker-compose.yml.

If you are deploying by manual docker run commands, do not mix both methods unless you know exactly what is running.

Useful Docker Commands
Show all running containers
docker ps
Show all containers including stopped ones
docker ps -a
Show container logs
docker logs iot_project_backend_1
docker logs db
docker logs iot_project_mosquitto_1
Follow logs live
docker logs -f iot_project_backend_1
Inspect environment values
docker inspect db --format='{{range .Config.Env}}{{println .}}{{end}}'
Check backend environment
docker exec -it iot_project_backend_1 printenv
Open shell inside backend container
docker exec -it iot_project_backend_1 sh
Check Docker network
docker network inspect iot_project_smartwell_net
Pull latest backend image
docker pull shahbazzulfiqar/smartwell:latest
API Endpoints
Authentication
POST /auth/register
POST /auth/login
Devices
POST /devices
GET /devices
Motor
POST /motor/start
POST /motor/stop
Schedule
POST /schedule
GET /schedule/{device_id}
Khata
POST /khata
DELETE /khata/{id}
MQTT Communication

ESP32 devices subscribe to the following topic format:

tubewell/{device_uid}/motor
Example ON command
{
  "command": "ON"
}
Example OFF command
{
  "command": "OFF"
}
Health Check and Docs
Health endpoint
curl http://localhost/

Expected response:

{"status":"online","message":"IoT TubeWell Backend is running"}
Swagger documentation

Open:

http://localhost/docs

Or from public server:

http://YOUR_SERVER_IP/docs
Logging

The system logs important events such as:

motor start
motor stop
schedule execution
background job activity
database initialization issues
API errors

Use Docker logs for production monitoring:

docker logs -f iot_project_backend_1
Security
JWT authentication
protected API routes
device ownership validation
isolated database-backed user records
containerized deployment for better isolation
Production Recommendations
use a strong JWT_SECRET
restrict SSH access
use firewall rules on DigitalOcean
expose port 1883 only if required externally
use HTTPS with Nginx reverse proxy if going public
Scalability

The backend is designed to support:

many users
multiple devices per user
large motor log datasets
scheduled automation workloads

This project can be deployed on:

DigitalOcean
AWS
Railway
VPS servers
other Linux cloud environments
Troubleshooting
1. Backend fails with database initialization error

Check:

docker logs iot_project_backend_1
docker logs db

Make sure .env contains the correct database hostname:

DATABASE_URL=postgresql://shahbaz_admin:shahbaz_password@db:5432/smartwell_db
2. Container name conflict

Example error:

Conflict. The container name "/db" is already in use

Fix:

docker rm -f db

Then recreate container.

3. Backend cannot connect to database

Check the Docker network:

docker network inspect iot_project_smartwell_net

Make sure both containers are attached to the same network.

4. Latest code not showing in production

This usually means the latest image was not built or pulled.

Run:

docker build -t shahbaz/smartwell:v1 .
docker tag shahbaz/smartwell:v1 shahbazzulfiqar/smartwell:latest
docker push shahbazzulfiqar/smartwell:latest

ssh root@157.245.55.83
docker pull shahbazzulfiqar/smartwell:latest
docker rm -f iot_project_backend_1
docker run -d --name iot_project_backend_1 \
  --restart unless-stopped \
  --network iot_project_smartwell_net \
  -p 80:8080 \
  --env-file /root/iot_project/.env \
  shahbazzulfiqar/smartwell:latest
5. PostgreSQL data reset required

To fully reset database data:

docker rm -f db
docker volume rm iot_project_postgres_data

Then recreate the database container.

Warning: this deletes all saved database data.

Author

Developed by:

Shahbaz

IoT and Embedded Systems Engineer






mosquitto:
    image: eclipse-mosquitto:2
    container_name: iot_project_mosquitto_1
    restart: always
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
    networks:
      - smartwell_net
    deploy:
      resources:
        limits:
          memory: 40M



  JWT_SECRET_KEY: f66b65571dc72b984583b52f954f8d010bf5ca4f16598f0c862037fda6820894
  JWT_SECRET_KEY: f66b65571dc72b984583b52f954f8d010bf5ca4f16598f0c862037fda6820894