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

# 全局變數
serial_connection = None
serial_thread = None
is_running = False
last_processed_degree = None
available_ports = {}
available_displays = {}

def get_serial_ports():
    """獲取可用的序列埠列表"""
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
    """使用 displayplacer 獲取顯示器列表"""
    try:
        print("正在執行 displayplacer list 命令...")
        result = subprocess.run(['displayplacer', 'list'], capture_output=True, text=True, check=True)
        output = result.stdout
        print(f"displayplacer 輸出:\n{output}")
        
        displays = []
        current_display = {}
        
        for line in output.splitlines():
            line = line.strip()
            print(f"處理行: {line}")
            
            # 解析顯示器ID
            if "Persistent screen id:" in line:
                current_display["id"] = line.split(":")[-1].strip()
                print(f"找到 Screen ID: {current_display['id']}")
            
            # 解析顯示器類型
            elif "Type:" in line:
                current_display["type"] = line.split(":")[-1].strip()
                print(f"找到 Type: {current_display['type']}")
            
            # 解析解析度
            elif "Resolution:" in line:
                current_display["res"] = line.split(":")[-1].strip()
                print(f"找到 Resolution: {current_display['res']}")

            # 解析Hertz
            elif "Hertz:" in line:
                current_display["hz"] = line.split(":")[-1].strip()
                print(f"找到 Hertz: {current_display['hz']}")   

            # Color Depth
            elif "Color Depth:" in line:
                current_display["color_depth"] = line.split(":")[-1].strip()
                print(f"找到 Hertz: {current_display['color_depth']}")   

            elif "Scaling:" in line:
                current_display["scaling"] = line.split(":")[-1].strip()
                print(f"找到 Scaling: {current_display['scaling']}") 

            elif "Origin:" in line:
                current_display["origin"] = parse_origin(line)
                print(f"找到 Origin: {current_display['origin']}") 


            elif "Rotation:" in line:
                current_display["degree"] = parse_rotation(line)
                print(f"找到 Rotation: {current_display['degree']}")

            elif "Enabled:" in line:
                current_display["enabled"] = line.split(":")[-1].strip()
                print(f"找到 Enabled: {current_display['enabled']}") 
            
            # 當我們收集到足夠的信息時，創建顯示器描述並添加到列表
            if all(key in current_display for key in ["id", "type", "res", "hz", "color_depth", "scaling", "origin", "degree", "enabled"]):
                current_display["desc"] = f'{current_display["type"]} ({current_display["res"]}) - ID: {current_display["id"]}'
                print(f"完成顯示器描述: {current_display['desc']}")
                displays.append(current_display.copy())
                current_display = {}  # 重置當前顯示器信息
        
        print(f"找到 {len(displays)} 個顯示器")
        return displays
    except FileNotFoundError:
        print("錯誤: 找不到 'displayplacer' 命令")
        return []
    except subprocess.CalledProcessError as e:
        print(f"執行 displayplacer 失敗: {e.stderr}")
        return []
    except Exception as e:
        print(f"解析顯示器信息時發生錯誤: {str(e)}")
        return []

def parse_rotation(rotation_str):
    """解析 Rotation 字符串，提取角度值"""
    if not rotation_str:
        return None
    
    # 嘗試提取數字部分
    import re
    match = re.search(r'Rotation:\s*(\d+)', rotation_str)
    if match:
        return match.group(1)  # 返回數字部分
    
    return rotation_str  # 如果沒有找到匹配，返回原始字符串

def parse_origin(origin_str):
    """解析 Origin 字符串，提取坐標部分"""
    if not origin_str:
        return None
    
    # 嘗試提取括號中的坐標
    import re
    match = re.search(r'\(([^)]+)\)', origin_str)
    if match:
        return match.group(0)  # 返回完整的 (x,y) 格式
    
    return origin_str

def rotate_display(displays, display_id_to_control, degree):
    """執行 displayplacer 命令來旋轉所有螢幕，同時保持其他顯示器設置"""
    try:
        success = True
          # 構建完整的 displayplacer 命令
        command = 'displayplacer '
        for display in displays:
            # 添加顯示器 ID
            command += f'"id:{display["id"]} '

            # 添加旋轉角度
            if display_id_to_control == display["id"]:
                command += f'degree:{degree} '
            else:
                command += f'degree:{display["degree"]} '
            
            # 添加其他參數（如果提供）
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
            
        socketio.emit('action', {'status': f"執行中: 旋轉顯示器 {display['id']} 到 {degree}°"})
        
        # 執行命令 - 使用 shell=True 來處理完整命令字符串
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True, timeout=5)
            socketio.emit('action', {'status': f"成功: 顯示器 {display['id']} 已設為 {degree}°"})
        except Exception as e:
            error_message = f"旋轉顯示器 {display['id']} 時發生錯誤: {str(e)}"
            socketio.emit('error', {'message': error_message})
            success = False
        
        return success
        
    except Exception as e:
        error_message = f"旋轉顯示器時發生錯誤: {str(e)}"
        socketio.emit('error', {'message': error_message})
        return False

