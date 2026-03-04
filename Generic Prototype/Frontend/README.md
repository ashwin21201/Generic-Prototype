# Architecture Discovery Agent - Frontend

Modern React + Vite frontend for the Architecture Discovery Agent.

## Features

- 🎨 Modern, responsive chat interface
- 🤖 Real-time AI conversation with Claude
- 📊 Question progress tracking (max 12 questions)
- 📋 JSON output with copy-to-clipboard
- ⚡ Fast development with Vite HMR

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The app will run on `http://localhost:5173` and proxy API requests to `http://localhost:8000`.

## Backend Requirements

Make sure the FastAPI backend is running on `http://localhost:8000` with:
- `GET /api/health` - Health check endpoint
- `POST /api/chat` - Chat endpoint accepting `{ messages: [...] }`

## Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.
