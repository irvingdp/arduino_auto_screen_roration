import os
import json
import time
import threading
import subprocess
import serial
import serial.tools.list_ports
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'screen_rotator_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
serial_connection = None
serial_thread = None
is_running = False
last_processed_degree = None
available_ports = {}
available_displays = {}
first_origin_values = {}  # Store the first Origin value for each display

def get_serial_ports():
    """Get list of available serial ports"""
    ports = serial.tools.list_ports.comports()
    port_list = []
    for p in ports:
        port_info = {
            'device': p.device,
            'description': p.description
        }
        port_list.append(port_info)
    return port_list

def get_displays():
    """Use displayplacer to get display list"""
    global first_origin_values
    try:
        print("Executing displayplacer list command...")
        result = subprocess.run(['displayplacer', 'list'], capture_output=True, text=True, check=True)
        output = result.stdout
        print(f"displayplacer output:\n{output}")
        
        displays = []
        current_display = {}
        
        for line in output.splitlines():
            line = line.strip()
            print(f"Processing line: {line}")
            
            # Parse display ID
            if "Persistent screen id:" in line:
                current_display["id"] = line.split(":")[-1].strip()
                print(f"Found Screen ID: {current_display['id']}")
            
            # Parse display type
            elif "Type:" in line:
                current_display["type"] = line.split(":")[-1].strip()
                print(f"Found Type: {current_display['type']}")
            
            # Parse resolution
            elif "Resolution:" in line:
                current_display["res"] = line.split(":")[-1].strip()
                print(f"Found Resolution: {current_display['res']}")

            # Parse Hertz
            elif "Hertz:" in line:
                current_display["hz"] = line.split(":")[-1].strip()
                print(f"Found Hertz: {current_display['hz']}")   

            # Color Depth
            elif "Color Depth:" in line:
                current_display["color_depth"] = line.split(":")[-1].strip()
                print(f"Found Color Depth: {current_display['color_depth']}")   

            elif "Scaling:" in line:
                current_display["scaling"] = line.split(":")[-1].strip()
                print(f"Found Scaling: {current_display['scaling']}") 

            elif "Origin:" in line:
                if "id" in current_display and current_display["id"] not in first_origin_values:
                    # First time finding Origin for this display, store it
                    first_origin_values[current_display["id"]] = parse_origin(line)
                    current_display["origin"] = first_origin_values[current_display["id"]]
                    print(f"Found and stored Origin: {current_display['origin']}")
                elif "id" in current_display and current_display["id"] in first_origin_values:
                    # Use previously stored Origin value
                    current_display["origin"] = first_origin_values[current_display["id"]]
                    print(f"Using stored Origin: {current_display['origin']}")

            elif "Rotation:" in line:
                current_display["degree"] = parse_rotation(line)
                print(f"Found Rotation: {current_display['degree']}")

            elif "Enabled:" in line:
                current_display["enabled"] = line.split(":")[-1].strip()
                print(f"Found Enabled: {current_display['enabled']}") 
            
            # When we have collected enough information, create display description and add to list
            if all(key in current_display for key in ["id", "type", "res", "hz", "color_depth", "scaling", "origin", "degree", "enabled"]):
                current_display["desc"] = f'{current_display["type"]} ({current_display["res"]}) - ID: {current_display["id"]}'
                print(f"Completed display description: {current_display['desc']}")
                displays.append(current_display.copy())
                current_display = {}  # Reset current display information
        
        print(f"Found {len(displays)} displays")
        return displays
    except FileNotFoundError:
        print("Error: 'displayplacer' command not found")
        return []
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute displayplacer: {e.stderr}")
        return []
    except Exception as e:
        print(f"Error parsing display information: {str(e)}")
        return []

def parse_rotation(rotation_str):
    """Parse Rotation string, extract angle value"""
    if not rotation_str:
        return None
    
    # Try to extract the numeric part
    import re
    match = re.search(r'Rotation:\s*(\d+)', rotation_str)
    if match:
        return match.group(1)  # Return the numeric part
    
    return rotation_str  # If no match found, return the original string

def parse_origin(origin_str):
    """Parse Origin string, extract coordinate part"""
    if not origin_str:
        return None
    
    # Try to extract coordinates in parentheses
    import re
    match = re.search(r'\(([^)]+)\)', origin_str)
    if match:
        return match.group(0)  # Return the complete (x,y) format
    
    return origin_str

