# Open WebUI Developer Guide

## Project Overview

Open WebUI is a comprehensive, self-hosted AI platform built with a **FastAPI backend** and **SvelteKit frontend**. It supports various LLM runners like Ollama and OpenAI-compatible APIs, with built-in RAG capabilities, making it a powerful AI deployment solution.

## Architecture Overview

### Technology Stack
- **Backend**: Python FastAPI with SQLAlchemy/Peewee ORM
- **Frontend**: SvelteKit with TypeScript and Tailwind CSS
- **Database**: SQLite (default), PostgreSQL, MySQL support
- **Real-time**: Socket.IO for WebSocket communication
- **Containerization**: Docker with multi-stage builds
- **Package Management**: 
  - Backend: Python pip/uv
  - Frontend: npm

### Project Structure
```
open-webui/
├── backend/                    # Python FastAPI backend
│   └── open_webui/
│       ├── main.py            # FastAPI application entry point
│       ├── config.py          # Configuration management
│       ├── routers/           # API route handlers
│       ├── models/            # Database models
│       ├── utils/             # Utility functions
│       ├── retrieval/         # RAG and document processing
│       └── socket/            # WebSocket handlers
├── src/                       # SvelteKit frontend
│   ├── lib/
│   │   ├── apis/             # API client functions
│   │   ├── components/       # Svelte components
│   │   ├── stores/           # Svelte stores (state management)
│   │   ├── utils/            # Frontend utilities
│   │   └── i18n/             # Internationalization
│   └── routes/               # SvelteKit routes
├── static/                   # Static assets
├── docs/                     # Documentation
└── kubernetes/               # K8s deployment configs
```

## Development Environment Setup

### Prerequisites
- **Python 3.11-3.12**
- **Node.js 18.13.0-22.x.x**
- **npm 6.0.0+**
- **Docker** (optional, for containerized development)

### Local Development Setup

1. **Clone and Setup**
```bash
git clone https://github.com/open-webui/open-webui.git
cd open-webui
```

2. **Backend Setup**
```bash
# Install Python dependencies
pip install -r backend/requirements.txt
# or using uv (recommended)
uv pip install -r backend/requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run backend development server
cd backend
python -m open_webui.main
# or
./dev.sh
```

3. **Frontend Setup**
```bash
# Install Node.js dependencies
npm install

# Run frontend development server
npm run dev
# or on specific port
npm run dev:5050
```

4. **Full Stack Development**
```bash
# Terminal 1: Backend
cd backend && ./dev.sh

# Terminal 2: Frontend  
npm run dev
```

## Backend Architecture Deep Dive

### Core Components

#### 1. Main Application (`backend/open_webui/main.py`)
- FastAPI application initialization
- Middleware configuration (CORS, compression, security)
- Route registration
- WebSocket setup
- Application lifecycle management

#### 2. Configuration System (`backend/open_webui/config.py`)
- **PersistentConfig**: Database-backed configuration with Redis caching
- Environment variable management
- OAuth provider configuration
- Dynamic configuration updates

#### 3. Database Models (`backend/open_webui/models/`)
Key models include:
- `users.py`: User management and authentication
- `chats.py`: Chat conversations and history
- `models.py`: AI model configurations
- `files.py`: File upload and management
- `knowledge.py`: RAG knowledge base
- `functions.py`: Custom function definitions
- `tools.py`: Tool integrations

#### 4. API Routers (`backend/open_webui/routers/`)
RESTful API endpoints organized by functionality:
- `auths.py`: Authentication and authorization
- `chats.py`: Chat management
- `models.py`: Model operations
- `files.py`: File operations
- `retrieval.py`: RAG and document processing
- `openai.py`: OpenAI API compatibility
- `ollama.py`: Ollama integration

#### 5. Utilities (`backend/open_webui/utils/`)
- `auth.py`: JWT token management, OAuth handling
- `chat.py`: Chat completion processing
- `embeddings.py`: Vector embedding generation
- `middleware.py`: Request/response processing
- `access_control.py`: Permission management

### Key Backend Patterns

