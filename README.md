# AI Recruitment Platform

A modern web application built with Next.js for AI-powered recruitment processes. This platform helps streamline the hiring process by leveraging artificial intelligence to process CV and JD PDFs, and then match candidates with job opportunities.

## Features

- 🔐 Secure authentication with Auth0
- 🎨 Modern UI with Tailwind CSS and Radix UI components
- 🌐 Responsive design for all devices
- 🔍 AI-powered candidate matching
- 📱 Mobile-friendly interface
- 🎯 Job posting and candidate management
- 🚀 FastAPI backend for robust API services

## Tech Stack

### Frontend

- **Framework:** Next.js 15
- **UI Components:** Radix UI
- **Styling:** Tailwind CSS
- **Authentication:** Auth0
- **Language:** TypeScript
- **State Management:** React Hooks
- **Package Manager:** pnpm

### Backend

- **Framework:** FastAPI
- **Language:** Python
- **Package Manager:** Poetry
- **API Documentation:** OpenAPI/Swagger

## Prerequisites

- Node.js (v18 or higher)
- Python 3.8 or higher
- pnpm package manager
- Poetry package manager
- Auth0 account and credentials

## Getting Started

1. Clone the repository:

    ```bash
    git clone [repository-url]
    cd ai-recruitment
    ```

2. Install frontend dependencies:

    ```bash
    pnpm install
    ```

3. Install backend dependencies:

    ```bash
    cd backend
    poetry install
    cd ..
    ```

4. Set up environment variables:
   - Copy `.env.example` to `.env.local` in the root directory
   - Fill in your Auth0 credentials and other required environment variables

5. Start the development servers:

    For frontend (in root directory):

    ```bash
    pnpm dev
    ```

    For backend (in backend directory):

    ```bash
    cd backend
    poetry run uvicorn main:app --reload
    ```

    The frontend will be available at [http://localhost:3000](http://localhost:3000) and the backend API at [http://    localhost:8000](http://localhost:8000).

## Development

### Frontend Commands

- `pnpm dev` - Start the development server with Turbopack
- `pnpm build` - Build the application for production
- `pnpm start` - Start the production server
- `pnpm lint` - Run ESLint for code linting

### Backend Commands

- `cd backend && poetry run uvicorn main:app --reload` - Start the development server
- `cd backend && poetry run pytest` - Run backend tests
- `cd backend && poetry run black .` - Format Python code
- `cd backend && poetry run isort .` - Sort Python imports

## License

This project is licensed under the terms specified in the LICENSE file.

## Author

Created by Ali Mahouk.
