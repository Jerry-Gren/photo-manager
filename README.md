# photo-manager

A modern, AI-powered B/S image management platform featuring RAG (Retrieval-Augmented Generation) search, automatic tagging, and non-destructive editing.

## Prerequisites

### Docker & Docker Compose:

- Windows/macOS: [Docker Desktop](https://www.docker.com/products/docker-desktop/) is recommended.

- Linux: [Docker Engine](https://docs.docker.com/engine/install/) and [Docker Compose Plugin](https://docs.docker.com/compose/install/linux/).

## Installation & Launch

### 1. Configure Environment Variables

Create a `.env` file in the root directory. You can copy the template below.

```
# Database Configuration
# This DB_HOST matches the service name in docker-compose.yml
DB_HOST=db
DB_USER=root
# Use 'MYSQL_USER' and 'MYSQL_PASSWORD' for the 'db' service
MYSQL_DATABASE=photodb
MYSQL_ROOT_PASSWORD=<password>

# JWT Configuration
# Generate a strong secret key, e.g., using: openssl rand -hex 32
JWT_SECRET=...
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# SQLAlchemy Database URL
# Format: "mysql+pymysql://USER:PASSWORD@HOST/DB_NAME"
DATABASE_URL=mysql+pymysql://root:<password>@db/photodb

# ChromaDB Config
CHROMA_DB_HOST=vectordb
CHROMA_DB_PORT=8000
CHROMA_COLLECTION_NAME=image_gallery

# LLM Config
LLM_API_KEY=sk-xxx
LLM_API_BASE=...
LLM_MODEL=gpt-4o

# Hugging Face Mirror
HF_ENDPOINT=https://hf-mirror.com
```

**Important**: You must provide a valid LLM_API_KEY for AI features (Auto-tagging & Chat Search) to work.

### 2. Start the Application

Run the following command to build and start all services:

```shell
docker-compose up -d --build
```

### 3. Access the System

Once the containers are running:

- Web Interface: Open http://localhost in your browser.

- First Run: The database will be initialized automatically. Please register a new user account on the login page to start.

## Production Deployment Notes

This project is configured for Development/Demonstration purposes by default (HTTP on port 80). If you plan to deploy this in a production environment, you MUST take the following security measures:

### 1. Enable HTTPS (SSL) & Redirection

- Obtain an SSL certificate.

- Update `nginx.conf` to listen on port 443 and configure SSL paths.

- Configure Nginx to redirect all traffic from port 80 to port 443 to enforce secure connections.

- Update `docker-compose.yml` to expose port 443.

### 2. Secure Cookies

- In `app/routers/auth.py`, find the `login` endpoint.

- Change `secure=False` to `secure=True` when setting the `refresh_token` cookie. This ensures the cookie is never sent over unencrypted HTTP connections.

### 3. Strong Secrets

- Ensure `JWT_SECRET` and `MYSQL_ROOT_PASSWORD` in your `.env` file are long, random, and complex strings.

## Notes

**AI Processing Delay**: After uploading an image, please wait a few seconds for the background Celery worker to generate tags and vector embeddings.
