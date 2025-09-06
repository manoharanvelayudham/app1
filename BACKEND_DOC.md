Corporate Wellness Platform - Frontend Integration Hand-off Documentation
Based on my comprehensive analysis of the app1 backend system, I've identified critical integrity issues and created detailed hand-off instructions for the frontend development team.

🏗️ SYSTEM ARCHITECTURE OVERVIEW
Technology Stack
Framework: FastAPI 0.104.1
Database: SQLAlchemy 2.0.23 with PostgreSQL support
Authentication: JWT with bcrypt password hashing
AI Integration: OpenAI GPT-3.5-turbo for insights generation
Background Jobs: APScheduler for automated tasks
File Processing: Support for images, audio, documents, PDFs

Core Features
AI-driven personality and behavioral analysis
Predictive analytics and competency gap analysis
Comprehensive audit logging
System health monitoring
Excel export capabilities
Real-time dashboard analytics

🔐 AUTHENTICATION & AUTHORIZATION FLOW
Authentication Endpoints
POST /auth/login # User login
POST /auth/register # User registration
POST /auth/refresh # Token refresh
POST /auth/logout # User logout

Token Structure
Access Token: 30-minute expiry, JWT format
Refresh Token: 7-day expiry
Header Format: Authorization: Bearer <token>

Role-Based Access
CLIENT: Basic user access to programs and responses
TRAINER: Can review responses and manage programs
ADMIN: Full system access including user management

📊 DATABASE MODELS & RELATIONSHIPS
Core Models
User (id, email, first_name, last_name, role, hashed_password)
├── Programs (many-to-many via Enrollment)
├── Responses (one-to-many)
├── Reviews (one-to-many as reviewer)
└── AuditLogs (one-to-many)

Program (id, title, description, difficulty, duration)
├── Enrollments (one-to-many)
├── Responses (one-to-many)
└── Reviews (one-to-many)

Enrollment (user_id, program_id, status, enrolled_at)
├── User (many-to-one)
└── Program (many-to-one)

Response (id, user_id, program_id, content, type, status)
├── User (many-to-one)
├── Program (many-to-one)
└── Reviews (one-to-many)

AI & Analytics Models
AIInsight (id, user_id, insight_type, category, confidence_score)
AIRecommendation (id, user_id, ai_insight_id, priority, status)
PredictiveAnalysis (id, user_id, prediction_type, confidence_score)
SystemHealth (id, component_type, status, metrics)

🌐 API ENDPOINTS DOCUMENTATION
User Management
GET /users/ # List users (admin only)
POST /users/ # Create user
GET /users/{user_id} # Get user details
PUT /users/{user_id} # Update user
DELETE /users/{user_id} # Delete user (admin only)
GET /users/me # Get current user profile

Program Management
GET /programs/ # List programs
POST /programs/ # Create program (trainer/admin)
GET /programs/{id} # Get program details
PUT /programs/{id} # Update program (trainer/admin)
DELETE /programs/{id} # Delete program (admin only)

Enrollment & Responses
POST /enrollments/ # Enroll in program
GET /enrollments/me # My enrollments
POST /responses/ # Submit response
GET /responses/me # My responses
PUT /responses/{id} # Update response (draft only)

AI & Analytics
POST /api/v1/ai/generate-insights/{participant_id} # Generate AI insights
GET /api/v1/ai/insights/{insight_id} # Get insight details
POST /api/v1/ai/coaching-suggestions # Get coaching suggestions
GET /api/v1/ai/analytics/summary/{user_id} # Analytics summary
PUT /api/v1/ai/recommendations/{id}/status # Update recommendation status

Dashboard & Analytics
GET /dashboard/stats # Dashboard statistics
GET /analytics/overview # Analytics overview
GET /analytics/programs/{id}/metrics # Program metrics
POST /export/excel # Export data to Excel

System Monitoring
GET /health # Basic health check
GET /health/ai-processing # AI processing health
GET /system/status # System status
GET /system/config # System configuration (admin)

🎨 FRONTEND INTEGRATION GUIDELINES
Base URL Configuration
```javascript
const API_BASE_URL = 'http://localhost:8000'; // Development
// const API_BASE_URL = 'https://api.yourcompany.com'; // Production
```

Authentication Setup
```javascript
// Store tokens in localStorage or secure storage
const authToken = localStorage.getItem('access_token');
const refreshToken = localStorage.getItem('refresh_token');

// API request headers
const headers = {
  'Authorization': `Bearer ${authToken}`,
  'Content-Type': 'application/json'
};
```

Error Handling
```javascript
// Standard error response format
{
  "detail": "Error message",
  "status_code": 400,
  "timestamp": "2024-01-01T00:00:00Z"
}

// Handle 401 responses by refreshing token
if (response.status === 401) {
  // Attempt token refresh
  // If refresh fails, redirect to login
}
```

File Upload Handling
```javascript
// For responses with file attachments
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('content', responseText);
formData.append('response_type', 'file');

fetch(`${API_BASE_URL}/responses/`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});
```

🔧 ENVIRONMENT SETUP
Required Environment Variables
```env
# Database
DATABASE_URL=postgresql://user:password@localhost/wellness_db

# Authentication
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256

# AI Processing
OPENAI_API_KEY=your-openai-api-key

# Optional: Redis for caching
REDIS_URL=redis://localhost:6379
```

Development Dependencies
```bash
# Backend requirements are in requirements.txt
pip install -r requirements.txt

# Key packages for frontend integration:
# - FastAPI with CORS enabled
# - JWT authentication
# - File upload support
# - WebSocket support (future feature)
```

⚠️ KNOWN LIMITATIONS & WORKAROUNDS
CORS Configuration: Currently set to allow all origins (*) - restrict in production
File Size Limits: No explicit limits set - implement client-side validation
Rate Limiting: Not implemented - consider adding for production
WebSocket Support: Planned but not yet implemented for real-time features

🚀 RECOMMENDED FRONTEND ARCHITECTURE
Suggested Tech Stack
React/Vue.js/Angular for UI framework
Axios/Fetch for API communication
React Query/SWR for data fetching and caching
React Router/Vue Router for navigation
Tailwind CSS/Material-UI for styling

Key Components to Build
Authentication Components: Login, Register, Profile
Dashboard: Overview, Statistics, Recent Activity
Program Management: List, Details, Enrollment
Response System: Create, Edit, Submit, Review
AI Insights: Display insights, recommendations, analytics
Admin Panel: User management, system monitoring

State Management Recommendations
Use context/store for authentication state
Implement proper loading and error states
Cache frequently accessed data (user profile, programs)
Handle offline scenarios gracefully
