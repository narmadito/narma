# Narma

**Narma** is a backend social network project built with Django + REST Framework.  
It is designed for practicing and mastering modern web development concepts such as scalable architecture, API design, background task processing, and containerized deployment.  

---

## 📚 API Overview (Summary)

The **Narma** backend provides a full-featured social network API including:

- **User authentication and JWT token management**  
- **User blocking and unblocking** functionality  
- **Direct messaging** between users with message read, delete, and list capabilities  
- **Email change workflow** with confirmation steps  
- **Friend request management**: sending, accepting, and declining requests  
- **Friend list management** including unfriending  
- **Group chat features**: creating groups, messaging, managing members, and ownership transfer  
- **Password reset and confirmation** processes  
- **Post and comment system** with favorites, reactions, and comments  
- **User profiles** with username changes, profile picture updates, and account deletion  
- **User registration** with email confirmation codes  
- **Pagination** support for scalable data access  
- **Throttling** to prevent abuse and rate-limit excessive API usage  

All these features are accessible via RESTful API endpoints documented with Swagger UI.

## ⚙️ Tools & Technologies Used

This project is powered by:

- **Django** – Backend web framework

- **Django REST Framework** – For building APIs

- **Swagger** – API documentation

- **Docker** – Containerization for consistent deployment

- **Redis** – Used with Celery for background task management

- **Celery**  – For sending emails and other async tasks

- **PostgreSQL** – Database

- **Nginx** – Acts as a reverse proxy, serves static files, and helps improve performance

## 🚀 Installation

Follow these steps to run the project on your local machine using Docker.

### ✅ Prerequisites

Make sure you have the following tools installed:

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)


## 🛠️ Setup Steps
#### 1. Clone the Repository
```bash
git clone https://github.com/narmadito/narma.git
cd narma
```
#### 2. Create your .env file
```bash
cp .env.example .env
```
 Fill in your .env file following the template provided in .env.example from the repository. This includes database credentials, email settings, and secret keys.

#### 3. Build and start the Docker containers
```bash
docker-compose up --build
```
This command will build and start all necessary containers. Wait for all services to initialize completely.

#### 4. Verify Installation
Check that all containers are running properly:
```bash
docker ps
```

You should see **5 containers** running:
- **web** – Django application (backend and API logic)
- **db** – PostgreSQL database for data storage
- **redis** – Redis cache and message broker for Celery
- **celery** – Background task worker for asynchronous processing
- **nginx** – Reverse proxy that serves static files and improves performance

## 5. Configure the Project
Access the web container and set up the database:
```bash
docker exec -it <web-container-id> bash
python manage.py migrate
python manage.py test
```
**Pro tip**: Use docker ps to find your exact web container ID, or use docker exec -it narma-web-1 bash if that's your container name.

When you run tests, make sure to place a default profile image inside the `media/profile/` directory.
This image will be automatically used for users who haven't uploaded a custom profile picture.

### ✅ 6. Start Exploring!

Your **Narma** backend is now up and running! You can access the following:

- 🔍 **API Documentation (Swagger UI)**: [http://localhost/swagger/](http://localhost/swagger/)
- 🔐 **Admin Panel**: [http://localhost/admin/](http://localhost/admin/)
- 🌐 **API Base URL**: [http://localhost/](http://localhost/)


# 🔧 Development Tips
- **Create super user** – `python manage.py createsuperuser`
- **View logs for debugging** – `docker-compose logs -f web`
- **View Nginx logs** – `docker-compose logs -f nginx`
- **Restart web after code changes** – `docker-compose restart web`
- **Run tests** – `python manage.py test`
- **Access Django shell** - `python manage.py shell`
- **Rebuild all services if needed** - `docker-compose up --build`