#### Configuration Management
```python
# PersistentConfig pattern for database-backed settings
ENABLE_SIGNUP = PersistentConfig(
    "ENABLE_SIGNUP",
    "auth.signup.enable", 
    os.environ.get("ENABLE_SIGNUP", "True").lower() == "true"
)

# Usage in code
if ENABLE_SIGNUP.value:
    # Allow user registration
```

#### Database Operations
```python
# Using SQLAlchemy with context managers
from open_webui.internal.db import get_db

def get_user_by_id(user_id: str):
    with get_db() as db:
        return db.query(User).filter(User.id == user_id).first()
```

#### API Route Pattern
```python
from fastapi import APIRouter, Depends, HTTPException
from open_webui.utils.auth import get_verified_user

router = APIRouter()

@router.get("/api/endpoint")
async def endpoint(user=Depends(get_verified_user)):
    # Route implementation
    return {"status": "success"}
```

## Frontend Architecture Deep Dive

### Core Components

#### 1. SvelteKit App Structure
- **Routes**: File-based routing in `src/routes/`
- **Layouts**: Shared layouts for different route groups
- **Components**: Reusable UI components in `src/lib/components/`
- **Stores**: Global state management with Svelte stores

#### 2. State Management (`src/lib/stores/index.ts`)
Global application state using Svelte stores:
```typescript
export const user: Writable<SessionUser | undefined> = writable(undefined);
export const config: Writable<Config | undefined> = writable(undefined);
export const models: Writable<Model[]> = writable([]);
export const chats = writable(null);
export const settings: Writable<Settings> = writable({});
```

#### 3. API Client (`src/lib/apis/`)
Organized API client functions:
- `index.ts`: Core API functions
- `auths/`: Authentication APIs
- `chats/`: Chat management APIs
- `models/`: Model operations
- `files/`: File operations

#### 4. Component Architecture
```
src/lib/components/
├── chat/                 # Chat-related components
│   ├── MessageInput.svelte
│   ├── Messages/
│   └── SettingsModal.svelte
├── layout/              # Layout components
│   ├── Sidebar.svelte
│   └── Navbar.svelte
├── common/              # Reusable components
└── admin/               # Admin-specific components
```

### Key Frontend Patterns

#### API Integration
```typescript
// API client pattern
export const getChatList = async (token: string, page: number = 1) => {
    const res = await fetch(`${WEBUI_BASE_URL}/api/chats?page=${page}`, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    
    if (!res.ok) throw await res.json();
    return res.json();
};
```

#### Component Communication
```svelte
<!-- Parent component -->
<script>
    import { user, settings } from '$lib/stores';
    import ChildComponent from './ChildComponent.svelte';
    
    let componentData = {};
</script>

<ChildComponent bind:data={componentData} />

<!-- Child component -->
<script>
    export let data = {};
    
    // Access global stores
    $: if ($user) {
        // React to user changes
    }
</script>
```

#### Real-time Communication
```typescript
// WebSocket integration
const setupSocket = async () => {
    const socket = io(`${WEBUI_BASE_URL}`, {
        auth: { token: localStorage.token }
    });
    
    socket.on('chat-events', (event) => {
        // Handle real-time chat events
    });
};
```

## Key Development Areas

### 1. Authentication & Authorization

#### Backend Implementation
```python
# JWT token verification
from open_webui.utils.auth import get_verified_user

@router.get("/protected-endpoint")
async def protected_route(user=Depends(get_verified_user)):
    return {"user_id": user.id}
```

#### Frontend Implementation
```typescript
// Token management
const token = localStorage.getItem('token');
const user = await getSessionUser(token);
```

### 2. Chat System

#### Message Flow
1. **Frontend**: User input → `MessageInput.svelte`
2. **API**: POST `/api/chat/completions`
3. **Backend**: Process through chat completion handler
4. **WebSocket**: Real-time updates via Socket.IO
5. **Frontend**: Update chat UI reactively

#### Adding New Chat Features
```python
# Backend: Add new chat router endpoint
@router.post("/api/chat/custom-action")
async def custom_chat_action(
    request: CustomChatRequest,
    user=Depends(get_verified_user)
):
    # Implementation
    return {"result": "success"}
```

