# Finch Frontend

Next.js frontend for the Finch portfolio chatbot.

## Quick Start

1. Install dependencies:
```bash
npm install
```

2. Run the development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

- `app/` - Next.js 14 app directory structure
  - `page.tsx` - Main chat page
  - `layout.tsx` - Root layout with metadata
  - `globals.css` - Global styles and Tailwind imports
- `components/` - React components
  - `ChatContainer.tsx` - Main chat logic and state management
  - `ChatMessage.tsx` - Individual message display
  - `ChatInput.tsx` - Message input with keyboard shortcuts
- `lib/` - Utilities and API client
  - `api.ts` - Axios-based API client

## Features

- Real-time chat interface
- Message history per session
- Typing indicators
- Error handling
- Responsive design
- Keyboard shortcuts (Enter to send, Shift+Enter for new line)

## Configuration

Create `.env.local` to customize the API URL:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Build for Production

```bash
npm run build
npm start
```

## Styling

Uses Tailwind CSS with custom configuration. Modify `tailwind.config.js` to customize colors and theme.

