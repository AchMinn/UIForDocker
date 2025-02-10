# Docker Container Manager Web App

A simple web application built with Flask that allows you to manage Docker containers through a web interface. This application provides a user-friendly way to monitor and control Docker containers running on your system.

## Features

- List all Docker containers with their status
- Start and stop containers
- View container logs
- Real-time container status updates
- Clean and intuitive web interface

## Prerequisites

- Python 3.6+
- Docker installed and running on your system
- Docker SDK for Python

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd docker-container-manager
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3.If you need an environment variable, you can use the following command:
```bash
python -m venv venv
source venv/bin/activate
```

## Configuration

Make sure Docker daemon is running on your system before starting the application.

## Running the Application

1. Start the Flask application:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

## API Endpoints

The application provides the following REST API endpoints:

- `GET /containers` - List all containers
- `POST /container/<container_id>/start` - Start a specific container
- `POST /container/<container_id>/stop` - Stop a specific container
- `GET /container/<container_id>/logs` - Get logs for a specific container

## Security Considerations

This application should be used in a secure environment as it provides direct access to Docker containers. Consider implementing authentication and authorization before deploying in a production environment.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 