```typescript
// Frontend: Add API client function
export const customChatAction = async (token: string, data: any) => {
    const res = await fetch(`${WEBUI_BASE_URL}/api/chat/custom-action`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    return res.json();
};
```

### 3. Model Integration

#### Adding New Model Providers
1. **Backend**: Create new router in `routers/`
2. **Configuration**: Add provider settings to `config.py`
3. **Frontend**: Update model selection UI
4. **API Client**: Add provider-specific API functions

#### Example: Custom Model Provider
```python
# backend/open_webui/routers/custom_provider.py
from fastapi import APIRouter, Depends
from open_webui.utils.auth import get_verified_user

router = APIRouter()

@router.get("/api/custom-provider/models")
async def get_custom_models(user=Depends(get_verified_user)):
    # Fetch models from custom provider
    return {"models": []}
```

### 4. RAG (Retrieval Augmented Generation)

#### Document Processing Pipeline
1. **Upload**: File upload via `/api/files/`
2. **Processing**: Text extraction and chunking
3. **Embedding**: Vector embedding generation
4. **Storage**: Vector database storage (ChromaDB/Qdrant)
5. **Retrieval**: Similarity search during chat

#### Adding New Document Types
```python
# backend/open_webui/retrieval/loaders/
class CustomDocumentLoader:
    def load(self, file_path: str) -> List[Document]:
        # Custom document processing logic
        return documents
```

### 5. UI Components

#### Creating New Components
```svelte
<!-- src/lib/components/custom/NewComponent.svelte -->
<script lang="ts">
    import { getContext } from 'svelte';
    import { user, settings } from '$lib/stores';
    
    const i18n = getContext('i18n');
    
    export let prop1: string = '';
    export let prop2: number = 0;
    
    // Component logic
</script>

<div class="custom-component">
    <!-- Component template -->
    <h2>{$i18n.t('Component Title')}</h2>
    <p>{prop1}</p>
</div>

<style>
    .custom-component {
        /* Component styles */
    }
</style>
```

## Configuration & Environment

### Environment Variables
Key environment variables for development:

```bash
# Backend Configuration
WEBUI_AUTH=True
ENABLE_SIGNUP=True
ENABLE_OAUTH_SIGNUP=False
DEFAULT_USER_ROLE=pending

# Database
DATABASE_URL=sqlite:///data/webui.db

# External Services
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=your_openai_key
OPENAI_API_BASE_URL=https://api.openai.com/v1

# Features
ENABLE_RAG_HYBRID_SEARCH=True
ENABLE_WEB_SEARCH=False
ENABLE_IMAGE_GENERATION=False

# Development
ENV=dev
WEBUI_SECRET_KEY=your_secret_key
```

### Configuration System
The application uses a sophisticated configuration system:

1. **Environment Variables**: Base configuration
2. **Database Storage**: Persistent configuration via `PersistentConfig`
3. **Redis Caching**: Distributed configuration updates
4. **Runtime Updates**: Dynamic configuration changes

## Testing

### Backend Testing
```bash
# Run backend tests
cd backend
python -m pytest

# Run specific test file
python -m pytest tests/test_auth.py

# Run with coverage
python -m pytest --cov=open_webui
```

### Frontend Testing
```bash
# Run frontend tests
npm run test:frontend

# Run Cypress e2e tests
npm run cy:open
```

## Deployment

### Docker Development
```bash
# Build development image
docker build -t open-webui:dev .

# Run with docker-compose
docker-compose -f docker-compose.yaml up
```

### Production Deployment
```bash
# Build production image
docker build -t open-webui:latest .

# Deploy with environment variables
docker run -d \
  -p 3000:8080 \
  -e WEBUI_SECRET_KEY=your_secret_key \
  -e DATABASE_URL=postgresql://user:pass@db:5432/openwebui \
  -v open-webui:/app/backend/data \
  open-webui:latest
```

## Common Development Tasks

### Adding a New API Endpoint

1. **Backend Route**:
```python
# backend/open_webui/routers/custom.py
@router.post("/api/custom/action")
async def custom_action(
    request: CustomRequest,
    user=Depends(get_verified_user)
):
    # Implementation
    return {"success": True}
```

