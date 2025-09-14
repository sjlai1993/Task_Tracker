# travel_tab.py

import json
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTableWidgetItem, QDialog,
                             QGroupBox, QGridLayout, QCalendarWidget, QHeaderView,
                             QAbstractItemView)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QTextDocument
from datetime import datetime, timedelta, time
from datetime import datetime, timedelta
from timesheet_tab import CopyableTableWidget

class TravelTab(QWidget):
    CONFIG_FILE = 'travel.json'

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.view_date = datetime.now().date()
        self.travel_config = self._load_config()
        
        self.init_ui()
        self.update_travel_view()

    def _load_config(self):
        if not os.path.exists(self.CONFIG_FILE):
            default_config = {"travel_categories": []}
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
        
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"travel_categories": []}

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        nav_group = QGroupBox("Month Navigation")
        nav_layout = QGridLayout(nav_group)
        
        prev_button = QPushButton("<")
        prev_button.setToolTip("Previous Month")
        prev_button.clicked.connect(self._go_to_previous_month)
        
        self.month_label = QLabel()
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.month_label.setStyleSheet("QLabel { border: 1px solid gray; border-radius: 4px; padding: 4px; }")
        self.month_label.setToolTip("Click to select a date")
        self.month_label.mousePressEvent = self._show_calendar_picker
        
        next_button = QPushButton(">")
        next_button.setToolTip("Next Month")
        next_button.clicked.connect(self._go_to_next_month)
        
        nav_layout.addWidget(prev_button, 0, 0)
        nav_layout.addWidget(self.month_label, 0, 1)
        nav_layout.addWidget(next_button, 0, 2)
        nav_layout.setColumnStretch(1, 1)
        
        main_layout.addWidget(nav_group)

        self.table = CopyableTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Date", "Time", "Project Code", "Description"])
        
        self.table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #447ED0;
                color: white;
            }
        """)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setHighlightSections(False)

        main_layout.addWidget(self.table)
    
    def _add_months(self, source_date, months):
        month = source_date.month - 1 + months
        year = source_date.year + month // 12
        month = month % 12 + 1
        return source_date.replace(year=year, month=month, day=1)

    def _go_to_previous_month(self):
        self.view_date = self._add_months(self.view_date, -1)
        self.update_travel_view()

    def _go_to_next_month(self):
        self.view_date = self._add_months(self.view_date, 1)
        self.update_travel_view()

    def _show_calendar_picker(self, event):
        calendar_dialog = QDialog(self)
        calendar_dialog.setWindowTitle("Select Date")
        cal_layout = QVBoxLayout(calendar_dialog)
        calendar = QCalendarWidget()
        calendar.setSelectedDate(QDate(self.view_date))
        
        def on_date_selected():
            self.view_date = calendar.selectedDate().toPython()
            self.update_travel_view()
            calendar_dialog.accept()

        calendar.selectionChanged.connect(on_date_selected)
        cal_layout.addWidget(calendar)
        calendar_dialog.exec()

    def _group_consecutive_tasks(self, tasks):
        """Groups consecutive tasks with the same date, project, and description."""
        if not tasks:
            return []

        grouped_tasks = []
        # The tasks are already sorted by date and start time from the DB query.
        current_group = [tasks[0]]

        for i in range(1, len(tasks)):
            prev_task = current_group[-1]
            current_task = tasks[i]

            # Grouping criteria: same day, same project code, same description
            is_same_group = (
                current_task[1] == prev_task[1] and  # task_date
                current_task[4] == prev_task[4] and  # project_code
                current_task[5] == prev_task[5]      # description
            )

            # Consecutiveness criteria: current task starts exactly where the previous one ended
            try:
                prev_end_time = time.fromisoformat(prev_task[3])
                current_start_time = time.fromisoformat(current_task[2])
                is_consecutive = (prev_end_time == current_start_time)
            except ValueError:
                is_consecutive = False

            if is_same_group and is_consecutive:
                current_group.append(current_task)
            else:
                grouped_tasks.append(current_group[0]) # Add the representative task of the completed group
                current_group = [current_task]
        
        grouped_tasks.append(current_group[0]) # Add the last group's representative task
        return grouped_tasks

    def update_travel_view(self):
        self.month_label.setText(self.view_date.strftime('%B %Y'))

        start_of_month = self.view_date.replace(day=1)
        next_month = self._add_months(start_of_month, 1)
        end_of_month = next_month - timedelta(days=1)
        
        travel_tasks = []
        travel_categories_set = set(self.travel_config.get("travel_categories", []))

        current_date = start_of_month
        while current_date <= end_of_month:
            date_str = current_date.strftime("%Y-%m-%d")
            tasks_for_day = self.db.get_tasks_for_date(date_str)
            
            for task in tasks_for_day:
                task_categories = set(cat.strip() for cat in task[6].split(','))
                if not travel_categories_set.isdisjoint(task_categories):
                    travel_tasks.append(task)
            
            current_date += timedelta(days=1)

        # Group the collected tasks before displaying them
        display_tasks = self._group_consecutive_tasks(travel_tasks)

        self.table.setRowCount(len(display_tasks))
        for row, task in enumerate(display_tasks):
            task_date_obj = datetime.strptime(task[1], "%Y-%m-%d").date()
            display_date = task_date_obj.strftime("%d/%m/%Y (%a)")
            
            start_time_obj = time.fromisoformat(task[2])
            display_time = start_time_obj.strftime("%H:%M")

            doc = QTextDocument()
            doc.setHtml(task[5])
            plain_text_description = doc.toPlainText()
            
            date_item = QTableWidgetItem(display_date)
            time_item = QTableWidgetItem(display_time)
            project_item = QTableWidgetItem(task[4])
            description_item = QTableWidgetItem(plain_text_description)
            
            self.table.setItem(row, 0, date_item)
            self.table.setItem(row, 1, time_item)
            self.table.setItem(row, 2, project_item)
            self.table.setItem(row, 3, description_item)

        self.table.resizeRowsToContents()