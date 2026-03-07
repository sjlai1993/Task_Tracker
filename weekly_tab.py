import os
import sys
import json
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                                 QGroupBox, QGridLayout, QCalendarWidget, QDialog)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import Qt, QUrl, QObject, Slot, QDate, QTime, QTimer

class WeeklyApi(QObject):
    def __init__(self, db, parent_tab, config):
        super().__init__()
        self.db = db
        self.parent_tab = parent_tab
        self.config = config
        self.PROJECT_TITLES_FILE = 'project_names.json'

    @Slot(result=dict)
    def get_project_titles(self):
        if os.path.exists(self.PROJECT_TITLES_FILE):
            try:
                with open(self.PROJECT_TITLES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {}

    @Slot(str, str, result=list)
    def get_tasks(self, start_date_str, end_date_str):
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        all_tasks = []
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            tasks = self.db.get_tasks_for_date(date_str)
            for t in tasks:
                all_tasks.append({
                    'id': t[0],
                    'task_date': t[1],
                    'start_time': t[2],
                    'end_time': t[3],
                    'project_code': t[4],
                    'description': t[5]
                })
            current_date += timedelta(days=1)
        return all_tasks

    @Slot(result=dict)
    def get_project_colors(self):
        color_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'project_colors.json')
        if os.path.exists(color_file):
            with open(color_file, 'r') as f:
                return json.load(f)
        return {}

    @Slot(str, str)
    def save_project_color(self, project_code, color):
        color_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'project_colors.json')
        colors = {}
        if os.path.exists(color_file):
            with open(color_file, 'r') as f:
                colors = json.load(f)
        colors[project_code] = color
        with open(color_file, 'w') as f:
            json.dump(colors, f)

    def _safe_refresh(self):
        """Helper to safely call _refresh_all_tabs on the main window."""
        win = self.parent_tab.window()
        if win and hasattr(win, '_refresh_all_tabs'):
            win._refresh_all_tabs()
        else:
            parent = self.parent_tab.parent()
            while parent:
                if hasattr(parent, '_refresh_all_tabs'):
                    parent._refresh_all_tabs()
                    break
                parent = parent.parent()

    @Slot(int, str, str, str)
    def update_task(self, task_id, new_date, new_start, new_end):
        task = self.db.get_task_by_id(task_id)
        if not task:
            return
        
        data = {
            'start_time': new_start,
            'end_time': new_end,
            'project_code': task[4],
            'description': task[5],
            'categories': task[6],
            'software': task[7]
        }
        self.db.cursor.execute('UPDATE tasks SET task_date = ? WHERE id = ?', (new_date, task_id))
        self.db.update_task_by_id(task_id, data)
        self._safe_refresh()

    @Slot(int, str, str, str)
    def duplicate_task(self, task_id, new_date, new_start, new_end):
        task = self.db.get_task_by_id(task_id)
        if not task:
            return
        
        self.db.add_task(
            new_date,
            new_start,
            new_end,
            task[4],
            task[5],
            task[6],
            task[7]
        )
        self._safe_refresh()

    @Slot(int)
    def show_task_detail_dialog(self, task_id):
        # We reuse the edit dialog for now
        self.edit_task_dialog(task_id)

    @Slot(int)
    def edit_task_dialog(self, task_id):
        from popup import EditTaskPopup
        task_data = self.db.get_task_by_id(task_id)
        if not task_data:
            return
        
        dialog = EditTaskPopup(self.db, self.config, task_data, parent=self.parent_tab)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._safe_refresh()

    @Slot(int)
    def show_task_context_menu(self, task_id):
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QCursor, QAction
        
        menu = QMenu(self.parent_tab)
        detail_action = QAction("Show Detail", self.parent_tab)
        detail_action.triggered.connect(lambda: self.show_task_detail_dialog(task_id))
        menu.addAction(detail_action)

        edit_action = QAction("Edit Task", self.parent_tab)
        edit_action.triggered.connect(lambda: self.edit_task_dialog(task_id))
        menu.addAction(edit_action)
        
        delete_action = QAction("Delete Task", self.parent_tab)
        delete_action.triggered.connect(lambda: self.delete_task_dialog(task_id))
        menu.addAction(delete_action)
        
        menu.exec(QCursor.pos())

    @Slot(int)
    def delete_task_dialog(self, task_id):
        from PySide6.QtWidgets import QMessageBox
        task = self.db.get_task_by_id(task_id)
        if not task:
            return
            
        project_code = task[4]
        child_task_ids = self.db.get_child_task_ids(task_id)

        if child_task_ids:
            reply = QMessageBox.warning(self.parent_tab, "Confirm Delete Master Task",
                f"This task is a master for <b>{len(child_task_ids)} other task(s)</b>.<br><br>"
                f"Deleting it will unmerge all associated tasks.<br><br>"
                f"Are you sure you want to delete this master task for project '{project_code}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
        else:
            reply = QMessageBox.question(self.parent_tab, "Confirm Delete",
                f"Are you sure you want to delete the task for project '{project_code}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if child_task_ids:
                self.db.unmerge_specific_tasks(child_task_ids)
            self.db.delete_task_by_id(task_id)
            self._safe_refresh()

    def _get_settings_for_date(self, date_obj):
        date_str = date_obj.strftime('%Y-%m-%d')
        settings = self.db.get_work_times_for_date(date_str)
        if settings:
            start_time = settings[1] if settings[1] else settings[3]
            return {
                'start': start_time,
                'hours': settings[4],
                'lunch_start': settings[5],
                'lunch_end': settings[6]
            }
        
        # Fallback to config defaults
        config = self.config
        is_working = date_obj.strftime('%A') in config.get('working_days', []) and \
                     date_obj.strftime('%Y-%m-%d') not in config.get('holidays', [])
        
        return {
            'start': config.get('work_start_time_flexible', {}).get('upper', '09:15:00'),
            'hours': config.get('daily_working_hours', 8.0) if is_working else 0.0,
            'lunch_start': config.get('lunch_hour', {}).get('start', '12:30:00'),
            'lunch_end': config.get('lunch_hour', {}).get('end', '13:30:00')
        }

    @Slot(str, int)
    def add_task_at(self, date_str, minutes):
        # Find MainWindow to call manual_popup
        win = self.parent_tab.window()
        if not (win and hasattr(win, 'manual_popup')):
            parent = self.parent_tab.parent()
            while parent:
                if hasattr(parent, 'manual_popup'):
                    win = parent
                    break
                parent = parent.parent()
        
        if win and hasattr(win, 'manual_popup'):
            from datetime import time, datetime, timedelta
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            settings = self._get_settings_for_date(date_obj)
            
            if settings['hours'] <= 0:
                return

            # Work boundaries
            work_start_mins = self._time_str_to_mins(settings['start'])
            lunch_start_mins = self._time_str_to_mins(settings['lunch_start'])
            lunch_end_mins = self._time_str_to_mins(settings['lunch_end'])
            
            # Calculate workday end
            eff_start_dt = datetime.combine(date_obj, time(work_start_mins // 60, work_start_mins % 60))
            lunch_dur = timedelta(minutes=(lunch_end_mins - lunch_start_mins))
            work_dur = timedelta(hours=settings['hours'])
            work_end_dt = eff_start_dt + work_dur + lunch_dur
            work_end_mins = (work_end_dt.hour * 60) + work_end_dt.minute

            # Define segments
            if minutes < lunch_start_mins:
                seg_start, seg_end = work_start_mins, lunch_start_mins
            else:
                seg_start, seg_end = lunch_end_mins, work_end_mins

            # Find existing tasks for this day
            tasks = self.db.get_tasks_for_date(date_str)
            tasks_in_seg = []
            for t in tasks:
                t_start = self._time_str_to_mins(t[2])
                t_end = self._time_str_to_mins(t[3])
                if t_start < seg_end and t_end > seg_start:
                    tasks_in_seg.append((t_start, t_end))
            
            # Find gap boundaries
            gap_start = seg_start
            gap_end = seg_end
            
            # Narrow gap based on previous tasks
            for t_start, t_end in tasks_in_seg:
                if t_end <= minutes:
                    gap_start = max(gap_start, t_end)
                if t_start > minutes:
                    gap_end = min(gap_end, t_start)

            # Cap today's tasks at current time
            now = datetime.now()
            if date_obj == now.date():
                now_mins = now.hour * 60 + now.minute
                if gap_start < now_mins < gap_end:
                    gap_end = now_mins

            start_t = time(gap_start // 60, gap_start % 60)
            end_t = time(gap_end // 60, gap_end % 60)
            
            win.manual_popup(start_time=start_t, end_time=end_t, date_obj=date_obj)

    def _time_str_to_mins(self, t_str):
        if not t_str: return 0
        try:
            parts = t_str.split(':')
            return int(parts[0]) * 60 + int(parts[1])
        except:
            return 0

    @Slot(int, str, str)
    def update_task_multi(self, task_id, date_str, segments_json):
        segments = json.loads(segments_json)
        if not segments:
            return
            
        task = self.db.get_task_by_id(task_id)
        if not task:
            return

        # First segment updates the existing task
        first = segments[0]
        data = {
            'start_time': first['start'],
            'end_time': first['end'],
            'project_code': task[4],
            'description': task[5],
            'categories': task[6],
            'software': task[7]
        }
        self.db.cursor.execute('UPDATE tasks SET task_date = ? WHERE id = ?', (date_str, task_id))
        self.db.update_task_by_id(task_id, data)
        
        # Subsequent segments create new tasks
        for seg in segments[1:]:
            self.db.add_task(
                date_str,
                seg['start'],
                seg['end'],
                task[4],
                task[5],
                task[6],
                task[7]
            )
        
        self._safe_refresh()

    @Slot(str, str, result=str)
    def get_work_settings(self, start_date_str, end_date_str):
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        all_settings = {}
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            all_settings[date_str] = self._get_settings_for_date(current_date)
            current_date += timedelta(days=1)
        return json.dumps(all_settings)

class WeeklyTab(QWidget):
    def __init__(self, parent, db, config):
        super().__init__(parent)
        self.db = db
        self.config = config
        self.view_date = datetime.now().date()
        self.is_loaded = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Week Navigation
        nav_group = QGroupBox("Week Navigation")
        nav_layout = QHBoxLayout(nav_group)
        
        today_button = QPushButton("Today")
        today_button.setToolTip("Go to Today")
        today_button.clicked.connect(self._go_to_today)
        
        prev_button = QPushButton("<")
        prev_button.setToolTip("Previous Week")
        prev_button.setFixedWidth(30)
        prev_button.clicked.connect(self._go_to_previous_week)

        prev_month_button = QPushButton("<<")
        prev_month_button.setToolTip("Previous Month")
        prev_month_button.setFixedWidth(30)
        prev_month_button.clicked.connect(self._go_to_previous_month)

        next_month_button = QPushButton(">>")
        next_month_button.setToolTip("Next Month")
        next_month_button.setFixedWidth(30)
        next_month_button.clicked.connect(self._go_to_next_month)
        
        next_button = QPushButton(">")
        next_button.setToolTip("Next Week")
        next_button.setFixedWidth(30)
        next_button.clicked.connect(self._go_to_next_week)
        
        self.week_label = QLabel()
        self.week_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.week_label.setStyleSheet("QLabel { border: 1px solid gray; border-radius: 4px; padding: 4px; }")
        self.week_label.setToolTip("Click to select a date")
        self.week_label.mousePressEvent = self._show_calendar_picker
        
        nav_layout.addWidget(today_button)
        nav_layout.addWidget(prev_button)
        nav_layout.addWidget(prev_month_button)
        nav_layout.addWidget(next_month_button)
        nav_layout.addWidget(next_button)
        nav_layout.addWidget(self.week_label, 1)
        
        layout.addWidget(nav_group, 0)

        self.view = QWebEngineView()
        self.channel = QWebChannel()
        self.api = WeeklyApi(self.db, self, self.config)
        self.channel.registerObject('pyApi', self.api)
        self.view.page().setWebChannel(self.channel)
        
        # Set initial zoom factor
        zoom = self.config.get('weekly_zoom_factor', 1.0)
        self.view.setZoomFactor(zoom)
        
        # Connect zoom factor changed signal
        self.view.page().zoomFactorChanged.connect(self._on_zoom_factor_changed)
        
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.realpath(__file__))
        
        # Clear cache to ensure CSS/JS updates are loaded immediately
        self.view.page().profile().clearHttpCache()
        
        html_path = os.path.join(base_path, 'weekly_view.html')
        self.view.loadFinished.connect(self._on_load_finished)
        self.view.setUrl(QUrl.fromLocalFile(html_path))
        
        layout.addWidget(self.view, 1)

    def _get_week_boundaries(self, date_obj):
        days_to_sunday = (date_obj.weekday() + 1) % 7
        start_of_week = date_obj - timedelta(days=days_to_sunday)
        end_of_week = start_of_week + timedelta(days=6)
        return start_of_week, end_of_week

    def _go_to_today(self):
        self.view_date = datetime.now().date()
        self.update_nav_and_js()

    def _go_to_previous_week(self):
        self.view_date -= timedelta(weeks=1)
        self.update_nav_and_js()

    def _go_to_next_week(self):
        self.view_date += timedelta(weeks=1)
        self.update_nav_and_js()

    def _go_to_previous_month(self):
        self.view_date -= timedelta(days=30)
        self.update_nav_and_js()

    def _go_to_next_month(self):
        self.view_date += timedelta(days=30)
        self.update_nav_and_js()

    def _show_calendar_picker(self, event):
        calendar_dialog = QDialog(self)
        calendar_dialog.setWindowTitle("Select Date")
        cal_layout = QVBoxLayout(calendar_dialog)
        calendar = QCalendarWidget()
        calendar.setSelectedDate(QDate(self.view_date))

        def on_date_selected():
            self.view_date = calendar.selectedDate().toPython()
            self.update_nav_and_js()
            calendar_dialog.accept()

        calendar.selectionChanged.connect(on_date_selected)
        cal_layout.addWidget(calendar)
        # Lock size after the dialog is shown so it never resizes when changing months
        QTimer.singleShot(0, lambda: calendar_dialog.setFixedSize(calendar_dialog.sizeHint()))
        calendar_dialog.exec()

    def update_nav_and_js(self):
        start_of_week, end_of_week = self._get_week_boundaries(self.view_date)
        self.week_label.setText(
            f"{start_of_week.strftime('%d/%m/%Y')} to {end_of_week.strftime('%d/%m/%Y')}"
        )
        start_str = start_of_week.strftime('%Y-%m-%d')
        if self.is_loaded:
            # Wrap in a safety check to avoid ReferenceError if called too early
            js_code = f"""
            if (typeof window.setWeekStart === 'function') {{
                window.setWeekStart('{start_str}');
            }} else {{
                console.warn('Weekly setWeekStart not yet available, will retry on loadFinished');
            }}
            """
            self.view.page().runJavaScript(js_code)

    def _on_load_finished(self, success):
        self.is_loaded = True
        if success:
            self.update_nav_and_js()

    def refresh_view(self):
        self.update_nav_and_js()

    def _on_zoom_factor_changed(self, factor):
        """Saves current zoom factor to config."""
        self.config['weekly_zoom_factor'] = factor
        win = self.window()
        if win and hasattr(win, 'save_config'):
            win.save_config()
        else:
            # Fallback to search through parents
            parent = self.parent()
            while parent:
                if hasattr(parent, 'save_config'):
                    parent.save_config()
                    break
                parent = parent.parent()