2. **Frontend API Client**:
```typescript
// src/lib/apis/custom.ts
export const customAction = async (token: string, data: any) => {
    const res = await fetch(`${WEBUI_BASE_URL}/api/custom/action`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    return res.json();
};
```

3. **Component Integration**:
```svelte
<script>
    import { customAction } from '$lib/apis/custom';
    import { user } from '$lib/stores';
    
    const handleAction = async () => {
        try {
            const result = await customAction($user.token, { data: 'example' });
            console.log('Success:', result);
        } catch (error) {
            console.error('Error:', error);
        }
    };
</script>

<button on:click={handleAction}>Custom Action</button>
```

### Adding New Configuration Options

1. **Backend Configuration**:
```python
# backend/open_webui/config.py
CUSTOM_FEATURE_ENABLED = PersistentConfig(
    "CUSTOM_FEATURE_ENABLED",
    "features.custom_feature",
    os.environ.get("CUSTOM_FEATURE_ENABLED", "False").lower() == "true"
)
```

2. **Frontend Settings**:
```svelte
<!-- Settings component -->
<script>
    import { settings } from '$lib/stores';
    
    let customFeatureEnabled = $settings.customFeature ?? false;
    
    const updateSetting = async () => {
        await updateUserSettings(localStorage.token, {
            customFeature: customFeatureEnabled
        });
    };
</script>

<label>
    <input 
        type="checkbox" 
        bind:checked={customFeatureEnabled}
        on:change={updateSetting}
    />
    Enable Custom Feature
</label>
```

### Internationalization (i18n)

1. **Add Translation Keys**:
```json
// src/lib/i18n/locales/en-US/translation.json
{
    "Custom Feature": "Custom Feature",
    "Enable custom functionality": "Enable custom functionality"
}
```

2. **Use in Components**:
```svelte
<script>
    import { getContext } from 'svelte';
    const i18n = getContext('i18n');
</script>

<h2>{$i18n.t('Custom Feature')}</h2>
<p>{$i18n.t('Enable custom functionality')}</p>
```

## Best Practices

### Code Organization
- **Backend**: Follow FastAPI patterns with dependency injection
- **Frontend**: Use Svelte stores for state management
- **Components**: Keep components small and focused
- **API**: Maintain consistent error handling and response formats

### Security
- Always use `get_verified_user` dependency for protected routes
- Validate and sanitize user inputs
- Use HTTPS in production
- Implement proper CORS policies

### Performance
- Use database indexes for frequently queried fields
- Implement pagination for large datasets
- Optimize bundle size with proper imports
- Use caching for expensive operations

### Error Handling
```python
# Backend error handling
try:
    result = await some_operation()
    return {"success": True, "data": result}
except Exception as e:
    log.error(f"Operation failed: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

```typescript
// Frontend error handling
try {
    const result = await apiCall();
    toast.success('Operation successful');
    return result;
} catch (error) {
    console.error('API Error:', error);
    toast.error(error.message || 'Operation failed');
    throw error;
}
```

## Debugging

### Backend Debugging
```python
# Add logging
import logging
log = logging.getLogger(__name__)

@router.get("/debug-endpoint")
async def debug_endpoint():
    log.debug("Debug information")
    log.info("Info message")
    log.error("Error message")
```

### Frontend Debugging
```typescript
// Browser console debugging
console.log('Debug data:', data);
console.error('Error occurred:', error);

// Svelte reactive debugging
$: console.log('Store updated:', $user);
```

### Development Tools
- **Backend**: Use FastAPI's automatic OpenAPI docs at `/docs`
- **Frontend**: Use browser dev tools and Svelte dev tools
- **Database**: Use database admin tools for data inspection
- **Network**: Monitor API calls in browser network tab

## Contributing Guidelines

1. **Fork and Branch**: Create feature branches from `main`
2. **Code Style**: Follow existing patterns and use linters
3. **Testing**: Add tests for new functionality
4. **Documentation**: Update relevant documentation
5. **Pull Requests**: Provide clear descriptions and test instructions

This guide provides a comprehensive overview of the Open WebUI architecture and development practices. For specific implementation details, refer to the existing codebase and follow the established patterns.