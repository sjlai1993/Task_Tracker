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
                software TEXT,
                master_task_id INTEGER,
                merged_description TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_work_times (
                date TEXT PRIMARY KEY,
                effective_start_time TEXT NOT NULL,
                work_start_lower TEXT NOT NULL,
                work_start_upper NOT NULL,
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
                start_progress TEXT,
                UNIQUE(month_year, project_code, description)
            )
        ''')
        try:
            self.cursor.execute('ALTER TABLE qa83_progress ADD COLUMN start_progress TEXT')
        except sqlite3.OperationalError:
            # Column likely already exists, which is fine.
            pass
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_titles (
                project_code TEXT PRIMARY KEY,
                project_title TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def begin_transaction(self):
        self.conn.execute('BEGIN TRANSACTION')

    def commit_transaction(self):
        self.conn.commit()

    def rollback_transaction(self):
        self.conn.rollback()

    def set_effective_start_time(self, date_str, new_start_time_str):
        """Updates the effective_start_time for a given date. Returns row count."""
        self.cursor.execute('''
            UPDATE daily_work_times SET effective_start_time = ? WHERE date = ?
        ''', (new_start_time_str, date_str))
        self.conn.commit()
        return self.cursor.rowcount

    def update_task_categories(self, task_id, new_categories_str):
        """Updates the categories for a specific task."""
        self.cursor.execute('UPDATE tasks SET categories = ? WHERE id = ?', (new_categories_str, task_id))
        self.conn.commit()

    def get_task_ids_for_master(self, master_id, month_year_str):
        """Gets all task IDs (including the master) associated with a master task for a given month."""
        self.cursor.execute('''
            SELECT id FROM tasks 
            WHERE (id = ? OR master_task_id = ?) AND strftime('%Y-%m', task_date) = ?
        ''', (master_id, master_id, month_year_str))
        return [row[0] for row in self.cursor.fetchall()]

    def clear_master_for_tasks(self, task_ids):
        """Resets the master_task_id and merged_description for a list of tasks."""
        if not task_ids:
            return
        placeholders = ','.join('?' for _ in task_ids)
        query_master = f"UPDATE tasks SET master_task_id = NULL WHERE id IN ({placeholders})"
        # Also clear the merged_description from the master task itself
        query_desc = f"UPDATE tasks SET merged_description = NULL WHERE id IN ({placeholders})"
        params = task_ids
        self.cursor.execute(query_master, params)
        self.cursor.execute(query_desc, params)
        self.conn.commit()
    
    def get_tasks_for_master_group(self, master_id):
        """Retrieves all tasks (master and children) belonging to a merged group."""
        self.cursor.execute('SELECT * FROM tasks WHERE id = ? OR master_task_id = ?', (master_id, master_id))
        return self.cursor.fetchall()

    def get_child_task_ids(self, master_id):
        """Retrieves the IDs of all child tasks for a given master task ID."""
        self.cursor.execute('SELECT id FROM tasks WHERE master_task_id = ?', (master_id,))
        return [row[0] for row in self.cursor.fetchall()]

    def unmerge_specific_tasks(self, task_ids):
        """Sets the master_task_id to NULL for a specific list of task IDs."""
        if not task_ids:
            return
        placeholders = ','.join('?' for _ in task_ids)
        query = f"UPDATE tasks SET master_task_id = NULL WHERE id IN ({placeholders})"
        self.cursor.execute(query, task_ids)
        self.conn.commit()

    def get_project_title(self, project_code):
        """Retrieves the project title for a given project code."""
        self.cursor.execute('SELECT project_title FROM project_titles WHERE project_code = ?', (project_code,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def set_project_title(self, project_code, project_title):
        """Inserts or updates a project title."""
        self.cursor.execute('INSERT OR REPLACE INTO project_titles (project_code, project_title) VALUES (?, ?)', (project_code, project_title))
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

    def get_task_before(self, before_datetime):
        """
        Retrieves the latest task that starts before the given datetime.
        """
        before_date_str = before_datetime.strftime('%Y-%m-%d')
        before_time_str = before_datetime.strftime('%H:%M:%S')
        
        self.cursor.execute('''
            SELECT * FROM tasks 
            WHERE task_date < ? OR (task_date = ? AND start_time < ?)
            ORDER BY task_date DESC, start_time DESC 
            LIMIT 1
        ''', (before_date_str, before_date_str, before_time_str))
        return self.cursor.fetchone()

    def get_unique_project_codes(self):
        """Retrieves a sorted list of unique project codes from the tasks table."""
        self.cursor.execute('SELECT DISTINCT project_code FROM tasks WHERE project_code IS NOT NULL ORDER BY project_code')
        return [row[0] for row in self.cursor.fetchall()]

    def get_unique_descriptions_for_project(self, project_code):
        """Retrieves a list of unique, non-empty HTML descriptions for a given project code."""
        if not project_code:
            return []
        self.cursor.execute('SELECT DISTINCT description FROM tasks WHERE project_code = ? AND description IS NOT NULL AND TRIM(description) != ""', (project_code,))
        return [row[0] for row in self.cursor.fetchall()]

    def get_tasks_for_date(self, date_str):
        self.cursor.execute('SELECT id, task_date, start_time, end_time, project_code, description, categories, software, master_task_id FROM tasks WHERE task_date = ? ORDER BY start_time', (date_str,))
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
            INSERT OR REPLACE INTO daily_work_times (date, effective_start_time, work_start_lower, 
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

    def get_unique_tasks_for_month_by_category(self, month_year_str, categories_list):
        if not categories_list:
            return []
        
        where_clauses = " OR ".join(["categories LIKE ?"] * len(categories_list))
        
        query = f'''
            SELECT DISTINCT project_code, description 
            FROM tasks 
            WHERE strftime('%Y-%m', task_date) = ? AND ({where_clauses})
            ORDER BY project_code, description
        '''
        
        params = [month_year_str] + [f'%{cat}%' for cat in categories_list]
        
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    
    def get_task_hours_for_month(self, month_year, proj_code, desc):
        self.cursor.execute('''
            SELECT task_date, start_time, end_time
            FROM tasks
            WHERE strftime('%Y-%m', task_date) = ? AND project_code = ? AND description = ?
        ''', (month_year, proj_code, desc))
        return self.cursor.fetchall()

    def get_task_by_id(self, task_id):
        self.cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        return self.cursor.fetchone()

    def get_tasks_for_month_with_master_info(self, month_year_str):
        self.cursor.execute('''
            SELECT 
                t.id, t.task_date, t.start_time, t.end_time, t.project_code, 
                t.description, t.categories, t.software, t.master_task_id,
                m.project_code, m.description, m.merged_description
            FROM tasks t 
            LEFT JOIN tasks m ON t.master_task_id = m.id 
            WHERE strftime('%Y-%m', t.task_date) = ?
        ''', (month_year_str,))
        return self.cursor.fetchall()
        
    def get_task_ids_for_group(self, month_year_str, proj_code, description):
        self.cursor.execute('''
            SELECT id FROM tasks 
            WHERE strftime('%Y-%m', task_date) = ? AND project_code = ? AND description = ?
        ''', (month_year_str, proj_code, description))
        return [row[0] for row in self.cursor.fetchall()]

    def set_master_for_tasks(self, task_ids, master_id):
        if not task_ids:
            return
        placeholders = ','.join('?' for _ in task_ids)
        query = f"UPDATE tasks SET master_task_id = ? WHERE id IN ({placeholders})"
        params = [master_id] + task_ids
        self.cursor.execute(query, params)
        self.conn.commit()

    def set_merged_description(self, master_id, merged_desc):
        self.cursor.execute('UPDATE tasks SET merged_description = ? WHERE id = ?', (merged_desc, master_id))
        self.conn.commit()

    def get_qa83_progress(self, month_year, proj_code, desc):
        self.cursor.execute('''
            SELECT start_progress, final_progress 
            FROM qa83_progress 
            WHERE month_year = ? AND project_code = ? AND description = ?
        ''', (month_year, proj_code, desc))
        result = self.cursor.fetchone()
        return result if result else (None, None)

    def set_qa83_progress(self, month_year, proj_code, desc, start_progress, final_progress):
        self.cursor.execute('''
            INSERT OR REPLACE INTO qa83_progress 
            (month_year, project_code, description, start_progress, final_progress)
            VALUES (?, ?, ?, ?, ?)
        ''', (month_year, proj_code, desc, start_progress, final_progress))
        self.conn.commit()

    def __del__(self):
        self.conn.close()