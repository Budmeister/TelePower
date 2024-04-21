from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
import schedule
import time
import random
from datetime import datetime

from energy_read import find_device, get_power_reading
from power_tables import add_fine_record, update_tables, get_records_within_time, get_cc

app = Flask(__name__)
socketio = SocketIO(app)

local_state = False  # Initial power state
motherboard_power = True  # Initial motherboard power state

recent_log_messages = []

# Sample data for different time densities
data = {
    '1d': [['Time', 'Price'], ['10:00', 100], ['11:00', 120], ['12:00', 110], ['13:00', 130]],
    '5d': [['Time', 'Price'], ['Day 1', 100], ['Day 2', 120], ['Day 3', 110], ['Day 4', 130], ['Day 5', 140]],
    '1m': [['Time', 'Price'], ['Week 1', 100], ['Week 2', 120], ['Week 3', 110], ['Week 4', 130]]
}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('power_toggle')
def power_toggle(state):
    global local_state
    print(f"Power state changed to {state}")
    # Update the power state in your backend logic
    # Emit the updated power state to all connected clients
    local_state = state
    emit('power_state', state, broadcast=True)

@socketio.on('get_data')
def get_data(time_density):
    chart_data = data.get(time_density)
    emit('chart_data', chart_data)

@socketio.on('recent_logs')
def get_recent_logs():
    emit('recent_logs', recent_log_messages)

def emit_power_state():
    global local_state
    global motherboard_power
    while True:
        time.sleep(1)  # Delay for 1 second
        print("Emitting power state")
        socketio.emit('power_state', local_state)
        print("Emitting motherboard power")
        socketio.emit('motherboard_power', motherboard_power)

log_messages = [
    "System initialized successfully.",
    "Connection established with the database.",
    "User authentication successful.",
    "Data retrieval in progress...",
    "Data processing completed.",
    "Sending response to the client.",
    "Error occurred while fetching data from the API.",
    "Retrying failed request...",
    "Cache invalidated due to new data.",
    "Scheduled task executed successfully.",
    "Backup process started.",
    "Backup completed successfully.",
    "Monitoring system health...",
    "High CPU usage detected.",
    "Low memory warning triggered.",
    "Disk space running low.",
    "Network latency detected.",
    "Security scan initiated.",
    "Potential security breach detected.",
    "System update available.",
    "Applying system updates...",
    "Update completed successfully.",
    "Restarting services...",
    "Services restarted successfully.",
    "Logging enabled for debugging.",
    "Debug mode activated.",
    "Performance profiling started.",
    "Profiling results generated.",
    "Optimization recommendations provided.",
    "User feedback received.",
    "Processing user feedback...",
    "Feedback processed successfully.",
    "Generating reports...",
    "Reports generated and stored.",
    "Sending reports to stakeholders.",
    "Data archiving in progress...",
    "Data archived successfully.",
    "Cleaning up temporary files.",
    "Temporary files cleaned up.",
    "System maintenance scheduled.",
    "Maintenance tasks completed.",
    "System ready for peak usage.",
    "Peak usage period started.",
    "Handling increased traffic load.",
    "Traffic load normalized.",
    "Monitoring resource utilization.",
    "Resource utilization optimized.",
    "System performance optimized.",
    "Preparing for system shutdown.",
    "System shutdown initiated.",
    "Shutdown completed successfully."
]

def emit_log(log_message):
    # Get the current timestamp
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Create a log entry with the message and timestamp
    log_entry = f"[{timestamp}] - {log_message}"
    
    # Add the log entry to the recent log messages
    recent_log_messages.append(log_entry)
    
    # Keep only the last 100 log messages
    if len(recent_log_messages) > 100:
        recent_log_messages.pop(0)
    
    # Emit the log entry to all connected clients
    socketio.emit('log_message', log_entry)


def emit_random_log_messages():
    while True:
        # Select a random log message from the array
        log_message = random.choice(log_messages)
        
        # Get the current timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Create a log entry with the message and timestamp
        log_entry = f"{timestamp} - {log_message}"
        
        # Add the log entry to the recent log messages
        recent_log_messages.append(log_entry)
        
        # Keep only the last 100 log messages
        if len(recent_log_messages) > 100:
            recent_log_messages.pop(0)
        
        # Emit the log entry to all connected clients
        socketio.emit('log_message', log_entry)
        
        # Wait for a random interval before emitting the next message
        interval = random.uniform(0.5, 2.0)  # Random interval between 0.5 and 2 seconds
        time.sleep(interval)

def gather_energy_data():
    conn, cursor = get_cc()

    ip = None
    while ip is None:
        ip = find_device()

    last_sample = time.time()
    last_error_log = time.time()
    while True:
        power = get_power_reading(ip)
        cur_time = time.time()
        if not power:
            if cur_time - last_sample > 10 * 60 and cur_time - last_error_log > 10 * 60:
                minutes = (cur_time - last_sample) // 60
                emit_log(f"Last sample was more than {minutes} minutes ago...")
                last_error_log = cur_time
            continue
        power = float(power)
        last_sample = cur_time
        energy = power * 5 # TODO use trapazoidal interpolation
        add_fine_record(power, energy, conn, cursor)
        time.sleep(5)

def maintain_tables():
    conn, cursor = get_cc()
    # Schedule the function to run at 1 AM every day
    schedule.every().day.at("01:00").do(lambda: update_tables(conn, cursor))

    # Run the scheduled tasks
    while True:
        schedule.run_pending()
        time.sleep(60 * 10)

if __name__ == '__main__':
    thread_targets = [
        ("Emit Power State Thread", emit_power_state),
        ("Gather Energy Thread", gather_energy_data),
        ("Maintain Tables Thread", maintain_tables),
        ("Log Random Messages Thread", emit_random_log_messages),
    ]
    thread_handles = []
    for thread_name, thread_target in thread_targets:
        print(f"Starting thread: {thread_name}")
        handle = threading.Thread(target=thread_target)
        handle.start()
        thread_handles.append(handle)
    socketio.run(app, port=8447)
