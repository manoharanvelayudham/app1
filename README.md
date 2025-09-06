# Corporate Wellness Platform API

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive API for managing corporate wellness programs, including user management, program enrollment, participant responses, and AI-powered insights.

## Key Features

- **User Management**: Role-based access control (Admin, Coach, Participant)
- **Program Management**: Create and manage wellness programs
- **Response Collection**: Secure collection of participant responses
- **AI Processing**: Automated analysis of responses using OpenAI
- **Audit Logging**: Comprehensive tracking of all system actions
- **Auto-save**: Draft management with version history

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 13+
- Redis (for background processing)

### Installation
```bash
# Clone repository
git clone https://github.com/your-org/corporate-wellness-platform.git
cd corporate-wellness-platform/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\\venv\\Scripts\\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration
Create `.env` file:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/wellness_db

# Security
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Processing
OPENAI_API_KEY=your-openai-api-key
```

### Database Setup
```bash
alembic upgrade head
python -m app.database.init_db
```

### Running the Application
```bash
uvicorn app.main:app --reload
```

## API Documentation

### Base URL
`http://localhost:8000/api/v1`

### Authentication
| Endpoint          | Method | Description          |
|-------------------|--------|----------------------|
| `/token`          | POST   | Get access token     |
| `/token/refresh`  | POST   | Refresh access token |
| `/register`       | POST   | Register new user    |

### Example: User Login
```bash
curl -X POST "http://localhost:8000/api/v1/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=yourpassword"
```

### Response Management
| Endpoint                     | Method | Description                          |
|------------------------------|--------|--------------------------------------|
| `/responses/{id}/autosave`   | POST   | Auto-save draft response             |
| `/responses/{id}/status`     | POST   | Update response status               |
| `/responses/{id}/process-ai` | POST   | Trigger AI processing                |
| `/responses/batch-ai-processing` | POST | Batch process responses              |

## Project Structure

```
backend/
├── app/
│   ├── routers/        # API endpoints
│   │   ├── responses.py # Response management
│   │   ├── users.py     # User management
│   │   └── ...
│   ├── services/       # Business logic
│   │   ├── ai_pipeline.py # AI processing
│   │   ├── audit_service.py # Audit logging
│   │   └── ...
│   ├── models.py       # Database models
│   ├── schemas/        # Pydantic schemas
│   └── main.py         # Application entry point
├── alembic/            # Database migrations
├── requirements.txt    # Dependencies
└── .env                # Environment configuration
```

## Development

### Running Tests
```bash
pytest tests/
pytest --cov=app --cov-report=term-missing
```

### Code Quality
```bash
flake8 app  # Linting
black app   # Code formatting
mypy app    # Type checking
```

### Key Components
1. **AI Processing Pipeline** (`app/services/ai_pipeline.py`)
   - Text standardization
   - Content analysis
   - Multi-format support (text, audio, images)

2. **Audit Service** (`app/services/audit_service.py`)
   - Action tracking
   - Change history
   - Security compliance

## Deployment

### Production Setup
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

### Docker Deployment
```bash
docker build -t wellness-api .
docker run -d --name wellness-api -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e SECRET_KEY=your-secret-key \
  wellness-api
```

### Docker Compose
```yaml
version: '3.8'
services:
  db:
    image: postgres:13
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: wellness_db
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/wellness_db
      - SECRET_KEY=your-secret-key
    depends_on:
      - db

volumes:
  postgres_data:
```

## Contributing
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a pull request

## License
MIT License - see [LICENSE](LICENSE) for details
