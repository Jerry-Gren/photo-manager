# photo-manager

## How to launch

```shell
docker-compose up -d --build
```

## Example of environment file (.env)

Create a `.env` file as follows:

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
```

This must be done before you launch the project.