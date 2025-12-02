#!/bin/bash
# BDT Platform Setup Script
# One-command setup for development environment

set -e

echo "========================================="
echo "BDT Platform - Development Setup"
echo "========================================="
echo ""

# Check for required tools
check_requirements() {
    echo "Checking requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed. Please install Docker first."
        exit 1
    fi
    echo "✅ Docker found"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    echo "✅ Docker Compose found"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 is not installed. Please install Python 3.10+."
        exit 1
    fi
    echo "✅ Python found"
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        echo "⚠️  Node.js is not installed. Frontend development will require Node.js 18+."
    else
        echo "✅ Node.js found"
    fi
    
    echo ""
}

# Setup Python virtual environment
setup_python() {
    echo "Setting up Python environment..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo "✅ Virtual environment created"
    fi
    
    # Activate and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "✅ Python dependencies installed"
    echo ""
}

# Setup Node.js dependencies
setup_node() {
    echo "Setting up Node.js environment..."
    
    if command -v npm &> /dev/null; then
        cd frontend
        npm install
        cd ..
        echo "✅ Node dependencies installed"
    else
        echo "⚠️  Skipping Node setup (npm not found)"
    fi
    echo ""
}

# Setup environment configuration
setup_env() {
    echo "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        echo "✅ .env file created from template"
        echo ""
        echo "⚠️  IMPORTANT: Edit .env file with your configuration:"
        echo "   - OpenAI API key"
        echo "   - Microsoft 365 credentials (if using)"
        echo "   - Google Workspace credentials (if using)"
        echo "   - Database passwords"
    else
        echo "✅ .env file already exists"
    fi
    echo ""
}

# Initialize database
init_database() {
    echo "Initializing database..."
    
    # Start only PostgreSQL and Redis
    docker-compose up -d postgres redis
    
    # Wait for PostgreSQL to be ready
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
    
    # Run migrations
    if [ -f "scripts/migrate.py" ]; then
        source venv/bin/activate
        python scripts/migrate.py
        echo "✅ Database migrations completed"
    else
        echo "⚠️  Migration script not found, skipping"
    fi
    echo ""
}

# Start services
start_services() {
    echo "Starting all services..."
    
    # Use development docker-compose if it exists
    if [ -f "docker-compose.dev.yml" ]; then
        docker-compose -f docker-compose.dev.yml up -d
        echo "✅ Development services started"
    else
        docker-compose up -d
        echo "✅ Services started"
    fi
    
    echo ""
    echo "========================================="
    echo "✅ Setup Complete!"
    echo "========================================="
    echo ""
    echo "Services running at:"
    echo "  - Frontend: http://localhost:3000"
    echo "  - API: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - Redis: localhost:6379"
    echo ""
    echo "Next steps:"
    echo "  1. Edit .env file with your API keys"
    echo "  2. Access the frontend at http://localhost:3000"
    echo "  3. View API documentation at http://localhost:8000/docs"
    echo ""
    echo "Useful commands:"
    echo "  - View logs: docker-compose logs -f"
    echo "  - Stop services: docker-compose down"
    echo "  - Run tests: pytest"
    echo "  - Development mode: uvicorn backend.api.main:app --reload"
}

# Main execution
main() {
    check_requirements
    setup_env
    setup_python
    setup_node
    init_database
    start_services
}

# Run main function
main
