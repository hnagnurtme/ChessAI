# Chess Bot API

A chess engine application with three different bot difficulty levels and a React-based frontend interface.

## Project Structure

- **Backend**: FastAPI-based REST API with three chess engines
- **Frontend**: React + Vite with chess.js and react-chessboard

## Features

### Chess Engines

1. **Bot V1**: Simple alpha-beta pruning engine
2. **Bot V2**: Enhanced with iterative deepening, transposition tables, and late move reduction
3. **Bot VIP**: Advanced engine with static exchange evaluation, aspiration windows, and pawn hash tables

## Quick Start with Docker

### Run Everything

```bash
docker-compose up -d
```

Services will be available at:
- Backend API: http://localhost:8000/docs
- Frontend: http://localhost:5000

### Stop Services

```bash
docker-compose down
```

### View Logs

```bash
docker-compose logs -f
```

## Manual Setup

### Backend

1. Navigate to Backend folder:
```bash
cd Backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API documentation: http://localhost:8000/docs

### Frontend

1. Navigate to Frontend folder:
```bash
cd Frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run development server:
```bash
npm run dev
```

Application: http://localhost:5173

4. Build for production:
```bash
npm run build
```

## API Endpoints

### Get Best Move

```
POST /api/v1/best-move
POST /api/v2/best-move
POST /api/vip/best-move
```

Request body:
```json
{
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "depth": 4
}
```

Response:
```json
{
  "move": "e2e4",
  "eval": 0.5
}
```

## Development

### Run Tests

Backend:
```bash
cd Backend
pytest
```

Frontend:
```bash
cd Frontend
npm run lint
```

## Technology Stack

### Backend
- FastAPI
- python-chess
- uvicorn
- numpy
- pydantic-settings

### Frontend
- React 19
- Vite
- chess.js
- react-chessboard
- axios

## Docker Images

- Backend: Python 3.11-slim based (approximately 150-200MB)
- Frontend: Multi-stage Nginx Alpine based (approximately 25-35MB)

