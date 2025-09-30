# AI Portfolio Frontend

A modern React + TypeScript frontend for the AI Portfolio application.

## Features

- **Dark Theme UI** with Tailwind CSS
- **Responsive Design** for desktop and mobile
- **Authentication** via email/name registration
- **Portfolio Management** - view and add positions
- **Real-time Data** - positions list updates after adding new entries
- **Configurable Backend** - change API URL from the UI
- **Production Ready** - Docker support with nginx

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **React Router** for navigation
- **Zustand** for state management
- **Fetch API** for HTTP requests

## Development

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Create environment file:
```bash
cp .env.development .env
```

3. Start development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Environment Variables

- `VITE_API_BASE` - Backend API URL (default: http://localhost:8001)

## Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Docker

### Development
```bash
docker-compose -f infra/docker-compose.yml up frontend
```

### Production
```bash
docker-compose -f infra/docker-compose.yml up frontend
```

The frontend will be available at `http://localhost:8080`

## Usage

### 1. Configure Backend URL
- Use the "Backend URL" input in the top navigation
- Click "Apply" to save the URL
- Click "Reload" to refresh the current page

### 2. Register/Login
- Enter your email and name in the top navigation
- Click "Register" to create an account
- The app will remember your login status

### 3. Add Positions
- Navigate to the "Positions" page
- Fill in the form:
  - **Symbol**: Stock symbol (e.g., AAPL)
  - **Quantity**: Number of shares
  - **Purchase Price**: Price per share
- Click "Add Position"
- The positions list will refresh automatically

### 4. View Dashboard
- The dashboard shows portfolio overview with:
  - Total positions count
  - Total invested amount
  - Current market value
  - Profit/Loss with percentage

## API Endpoints

The frontend expects these backend endpoints:

- `GET /health` - Health check
- `POST /users/register?email=<email>&name=<name>` - User registration
- `POST /users/login?email=<email>` - User login
- `GET /positions` - Get user positions
- `POST /positions` - Add new position
- `DELETE /positions/:id` - Delete position

## Project Structure

```
frontend/
├── src/
│   ├── components/     # Reusable components
│   ├── pages/         # Page components
│   ├── store/         # State management
│   ├── lib/           # Utilities and API helpers
│   └── main.tsx       # App entry point
├── public/            # Static assets
├── Dockerfile         # Production Docker image
├── nginx.conf         # Nginx configuration
└── package.json       # Dependencies and scripts
```

## Development Notes

- The app uses localStorage to persist:
  - Backend URL configuration
  - User authentication state
- All API calls include proper error handling
- Form validation ensures data integrity
- The UI is fully responsive and works on mobile devices