def rotate_display(displays, display_id_to_control, degree):
    """Execute displayplacer command to rotate all screens while maintaining other display settings"""
    try:
        success = True
          # Build the complete displayplacer command
        command = 'displayplacer '
        for display in displays:
            # Add display ID
            command += f'"id:{display["id"]} '

            # Add rotation angle
            if display_id_to_control == display["id"]:
                command += f'degree:{degree} '
            else:
                command += f'degree:{display["degree"]} '
            
            # Add other parameters (if provided)
            if "res" in display:
                command += f'res:{display["res"]} '
            if "hz" in display:
                command += f'hz:{display["hz"]} '
            if "color_depth" in display:
                command += f'color_depth:{display["color_depth"]} '
            if "enabled" in display:
                command += f'enabled:{str(display["enabled"]).lower()} '
            if "scaling" in display:
                command += f'scaling:{display["scaling"]} '
            if "origin" in display:
                command += f'origin:{display["origin"]}" '
            
        socketio.emit('action', {'status': f"Executing: Rotating display {display['id']} to {degree}°"})
        
        # Execute command - use shell=True to handle the complete command string
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True, timeout=5)
            socketio.emit('action', {'status': f"Success: Display {display['id']} set to {degree}°"})
        except Exception as e:
            error_message = f"Error rotating display {display['id']}: {str(e)}"
            socketio.emit('action', {'message': error_message})
            success = False
        
        return success
        
    except Exception as e:
        error_message = f"Error rotating display: {str(e)}"
        socketio.emit('action', {'message': error_message})
        return False

def serial_monitor_thread(port, display_id_to_control):
    """Read serial port and process data in background thread"""
    global serial_connection, is_running, last_processed_degree
    
    socketio.emit('connection', {'status': f"Connecting to {port}...", 'color': 'orange'})
    
    while is_running:
        try:
            # Try to connect to serial port
            serial_connection = serial.Serial(port, 9600, timeout=2)
            socketio.emit('connection', {'status': f"Connected to {port}", 'color': 'green'})

            while is_running:
                if serial_connection.in_waiting > 0:
                    try:
                        line = serial_connection.readline().decode('utf-8').strip()
                        socketio.emit('received', {'data': line})
                        
                        if line in ["0", "90", "180", "270"]:
                            current_degree = line
                            # Only rotate if the angle is different from the last successfully processed one
                            if current_degree != last_processed_degree:
                                # Get all displays and rotate
                                try:
                                    displays = get_displays()
                                    if rotate_display(displays, display_id_to_control, current_degree):
                                        last_processed_degree = current_degree
                                except Exception as e:
                                    socketio.emit('action', {'message': f"Error getting or rotating displays: {str(e)}"})
                            else:
                                socketio.emit('action', {'status': f"Angle unchanged, skipping rotation: {current_degree}°"})
                        elif line:
                            socketio.emit('error', {'status': f"Received unexpected data: {line}"})

                    except UnicodeDecodeError:
                        socketio.emit('error', {'message': "Unable to decode received data, may contain non-UTF-8 characters"})
                    except Exception as read_err:
                        socketio.emit('error', {'message': f"Error reading or processing data: {read_err}"})
                        if isinstance(read_err, (serial.SerialException, OSError)):
                            raise
                        else:
                            time.sleep(0.1)

                else:
                    time.sleep(0.05)

            # Normal exit from inner loop
            if serial_connection.is_open:
                serial_connection.close()
            break

        except serial.SerialException as e:
            socketio.emit('connection', {'status': f"Unable to connect or disconnected: {port}", 'color': 'red'})
            if is_running:
                time.sleep(3)
            else:
                break
        except Exception as thread_err:
            socketio.emit('error', {'message': f"Unexpected error in monitoring thread: {thread_err}"})
            if is_running:
                time.sleep(3)
            else:
                break

    # Ensure connection is closed when thread ends
    if serial_connection and serial_connection.is_open:
        serial_connection.close()
    socketio.emit('connection', {'status': "Disconnected", 'color': 'grey'})

@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')

@app.route('/api/ports')
def get_ports():
    """API endpoint: Get serial port list"""
    ports = get_serial_ports()
    return jsonify(ports)

@app.route('/api/displays')
def get_displays_api():
    """API endpoint: Get display list"""
    displays = get_displays()
    return jsonify(displays)

@app.route('/api/start', methods=['POST'])
def start_monitoring():
    """API endpoint: Start monitoring serial port"""
    global is_running, serial_thread, last_processed_degree
    
    data = request.json
    port = data.get('port')
    display_id = data.get('display_id')
    
    if not port:
        return jsonify({'success': False, 'message': 'Please select a serial port'})
    if not display_id:
        return jsonify({'success': False, 'message': 'Please select a display to control'})
    
    if is_running:
        return jsonify({'success': False, 'message': 'Monitoring is already running'})
    
    is_running = True
    last_processed_degree = None
    
    # Start background thread
    serial_thread = threading.Thread(target=serial_monitor_thread, args=(port, display_id), daemon=True)
    serial_thread.start()
    
    return jsonify({'success': True, 'message': 'Monitoring started'})

@app.route('/api/stop', methods=['POST'])
def stop_monitoring():
    """API endpoint: Stop monitoring serial port"""
    global is_running, serial_connection
    
    if not is_running:
        return jsonify({'success': False, 'message': 'Monitoring is not running'})
    
    is_running = False
    
    if serial_connection and serial_connection.is_open:
        try:
            serial_connection.close()
        except Exception as e:
            print(f"Error closing serial port: {e}")
    
    return jsonify({'success': True, 'message': 'Monitoring stopped'})

@app.route('/api/debug/displays')
def debug_displays():
    """API endpoint: Directly check displayplacer output"""
    try:
        result = subprocess.run(['displayplacer', 'list'], capture_output=True, text=True)
        return jsonify({
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8098, debug=True) 