# SGR Deep Research Frontend

Vue 3 + TypeScript + Vite frontend for SGR Deep Research.

## 🚀 Quick Start

### Prerequisites
- Node.js 20.19+ or 22.12+

### Setup

1. **Install Node.js 22** (macOS):
```sh
brew install node@22
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
```

2. **Install dependencies**:
```sh
npm install
```

3. **Configure environment**:
```sh
cp .env.example .env.local
```

Edit `.env.local` and set:
- `VITE_API_BASE_URL` - your backend URL (default: `http://localhost:8010`)
- `VITE_TRANSCRIPTION_API_URL` - transcription service URL
- `VITE_TRANSCRIPTION_API_TOKEN` - your transcription API token

### Run

**Development:**
```sh
npm run dev
```
Open http://localhost:5173

**Production build:**
```sh
npm run build
```

**Docker (Full Stack - Backend + Frontend):**
```sh
# Перейти в папку services
cd ../services

# Опционально: создать .env для настройки портов
cp .env.example .env

# Запустить всё (backend + frontend)
docker-compose up -d --build

# Открыть в браузере
# Frontend: http://localhost:5174
# Backend API: http://localhost:8010
```

Подробнее о Docker deployment см. в `../services/README.md`

## 🛠️ Tech Stack

Vue 3 • TypeScript • Vite • Pinia • Vue Router • Axios • Feature-Sliced Design (FSD)
