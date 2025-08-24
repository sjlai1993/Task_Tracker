# qa83_tab.py

import json
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTableWidget, QTableWidgetItem, QDialog,
                             QGroupBox, QGridLayout, QCalendarWidget, QHeaderView,
                             QAbstractItemView, QLineEdit, QFormLayout)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QTextDocument
from datetime import datetime, time
import calendar

class ProgressInputDialog(QDialog):
    """A dialog to get a single final progress percentage from the user."""
    def __init__(self, project_code, description, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Task Progress")
        
        form_layout = QFormLayout()
        form_layout.addRow(QLabel(f"<b>Project:</b> {project_code}"))
        form_layout.addRow(QLabel(f"<b>Task:</b> {description}"))
        
        self.progress_input = QLineEdit()
        self.progress_input.setPlaceholderText("e.g., 85, or '-' for recurring")
        form_layout.addRow("Final Cumulative Progress (%):", self.progress_input)

        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addStretch()
        button_box.addWidget(cancel_button)
        button_box.addWidget(ok_button)
        
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(form_layout)
        main_layout.addLayout(button_box)

    def get_value(self):
        return self.progress_input.text().strip()


class QA83Tab(QWidget):
    CONFIG_FILE = 'QA83.json'

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.view_date = datetime.now().date()
        self.qa83_config = self._load_config()
        
        self.init_ui()
        self.update_qa83_view()

    def _load_config(self):
        if not os.path.exists(self.CONFIG_FILE):
            default_config = {"qa83_categories": ["QA83"]}
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
        
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"qa83_categories": []}

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        nav_group = QGroupBox("Month Navigation")
        nav_layout = QGridLayout(nav_group)
        
        prev_button = QPushButton("<")
        prev_button.clicked.connect(self._go_to_previous_month)
        self.month_label = QLabel()
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.month_label.setStyleSheet("QLabel { border: 1px solid gray; border-radius: 4px; padding: 4px; }")
        self.month_label.mousePressEvent = self._show_calendar_picker
        next_button = QPushButton(">")
        next_button.clicked.connect(self._go_to_next_month)
        
        nav_layout.addWidget(prev_button, 0, 0)
        nav_layout.addWidget(self.month_label, 0, 1)
        nav_layout.addWidget(next_button, 0, 2)
        nav_layout.setColumnStretch(1, 1)
        main_layout.addWidget(nav_group)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.table)

    def _add_months(self, source_date, months):
        month = source_date.month - 1 + months
        year = source_date.year + month // 12
        month = month % 12 + 1
        return source_date.replace(year=year, month=month, day=1)

    def _go_to_previous_month(self):
        self.view_date = self._add_months(self.view_date, -1)
        self.update_qa83_view()

    def _go_to_next_month(self):
        self.view_date = self._add_months(self.view_date, 1)
        self.update_qa83_view()

    def _show_calendar_picker(self, event):
        dialog = QDialog(self)
        cal_layout = QVBoxLayout(dialog)
        calendar = QCalendarWidget()
        calendar.setSelectedDate(QDate(self.view_date))
        
        def on_date_selected(qdate):
            self.view_date = qdate.toPython()
            self.update_qa83_view()
            dialog.accept()
        
        calendar.selectionChanged.connect(on_date_selected)
        dialog.exec()

    def _get_month_weeks_map(self, year, month):
        month_calendar = calendar.monthcalendar(year, month)
        week_map = {}
        for week_index, week in enumerate(month_calendar):
            for day in week:
                if day != 0:
                    week_map[day] = week_index
        return week_map, len(month_calendar)
    
    def update_qa83_view(self):
        self.month_label.setText(self.view_date.strftime('%B %Y'))
        month_year_str = self.view_date.strftime('%Y-%m')

        day_to_week_map, num_weeks = self._get_month_weeks_map(self.view_date.year, self.view_date.month)
        
        week_headers = [f"Week {i+1}" for i in range(num_weeks)]
        headers = ["Project Code", "Description"] + week_headers
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        qa83_categories = self.qa83_config.get("qa83_categories", [])
        unique_tasks = self.db.get_unique_tasks_for_month_by_category(month_year_str, qa83_categories)

        self.table.setRowCount(len(unique_tasks))

        for row, (proj_code, html_desc) in enumerate(unique_tasks):
            doc = QTextDocument()
            doc.setHtml(html_desc)
            plain_desc = doc.toPlainText()
            
            # Always populate the first two columns
            self.table.setItem(row, 0, QTableWidgetItem(proj_code))
            self.table.setItem(row, 1, QTableWidgetItem(plain_desc))

            final_progress_str = self.db.get_qa83_final_progress(month_year_str, proj_code, html_desc)
            
            if final_progress_str is None:
                dialog = ProgressInputDialog(proj_code, plain_desc, self)
                if dialog.exec():
                    final_progress_str = dialog.get_value()
                    self.db.set_qa83_final_progress(month_year_str, proj_code, html_desc, final_progress_str)
                else:
                    final_progress_str = "" # User cancelled, treat as empty

            # =====================================================================
            # === MODIFIED SECTION START (Corrected logic for populating weeks) ===
            # =====================================================================

            # This block now handles all cases: recurring, numeric, and empty/cancelled
            if final_progress_str == "-":
                for i in range(num_weeks):
                    item = QTableWidgetItem("-")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, i + 2, item)
                continue # Skip to the next task

            try:
                final_progress = float(final_progress_str)
                is_numeric = True
            except (ValueError, TypeError):
                is_numeric = False # Progress is empty or not a number

            if is_numeric:
                tasks_in_month = self.db.get_task_hours_for_month(month_year_str, proj_code, html_desc)
                weekly_hours = [0.0] * num_weeks
                total_hours = 0.0
                for date_str, start_str, end_str in tasks_in_month:
                    day = datetime.strptime(date_str, '%Y-%m-%d').day
                    week_index = day_to_week_map.get(day)
                    if week_index is not None:
                        duration = (datetime.combine(datetime.min, time.fromisoformat(end_str)) - 
                                    datetime.combine(datetime.min, time.fromisoformat(start_str))).total_seconds() / 3600
                        weekly_hours[week_index] += duration
                        total_hours += duration
                
                cumulative_progress = 0.0
                for i in range(num_weeks):
                    progress_gain = 0.0
                    if total_hours > 0:
                        progress_gain = (weekly_hours[i] / total_hours) * final_progress
                    
                    cumulative_progress += progress_gain
                    
                    if weekly_hours[i] > 0 or (cumulative_progress > 0.01 and sum(weekly_hours[i+1:]) == 0):
                        item = QTableWidgetItem(f"{cumulative_progress:.1f}%")
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.table.setItem(row, i + 2, item)
            # =====================================================================
            # === MODIFIED SECTION END ===
            # =====================================================================
        
        self.table.resizeRowsToContents()