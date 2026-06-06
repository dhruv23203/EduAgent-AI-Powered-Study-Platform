# EduAgent: AI-Powered Study Platform

An intelligent, AI-powered educational platform designed to enhance learning experiences through personalized study recommendations, adaptive quizzes, career guidance, and real-time progress tracking. EduAgent leverages cutting-edge AI agents to provide a comprehensive learning ecosystem.

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Backend Setup](#backend-setup)
- [Frontend Setup](#frontend-setup)
- [Development](#development)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

## ✨ Features

### Core Learning Features
- **📚 Smart Study Plans**: AI-generated personalized study plans based on learning goals and pace
- **🤖 AI Chat Agent**: Intelligent conversational AI tutor for real-time learning assistance
- **📝 Adaptive Quizzes**: Dynamic quiz generation with AI-powered question adaptation
- **📊 Progress Tracking**: Real-time dashboard showing learning progress and performance metrics
- **🎯 Career Guidance**: AI-driven career path recommendations based on skills and interests
- **🔄 Revision System**: Spaced repetition and intelligent revision scheduling
- **🔐 User Authentication**: Secure login and profile management system

### Platform Features
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices
- **Real-time Updates**: Live progress updates and notifications
- **Persistent Storage**: SQLite database for reliable data persistence
- **Scalable Architecture**: Modular design for easy feature additions

## 🛠️ Tech Stack

### Backend
- **Framework**: Python FastAPI
- **Database**: SQLite (expandable to PostgreSQL/MongoDB)
- **Agent Framework**: LangChain / Custom AI Agents
- **API Style**: RESTful with WebSocket support for real-time features
- **Authentication**: JWT-based token authentication

### Frontend
- **Framework**: Next.js (React)
- **Styling**: Tailwind CSS / Material-UI
- **State Management**: Redux / Zustand
- **Type Safety**: TypeScript
- **Real-time Communication**: WebSocket for live updates

## 📁 Project Structure

```
eduagent/
├── backend/                           # Backend server code
│   ├── agents/                        # AI agent implementations
│   │   ├── study_agent.py            # Study plan generation agent
│   │   ├── tutor_agent.py            # Conversational tutoring agent
│   │   └── career_agent.py           # Career guidance agent
│   ├── db/                           # Database models and migrations
│   │   ├── models.py                 # SQLAlchemy/ORM models
│   │   ├── database.py               # Database connection setup
│   │   └── migrations/               # Database migration scripts
│   ├── models/                       # Data models and schemas
│   │   ├── user.py                   # User model
│   │   ├── study_plan.py             # Study plan model
│   │   ├── quiz.py                   # Quiz and question models
│   │   └── progress.py               # Progress tracking model
│   ├── routers/                      # API route handlers
│   │   ├── auth.py                   # Authentication endpoints
│   │   ├── user.py                   # User management endpoints
│   │   ├── study.py                  # Study plan endpoints
│   │   ├── quiz.py                   # Quiz endpoints
│   │   ├── progress.py               # Progress tracking endpoints
│   │   ├── chat.py                   # Chat/tutoring endpoints
│   │   └── career.py                 # Career guidance endpoints
│   ├── memory/                       # Memory management for agents
│   │   ├── user_memory.py            # User interaction memory
│   │   └── agent_memory.py           # Agent conversation history
│   ├── utils/                        # Utility functions
│   │   ├── auth_utils.py             # Authentication utilities
│   │   ├── ai_utils.py               # AI/LLM utilities
│   │   └── validation.py             # Data validation utilities
│   ├── main.py                       # Application entry point
│   ├── config.py                     # Configuration settings
│   └── requirements.txt              # Python dependencies
│
├── frontend/                          # Frontend application
│   ├── app/                          # Next.js app router directory
│   │   ├── login/                    # Authentication pages
│   │   │   ├── page.tsx
│   │   │   └── layout.tsx
│   │   ├── setup/                    # Initial setup/onboarding
│   │   │   ├── page.tsx
│   │   │   └── layout.tsx
│   │   ├── dashboard/                # Main dashboard
│   │   │   ├── page.tsx
│   │   │   └── layout.tsx
│   │   ├── plans/                    # Study plans
│   │   │   ├── page.tsx
│   │   │   ├── [id]/
│   │   │   └── layout.tsx
│   │   ├── chat/                     # AI chat interface
│   │   │   ├── page.tsx
│   │   │   └── layout.tsx
│   │   ├── quiz/                     # Quiz interface
│   │   │   ├── page.tsx
│   │   │   └── layout.tsx
│   │   ├── progress/                 # Progress tracking
│   │   │   ├── page.tsx
│   │   │   └── layout.tsx
│   │   ├── revision/                 # Revision system
│   │   │   ├── page.tsx
│   │   │   └── layout.tsx
│   │   ├── career/                   # Career guidance
│   │   │   ├── page.tsx
│   │   │   └── layout.tsx
│   │   ├── layout.tsx                # Root layout
│   │   └── page.tsx                  # Root page
│   ├── components/                   # Reusable React components
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   ├── StudyPlanCard.tsx
│   │   ├── QuizCard.tsx
│   │   ├── ProgressChart.tsx
│   │   ├── ChatWindow.tsx
│   │   └── ...
│   ├── lib/                          # Utility functions and hooks
│   │   ├── api.ts                    # API client
│   │   ├── hooks/                    # Custom React hooks
│   │   ├── auth.ts                   # Authentication logic
│   │   └── utils.ts                  # Helper functions
│   ├── public/                       # Static assets
│   ├── package.json                  # NPM dependencies
│   ├── tailwind.config.js            # Tailwind CSS configuration
│   ├── tsconfig.json                 # TypeScript configuration
│   └── .env.local                    # Local environment variables
│
├── .gitignore                        # Git ignore rules
├── .env.example                      # Example environment variables
├── docker-compose.yml                # Docker setup (optional)
└── README.md                         # This file
```

## 🚀 Installation

### Prerequisites
- Python 3.9+ (for backend)
- Node.js 16+ (for frontend)
- npm or yarn package manager
- SQLite 3 (usually pre-installed)

### Clone the Repository

```bash
git clone https://github.com/dhruv23203/EduAgent-AI-Powered-Study-Platform.git
cd EduAgent-AI-Powered-Study-Platform
```

## 🔧 Backend Setup

### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your configuration:
# - Database URL
# - API keys (OpenAI, etc.)
# - Secret keys
# - Server port
```

### 4. Database Setup

```bash
python -m alembic upgrade head  # Apply migrations (if using Alembic)
# or
python db/init_db.py            # Initialize database
```

### 5. Run Backend Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at `http://localhost:8000`

## 🎨 Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
# or
yarn install
```

### 2. Environment Configuration

```bash
cp .env.example .env.local
# Edit .env.local with:
# - NEXT_PUBLIC_API_URL=http://localhost:8000
# - Other API keys and configuration
```

### 3. Run Development Server

```bash
npm run dev
# or
yarn dev
```

Frontend will be available at `http://localhost:3000`

## 💻 Development

### Running Both Services

Create a terminal session at the project root:

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

### API Documentation

Once the backend is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key API Endpoints

#### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout

#### Study Plans
- `GET /api/study-plans` - Get all user study plans
- `POST /api/study-plans` - Create new study plan
- `GET /api/study-plans/{id}` - Get specific study plan
- `PUT /api/study-plans/{id}` - Update study plan

#### Quiz
- `GET /api/quizzes` - Get all quizzes
- `POST /api/quizzes` - Create new quiz
- `GET /api/quizzes/{id}` - Get quiz details
- `POST /api/quizzes/{id}/submit` - Submit quiz answers

#### Chat/Tutoring
- `WebSocket /ws/chat/{user_id}` - Real-time chat with AI tutor
- `POST /api/chat/history` - Get chat history

#### Progress
- `GET /api/progress` - Get user progress overview
- `GET /api/progress/detailed` - Get detailed progress analytics

#### Career Guidance
- `GET /api/career/recommendations` - Get career recommendations
- `POST /api/career/assessment` - Start career assessment

## 📝 Features Breakdown

### AI Agents

1. **Study Agent** (`backend/agents/study_agent.py`)
   - Generates personalized study plans
   - Adapts difficulty based on performance
   - Recommends topics based on weak areas

2. **Tutor Agent** (`backend/agents/tutor_agent.py`)
   - Provides real-time tutoring assistance
   - Explains complex concepts
   - Answers student questions

3. **Career Agent** (`backend/agents/career_agent.py`)
   - Recommends career paths
   - Suggests skill development
   - Provides industry insights

### Database Models

- **User**: User profiles, credentials, preferences
- **StudyPlan**: Learning goals, timeline, topics
- **Quiz**: Questions, answers, scoring
- **Progress**: User performance metrics, completion status
- **ChatHistory**: Conversation logs with AI agents

## 🔒 Security

- JWT-based authentication
- Password hashing with bcrypt
- CORS configuration for cross-origin requests
- Environment variable management for sensitive data
- Input validation and sanitization

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm run test
```

## 📦 Deployment

### Docker Deployment

```bash
docker-compose up -d
```

### Cloud Deployment

- Backend: Deploy to AWS EC2, Heroku, or DigitalOcean
- Frontend: Deploy to Vercel, Netlify, or AWS CloudFront
- Database: Consider managed databases (AWS RDS, MongoDB Atlas)

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Coding Standards
- Follow PEP 8 for Python code
- Use TypeScript for frontend code
- Write meaningful commit messages
- Add tests for new features
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Authors

- **Dhruv Malhan** - Initial Development

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- Next.js and React for the frontend framework
- LangChain for AI agent capabilities
- The open-source community for amazing tools and libraries

## 📞 Support

For support, email support@eduagent.com or open an issue on GitHub.

## 🗺️ Roadmap

- [ ] Mobile app (iOS/Android)
- [ ] Advanced analytics dashboard
- [ ] Integration with popular LMS platforms
- [ ] Offline mode support
- [ ] Multi-language support
- [ ] Advanced AI models integration
- [ ] Gamification features
- [ ] Social learning features

---

**Last Updated**: June 2026
