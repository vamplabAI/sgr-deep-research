# SGR Deep Research - Docker Deployment

Запуск полного стека (backend + frontend) через Docker Compose.

## Быстрый старт

1. **Скопируйте `.env.example` в `.env`:**

   ```bash
   cp .env.example .env
   ```

2. **Отредактируйте `.env` при необходимости** (опционально)

3. **Запустите все сервисы:**

   ```bash
   docker-compose up -d --build
   ```

4. **Откройте в браузере:**

   - Frontend: http://localhost:5174
   - Backend API: http://localhost:8010
   - API Docs: http://localhost:8010/docs

## Управление

### Запуск

```bash
# Запуск всех сервисов
docker-compose up -d

# Запуск с пересборкой
docker-compose up -d --build

# Запуск только backend
docker-compose up -d sgr-backend

# Запуск только frontend
docker-compose up -d sgr-frontend
```

### Остановка

```bash
# Остановить все сервисы
docker-compose down

# Остановить и удалить volumes
docker-compose down -v
```

### Логи

```bash
# Все логи
docker-compose logs -f

# Логи backend
docker-compose logs -f sgr-backend

# Логи frontend
docker-compose logs -f sgr-frontend
```

### Перезапуск

```bash
# Перезапустить все
docker-compose restart

# Перезапустить только backend
docker-compose restart sgr-backend
```

## Конфигурация

### Переменные окружения (.env)

```bash
# Backend
BACKEND_PORT=8010              # Порт для backend API

# Frontend
FRONTEND_PORT=5174             # Порт для frontend
VITE_API_BASE_URL=http://localhost:8010  # URL backend API
VITE_APP_ENV=production        # Окружение (production/development)

# Transcription API (опционально)
VITE_TRANSCRIPTION_API_URL=https://speechcoreai.com/api
VITE_TRANSCRIPTION_API_TOKEN=your_token_here
```

### Структура сервисов

- **sgr-backend**: FastAPI backend на порту 8010

  - Healthcheck: проверяет `/health` каждые 30 секунд
  - Volumes: код, конфиги, логи, отчеты

- **sgr-frontend**: Nginx + Vue.js frontend на порту 5174

  - Зависит от backend (запускается после healthcheck)
  - Статические файлы собираются при сборке образа

### Сеть

Оба сервиса находятся в одной Docker сети `sgr-network`, что позволяет им взаимодействовать по именам контейнеров.

## Troubleshooting

### Frontend не может подключиться к backend

Проверьте, что `VITE_API_BASE_URL` в `.env` указывает на правильный URL backend.

### Backend не стартует

Проверьте логи:

```bash
docker-compose logs sgr-backend
```

Убедитесь, что `config.yaml` и `logging_config.yaml` существуют в корне проекта.

### Порты заняты

Измените порты в `.env`:

```bash
BACKEND_PORT=8011
FRONTEND_PORT=5175
```

Затем перезапустите:

```bash
docker-compose down
docker-compose up -d
```
