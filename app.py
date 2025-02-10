from flask import Flask, render_template, jsonify, request
import docker
import os
import socket
import tempfile
import shutil
import git
import subprocess

app = Flask(__name__)

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

# Initialize Docker client
try:
    if is_port_in_use(5000):
        print("Port 5000 is already in use. Please stop any other Flask applications using this port.")
    client = docker.from_env()
except docker.errors.DockerException as e:
    print(f"Failed to initialize Docker client: {e}")
    client = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/containers')
def get_containers():
    if not client:
        return jsonify({'status': 'error', 'message': 'Docker client not initialized'}), 500
    
    try:
        containers = client.containers.list(all=True)
        container_list = []
        for container in containers:
            container_list.append({
                'id': container.id[:12],
                'name': container.name,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else 'none'
            })
        return jsonify({'status': 'success', 'containers': container_list})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/container/<container_id>/start', methods=['POST'])
def start_container(container_id):
    try:
        container = client.containers.get(container_id)
        before_status = container.status
        container.start()
        container.reload()  # Refresh container data
        after_status = container.status
        
        response = {
            'status': 'success',
            'message': f'Container {container_id} started',
            'details': {
                'container_id': container_id,
                'container_name': container.name,
                'before_status': before_status,
                'after_status': after_status,
                'image': container.image.tags[0] if container.image.tags else 'none',
                'ports': container.attrs['NetworkSettings']['Ports'],
                'ip_address': container.attrs['NetworkSettings']['IPAddress']
            }
        }
        return jsonify(response)
    except Exception as e:
        error_message = str(e)
        if "bind: address already in use" in error_message:
            error_message = "Port 5000 is already in use. Please stop any other Flask applications using this port."
        return jsonify({'status': 'error', 'message': error_message}), 500

@app.route('/container/<container_id>/stop', methods=['POST'])
def stop_container(container_id):
    try:
        container = client.containers.get(container_id)
        container.stop()
        return jsonify({'status': 'success', 'message': f'Container {container_id} stopped'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/container/<container_id>/restart', methods=['POST'])
def restart_container(container_id):
    try:
        container = client.containers.get(container_id)
        container.restart()
        return jsonify({'status': 'success', 'message': f'Container {container_id} restarted'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/container/<container_id>/logs')
def get_container_logs(container_id):
    try:
        container = client.containers.get(container_id)
        logs = container.logs(tail=100).decode('utf-8')
        return jsonify({'status': 'success', 'logs': logs})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/containers/start-all', methods=['POST'])
def start_all_containers():
    try:
        containers = client.containers.list(all=True)
        for container in containers:
            if container.status != 'running':
                container.start()
        return jsonify({'status': 'success', 'message': 'All containers started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/containers/stop-all', methods=['POST'])
def stop_all_containers():
    try:
        containers = client.containers.list(all=True)
        for container in containers:
            if container.status == 'running':
                container.stop()
        return jsonify({'status': 'success', 'message': 'All containers stopped'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/container/<container_id>/health', methods=['GET'])
def container_health(container_id):
    try:
        container = client.containers.get(container_id)
        container.reload()  # Refresh container data
        status = container.status
        health = container.attrs.get('State', {}).get('Health', {}).get('Status', 'N/A')
        
        return jsonify({
            'status': 'success',
            'container_id': container_id,
            'container_status': status,
            'health_status': health
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/upload-and-build', methods=['POST'])
def upload_and_build():
    try:
        container_name = request.form.get('containerName')
        if not container_name:
            return jsonify({'status': 'error', 'message': 'Container name is required'}), 400

        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded files
            for file in request.files.getlist('files'):
                file_path = os.path.join(temp_dir, file.filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)

            # Build and run the container
            client = docker.from_env()
            project = client.compose.project_from_directory(temp_dir)
            
            # Build the containers
            project.build(stream=True)
            
            # Run the containers
            project.up(detach=True, stream=True)

            return jsonify({'status': 'success', 'message': 'Container built and started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/build-from-repo', methods=['POST'])
def build_from_repo():
    try:
        data = request.get_json()
        repo_url = data.get('repoUrl')
        if not repo_url:
            return jsonify({'status': 'error', 'message': 'Repository URL is required'}), 400

        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Check if it's a private repository
                if 'github.com' in repo_url:
                    # Extract token from request
                    token = data.get('githubToken')
                    if token:
                        # Modify URL to include token for authentication
                        repo_url = repo_url.replace('https://', f'https://{token}@')
                
                # Clone the repository
                git.Repo.clone_from(repo_url, temp_dir)
                
                # Run docker-compose build and up
                try:
                    # Build the containers
                    subprocess.run(
                        ['docker-compose', 'build'],
                        cwd=temp_dir,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    # Run the containers
                    subprocess.run(
                        ['docker-compose', 'up', '-d'],
                        cwd=temp_dir,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    return jsonify({'status': 'success', 'message': 'Container built and started'})
                except subprocess.CalledProcessError as e:
                    return jsonify({
                        'status': 'error',
                        'message': f'Docker Compose failed: {e.stderr.decode("utf-8")}'
                    }), 500
            except git.exc.GitCommandError as e:
                return jsonify({'status': 'error', 'message': f'Failed to clone repository: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/container/<container_id>/delete', methods=['DELETE'])
def delete_container(container_id):
    try:
        container = client.containers.get(container_id)
        container.stop()
        container.remove()
        return jsonify({'status': 'success', 'message': f'Container {container_id} deleted'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0')
    except OSError as e:
        if "Address already in use" in str(e):
            print("Port 5000 is already in use. Please stop any other Flask applications using this port.")
        else:
            raise e