def serial_monitor_thread(port, display_id_to_control):
    """在背景線程中讀取序列埠並處理數據"""
    global serial_connection, is_running, last_processed_degree
    
    socketio.emit('connection', {'status': f"正在連線到 {port}...", 'color': 'orange'})
    
    while is_running:
        try:
            # 嘗試連接序列埠
            serial_connection = serial.Serial(port, 9600, timeout=2)
            socketio.emit('connection', {'status': f"已連線到 {port}", 'color': 'green'})

            while is_running:
                if serial_connection.in_waiting > 0:
                    try:
                        line = serial_connection.readline().decode('utf-8').strip()
                        socketio.emit('received', {'data': line})
                        
                        if line in ["0", "90", "180", "270"]:
                            current_degree = line
                            # 只有當角度與上次成功處理的不同時才執行旋轉
                            if current_degree != last_processed_degree:
                                # 獲取所有顯示器並旋轉
                                try:
                                    displays = get_displays()
                                    if rotate_display(displays, display_id_to_control, current_degree):
                                        last_processed_degree = current_degree
                                except Exception as e:
                                    socketio.emit('error', {'message': f"獲取或旋轉顯示器時出錯: {str(e)}"})
                            else:
                                socketio.emit('action', {'status': f"角度未變化，跳過旋轉: {current_degree}°"})
                        elif line:
                            socketio.emit('action', {'status': f"收到非預期數據: {line}"})

                    except UnicodeDecodeError:
                        socketio.emit('error', {'message': "無法解碼收到的數據，可能包含非 UTF-8 字元"})
                    except Exception as read_err:
                        socketio.emit('error', {'message': f"讀取或處理數據時發生錯誤: {read_err}"})
                        if isinstance(read_err, (serial.SerialException, OSError)):
                            raise
                        else:
                            time.sleep(0.1)

                else:
                    time.sleep(0.05)

            # 正常退出內層循環
            if serial_connection.is_open:
                serial_connection.close()
            break

        except serial.SerialException as e:
            socketio.emit('connection', {'status': f"無法連線或斷線: {port}", 'color': 'red'})
            if is_running:
                time.sleep(3)
            else:
                break
        except Exception as thread_err:
            socketio.emit('error', {'message': f"監聽線程發生意外錯誤: {thread_err}"})
            if is_running:
                time.sleep(3)
            else:
                break

    # 線程結束時確保連接關閉
    if serial_connection and serial_connection.is_open:
        serial_connection.close()
    socketio.emit('connection', {'status': "未連線", 'color': 'grey'})

@app.route('/')
def index():
    """渲染主頁"""
    return render_template('index.html')

@app.route('/api/ports')
def get_ports():
    """API 端點：獲取序列埠列表"""
    ports = get_serial_ports()
    return jsonify(ports)

@app.route('/api/displays')
def get_displays_api():
    """API 端點：獲取顯示器列表"""
    displays = get_displays()
    return jsonify(displays)

@app.route('/api/start', methods=['POST'])
def start_monitoring():
    """API 端點：開始監聽序列埠"""
    global is_running, serial_thread, last_processed_degree
    
    data = request.json
    port = data.get('port')
    display_id = data.get('display_id')
    
    if not port:
        return jsonify({'success': False, 'message': '請選擇一個序列埠'})
    if not display_id:
        return jsonify({'success': False, 'message': '請選擇一個要控制的顯示器'})
    
    if is_running:
        return jsonify({'success': False, 'message': '監聽已在運行中'})
    
    is_running = True
    last_processed_degree = None
    
    # 啟動背景線程
    serial_thread = threading.Thread(target=serial_monitor_thread, args=(port, display_id), daemon=True)
    serial_thread.start()
    
    return jsonify({'success': True, 'message': '監聽已啟動'})

@app.route('/api/stop', methods=['POST'])
def stop_monitoring():
    """API 端點：停止監聽序列埠"""
    global is_running, serial_connection
    
    if not is_running:
        return jsonify({'success': False, 'message': '監聽未在運行中'})
    
    is_running = False
    
    if serial_connection and serial_connection.is_open:
        try:
            serial_connection.close()
        except Exception as e:
            print(f"關閉序列埠時出錯: {e}")
    
    return jsonify({'success': True, 'message': '監聽已停止'})

@app.route('/api/debug/displays')
def debug_displays():
    """API 端點：直接檢查 displayplacer 輸出"""
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