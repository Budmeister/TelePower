
import sqlite3
from datetime import datetime, timedelta
from time import sleep

def get_cc():
    conn = sqlite3.connect('energy_data.db')
    cursor = conn.cursor()
    return conn, cursor

def setup():
    conn, cursor = get_cc()
    # Create the tables if they don't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fine_records (
            datetime TEXT PRIMARY KEY,
            power REAL,
            energy REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS days (
            date TEXT PRIMARY KEY,
            power REAL,
            energy REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weeks (
            week_start TEXT PRIMARY KEY,
            power REAL,
            energy REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS months (
            month TEXT PRIMARY KEY,
            power REAL,
            energy REAL
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

setup()

def add_fine_record(power, energy, conn, cursor):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO fine_records VALUES (?, ?, ?)', (current_time, power, energy))
    conn.commit()

def merge_records(records):
    total_power = sum(record[0] for record in records)
    total_energy = sum(record[1] for record in records)
    avg_power = total_power / len(records)
    return avg_power, total_energy

def update_tables(conn, cursor):
    # Update days table
    cursor.execute('SELECT DISTINCT DATE(datetime) FROM fine_records')
    distinct_days = [row[0] for row in cursor.fetchall()]
    for day in distinct_days:
        if day >= (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'):
            continue  # Skip records from the last 7 days (including today)
        cursor.execute('SELECT power, energy FROM fine_records WHERE DATE(datetime) = ?', (day,))
        day_records = cursor.fetchall()
        cursor.execute('SELECT COUNT(*) FROM days WHERE date = ?', (day,))
        if cursor.fetchone()[0] == 0:
            avg_power, total_energy = merge_records(day_records)
            cursor.execute('INSERT INTO days VALUES (?, ?, ?)', (day, avg_power, total_energy))
            cursor.execute('DELETE FROM fine_records WHERE DATE(datetime) = ?', (day,))
            conn.commit()

    # Update weeks table
    cursor.execute('SELECT DISTINCT DATE(date, "weekday 0", "-6 days") FROM days')
    distinct_weeks = [row[0] for row in cursor.fetchall()]
    for week_start in distinct_weeks:
        if week_start == (datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%Y-%m-%d'):
            continue  # Skip current week's records
        cursor.execute('SELECT power, energy FROM days WHERE DATE(date) BETWEEN ? AND DATE(?, "+6 days")', (week_start, week_start))
        week_records = cursor.fetchall()
        cursor.execute('SELECT COUNT(*) FROM weeks WHERE week_start = ?', (week_start,))
        if cursor.fetchone()[0] == 0:
            avg_power, total_energy = merge_records(week_records)
            cursor.execute('INSERT INTO weeks VALUES (?, ?, ?)', (week_start, avg_power, total_energy))
            conn.commit()

    # Update months table
    cursor.execute('SELECT DISTINCT strftime("%Y-%m", date) FROM days')
    distinct_months = [row[0] for row in cursor.fetchall()]
    for month in distinct_months:
        if month == datetime.now().strftime('%Y-%m'):
            continue  # Skip current month's records
        cursor.execute('SELECT power, energy FROM days WHERE strftime("%Y-%m", date) = ?', (month,))
        month_records = cursor.fetchall()
        cursor.execute('SELECT COUNT(*) FROM months WHERE month = ?', (month,))
        if cursor.fetchone()[0] == 0:
            avg_power, total_energy = merge_records(month_records)
            cursor.execute('INSERT INTO months VALUES (?, ?, ?)', (month, avg_power, total_energy))
            conn.commit()

def get_records_within_time(time_range, conn, cursor):
    current_time = datetime.now()
    time_format = '%Y-%m-%d %H:%M:%S'

    if time_range.endswith('d'):
        days = int(time_range[:-1])
        start_time = (current_time - timedelta(days=days)).strftime(time_format)
    elif time_range.endswith('w'):
        weeks = int(time_range[:-1])
        start_time = (current_time - timedelta(weeks=weeks)).strftime(time_format)
    elif time_range.endswith('m'):
        months = int(time_range[:-1])
        start_time = (current_time - timedelta(days=months*30)).strftime(time_format)
    else:
        raise ValueError("Invalid time range format. Use 'd' for days, 'w' for weeks, or 'm' for months.")

    records = []

    # Retrieve records from fine_records table
    cursor.execute('SELECT * FROM fine_records WHERE datetime >= ?', (start_time,))
    fine_records = cursor.fetchall()
    records.extend([(datetime.strptime(record[0], time_format), record[1], record[2]) for record in fine_records])

    # Retrieve records from days table
    cursor.execute('SELECT * FROM days WHERE date >= ?', (start_time[:10],))
    day_records = cursor.fetchall()
    records.extend([(datetime.strptime(record[0], '%Y-%m-%d'), record[1], record[2]) for record in day_records])

    # Retrieve records from weeks table
    cursor.execute('SELECT * FROM weeks WHERE week_start >= ?', (start_time[:10],))
    week_records = cursor.fetchall()
    records.extend([(datetime.strptime(record[0], '%Y-%m-%d'), record[1], record[2]) for record in week_records])

    # Retrieve records from months table
    cursor.execute('SELECT * FROM months WHERE month >= ?', (start_time[:7],))
    month_records = cursor.fetchall()
    records.extend([(datetime.strptime(record[0], '%Y-%m'), record[1], record[2]) for record in month_records])

    return sorted(records, key=lambda x: x[0])

if __name__ == "__main__":
    # Example usage
    print("Adding example fine records")
    add_fine_record(10.5, 100)
    sleep(1)
    add_fine_record(12.3, 150)
    sleep(1)
    add_fine_record(9.8, 120)

    update_tables()

    # Retrieve records within the last 7 days
    records_7d = get_records_within_time('7d')
    print("Records within the last 7 days:")
    for record in records_7d:
        print(record)

    # Retrieve records within the last 2 weeks
    records_2w = get_records_within_time('2w')
    print("\nRecords within the last 2 weeks:")
    for record in records_2w:
        print(record)

    # Retrieve records within the last 1 month
    records_1m = get_records_within_time('1m')
    print("\nRecords within the last 1 month:")
    for record in records_1m:
        print(record)

    # Close the database connection
    conn.close()