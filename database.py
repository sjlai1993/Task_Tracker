# database.py

import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name='task_tracker.db'):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                project_code TEXT,
                description TEXT,
                categories TEXT,
                software TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_work_times (
                date TEXT PRIMARY KEY,
                effective_start_time TEXT NOT NULL,
                work_start_lower TEXT NOT NULL,
                work_start_upper TEXT NOT NULL,
                daily_working_hours REAL NOT NULL,
                lunch_start TEXT NOT NULL,
                lunch_end TEXT NOT NULL,
                working_days TEXT NOT NULL,
                holidays TEXT NOT NULL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS qa83_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_year TEXT NOT NULL,
                project_code TEXT NOT NULL,
                description TEXT NOT NULL,
                final_progress TEXT,
                UNIQUE(month_year, project_code, description)
            )
        ''')
        self.conn.commit()

    def add_task(self, task_date, start_time, end_time, project_code, description, categories, software):
        self.cursor.execute('''
            INSERT INTO tasks (task_date, start_time, end_time, project_code, description, categories, software)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (task_date, start_time, end_time, project_code, description, categories, software))
        self.conn.commit()

    def get_last_task(self):
        self.cursor.execute('SELECT * FROM tasks ORDER BY id DESC LIMIT 1')
        return self.cursor.fetchone()

    def get_tasks_for_date(self, date_str):
        self.cursor.execute('SELECT * FROM tasks WHERE task_date = ? ORDER BY start_time', (date_str,))
        return self.cursor.fetchall()
    
    def delete_task_by_id(self, task_id):
        self.cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        self.conn.commit()

    def update_task_by_id(self, task_id, data):
        self.cursor.execute('''
            UPDATE tasks 
            SET start_time = ?, end_time = ?, project_code = ?, 
                description = ?, categories = ?, software = ?
            WHERE id = ?
        ''', (
            data['start_time'], data['end_time'], data['project_code'],
            data['description'], data['categories'], data['software'],
            task_id
        ))
        self.conn.commit()

    def add_work_times(self, date_str, effective_start_time_str, settings):
        self.cursor.execute('''
            INSERT INTO daily_work_times (date, effective_start_time, work_start_lower, 
                                          work_start_upper, daily_working_hours, 
                                          lunch_start, lunch_end, working_days, holidays)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date_str,
              effective_start_time_str,
              settings['work_start_lower'], settings['work_start_upper'],
              settings['daily_working_hours'],
              settings['lunch_start'], settings['lunch_end'],
              ",".join(settings['working_days']), ",".join(settings['holidays'])))
        self.conn.commit()

    def get_work_times_for_date(self, date_str):
        self.cursor.execute('SELECT * FROM daily_work_times WHERE date = ?', (date_str,))
        return self.cursor.fetchone()

    def get_setting(self, key):
        self.cursor.execute('SELECT value FROM app_settings WHERE key = ?', (key,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def set_setting(self, key, value):
        self.cursor.execute('INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)', (key, value))
        self.conn.commit()

    def get_unique_tasks_for_month(self, month_year_str):
        self.cursor.execute('''
            SELECT DISTINCT project_code, description 
            FROM tasks 
            WHERE strftime('%Y-%m', task_date) = ?
            ORDER BY project_code, description
        ''', (month_year_str,))
        return self.cursor.fetchall()
    
    # =====================================================================
    # === MODIFIED SECTION START (Corrected filtering logic) ===
    # =====================================================================
    def get_unique_tasks_for_month_by_category(self, month_year_str, categories_list):
        if not categories_list:
            return []
        
        # Create a "?, ?, ?" string for the IN clause
        placeholders = ", ".join(["?"] * len(categories_list))
        
        # Build the query using proper parameter substitution for the LIKE clauses
        where_clauses = " OR ".join(["categories LIKE ?"] * len(categories_list))
        
        query = f'''
            SELECT DISTINCT project_code, description 
            FROM tasks 
            WHERE strftime('%Y-%m', task_date) = ? AND ({where_clauses})
            ORDER BY project_code, description
        '''
        
        # Build the parameters list: the month-year string, followed by
        # each category wrapped in '%' wildcards for the LIKE matching.
        params = [month_year_str] + [f'%{cat}%' for cat in categories_list]
        
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    # =====================================================================
    # === MODIFIED SECTION END ===
    # =====================================================================
    
    def get_task_hours_for_month(self, month_year, proj_code, desc):
        self.cursor.execute('''
            SELECT task_date, start_time, end_time
            FROM tasks
            WHERE strftime('%Y-%m', task_date) = ? AND project_code = ? AND description = ?
        ''', (month_year, proj_code, desc))
        return self.cursor.fetchall()

    def get_qa83_final_progress(self, month_year, proj_code, desc):
        self.cursor.execute('''
            SELECT final_progress 
            FROM qa83_progress 
            WHERE month_year = ? AND project_code = ? AND description = ?
        ''', (month_year, proj_code, desc))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def set_qa83_final_progress(self, month_year, proj_code, desc, final_progress):
        self.cursor.execute('''
            INSERT OR REPLACE INTO qa83_progress 
            (month_year, project_code, description, final_progress)
            VALUES (?, ?, ?, ?)
        ''', (month_year, proj_code, desc, final_progress))
        self.conn.commit()

    def __del__(self):
        self.conn.close()