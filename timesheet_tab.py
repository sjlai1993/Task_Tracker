# timesheet_tab.py

import json
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTableWidget, QTableWidgetItem, QDialog,

                             QGroupBox, QGridLayout, QCalendarWidget, QHeaderView,
                             QAbstractItemView, QStyledItemDelegate, QStyle, QApplication, QMenu)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QBrush, QFont, QKeySequence, QKeyEvent
from datetime import datetime, timedelta, time

class CopyableTableWidget(QTableWidget):
    """A QTableWidget subclass that supports copying selected cells to the clipboard."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def copy_selection(self):
        """Copies the content of the selected cells to the clipboard in a tab-separated format."""
        selected = self.selectedRanges()
        if not selected:
            return

        first_range = selected[0]
        rows = []
        for r in range(first_range.topRow(), first_range.bottomRow() + 1):
            row_data = []
            for c in range(first_range.leftColumn(), first_range.rightColumn() + 1):
                item = self.item(r, c)
                row_data.append(item.text() if item else "")
            rows.append("\t".join(row_data))
        
        QApplication.clipboard().setText("\n".join(rows))

    def keyPressEvent(self, event: QKeyEvent):
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selection()
        else:
            super().keyPressEvent(event)
            
    def contextMenuEvent(self, event):
        """Creates and shows a context menu on right-click."""
        menu = QMenu(self)
        
        copy_action = menu.addAction("Copy (Ctrl+C)")
        copy_action.triggered.connect(self.copy_selection)
        
        if not self.selectedRanges():
            copy_action.setEnabled(False)
            
        menu.exec(event.globalPos())

class CustomCellDelegate(QStyledItemDelegate):
    """A custom delegate to handle special drawing for all cells in timesheet."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.weekend_color = QColor("#88E788")
        self.weekend_selected_color = self.weekend_color.darker(115)
        self.weekday_selected_color = QColor("#447ED0")
        self.holiday_color = QColor("#90D5FF")
        self.holiday_selected_color = self.holiday_color.darker(115)
        
        self.holidays = set()
        self.week_dates = []

    def set_view_data(self, week_dates, holidays):
        self.week_dates = week_dates
        self.holidays = holidays

    def paint(self, painter, option, index):
        is_holiday = False
        is_weekend = False

        if index.column() > 0:
            current_date = self.week_dates[index.column() - 1]
            is_holiday = current_date in self.holidays
            is_weekend = current_date.weekday() in [5, 6]

        if option.state & QStyle.StateFlag.State_Selected:
            bg_color = self.weekend_selected_color if is_weekend else \
                       self.holiday_selected_color if is_holiday else \
                       self.weekday_selected_color
        else:
            bg_color = self.weekend_color if is_weekend else \
                       self.holiday_color if is_holiday else \
                       option.palette.base().color()

        painter.fillRect(option.rect, bg_color)

        if is_weekend or is_holiday:
            option.palette.setColor(option.palette.ColorRole.Text, Qt.GlobalColor.black)

        super().paint(painter, option, index)


class TimesheetTab(QWidget):
    CONFIG_FILE = 'timesheet.json'

    def __init__(self, parent, db, main_config):
        super().__init__(parent)
        self.db = db
        self.main_config = main_config
        self.view_date = datetime.now().date()
        self.timesheet_config = self._load_config()
        
        self.init_ui()
        self.update_timesheet_view()

    def _load_config(self):
        if not os.path.exists(self.CONFIG_FILE):
            default_config = {"row_configurations": []}
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
        
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"row_configurations": []}

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        nav_group = QGroupBox("Week Navigation")
        nav_layout = QGridLayout(nav_group)
        
        prev_button = QPushButton("<")
        prev_button.setToolTip("Previous Week")
        prev_button.clicked.connect(self._go_to_previous_week)
        
        self.week_label = QLabel()
        self.week_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.week_label.setStyleSheet("QLabel { border: 1px solid gray; border-radius: 4px; padding: 4px; }")
        self.week_label.setToolTip("Click to select a date")
        self.week_label.mousePressEvent = self._show_calendar_picker
        
        next_button = QPushButton(">")
        next_button.setToolTip("Next Week")
        next_button.clicked.connect(self._go_to_next_week)
        
        nav_layout.addWidget(prev_button, 0, 0)
        nav_layout.addWidget(self.week_label, 0, 1)
        nav_layout.addWidget(next_button, 0, 2)
        nav_layout.setColumnStretch(1, 1)
        
        main_layout.addWidget(nav_group)

        self.table = CopyableTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.delegate = CustomCellDelegate(self)
        self.table.setItemDelegate(self.delegate)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setHighlightSections(False)

        main_layout.addWidget(self.table)

    def _get_week_boundaries(self, date_obj):
        days_to_saturday = (date_obj.weekday() + 2) % 7
        start_of_week = date_obj - timedelta(days=days_to_saturday)
        end_of_week = start_of_week + timedelta(days=6)
        return start_of_week, end_of_week

    def _go_to_previous_week(self):
        self.view_date -= timedelta(weeks=1)
        self.update_timesheet_view()

    def _go_to_next_week(self):
        self.view_date += timedelta(weeks=1)
        self.update_timesheet_view()

    def _show_calendar_picker(self, event):
        calendar_dialog = QDialog(self)
        calendar_dialog.setWindowTitle("Select Date")
        cal_layout = QVBoxLayout(calendar_dialog)
        calendar = QCalendarWidget()
        calendar.setSelectedDate(QDate(self.view_date))
        
        def on_date_selected():
            self.view_date = calendar.selectedDate().toPython()
            self.update_timesheet_view()
            calendar_dialog.accept()

        calendar.selectionChanged.connect(on_date_selected)
        cal_layout.addWidget(calendar)
        calendar_dialog.exec()

    def update_timesheet_view(self):
        start_of_week, end_of_week = self._get_week_boundaries(self.view_date)
        self.week_label.setText(
            f"{start_of_week.strftime('%d/%m/%Y')} to {end_of_week.strftime('%d/%m/%Y')}"
        )
        
        week_dates = [start_of_week + timedelta(days=i) for i in range(7)]
        headers = ["Project"] + [d.strftime('%A\n(%d/%m)') for d in week_dates]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        official_holidays = set(self.main_config.get("holidays", []))
        working_days_names = self.main_config.get("working_days", [])
        day_name_to_weekday = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
        working_day_numbers = {day_name_to_weekday[name] for name in working_days_names}
        
        actual_holidays_this_week = set()
        for date_obj in week_dates:
            if date_obj.strftime("%Y-%m-%d") in official_holidays:
                actual_holidays_this_week.add(date_obj)
                if date_obj.weekday() == 6:
                    replacement_date = date_obj + timedelta(days=1)
                    while True:
                        if replacement_date.weekday() in working_day_numbers:
                            actual_holidays_this_week.add(replacement_date)
                            break
                        replacement_date += timedelta(days=1)
        
        self.delegate.set_view_data(week_dates, actual_holidays_this_week)

        project_hours = {}
        for i, current_date in enumerate(week_dates):
            tasks = self.db.get_tasks_for_date(current_date.strftime("%Y-%m-%d"))
            for task in tasks:
                proj_code = task[4]
                try:
                    start_t = time.fromisoformat(task[2])
                    end_t = time.fromisoformat(task[3])
                    duration = (datetime.combine(current_date, end_t) - 
                                datetime.combine(current_date, start_t)).total_seconds() / 3600
                    if proj_code not in project_hours:
                        project_hours[proj_code] = [0.0] * 7
                    project_hours[proj_code][i] += duration
                except ValueError:
                    continue

        row_configs = self.timesheet_config.get("row_configurations", [])
        holiday_project_code = next((c.get("project_code") for c in row_configs if c.get("is_holiday_code")), None)

        if holiday_project_code:
            if holiday_project_code not in project_hours:
                project_hours[holiday_project_code] = [0.0] * 7
            for i, date_obj in enumerate(week_dates):
                if date_obj in actual_holidays_this_week and date_obj.weekday() not in [5, 6]:
                    work_times_row = self.db.get_work_times_for_date(date_obj.strftime("%Y-%m-%d"))
                    hours_for_day = work_times_row[4] if work_times_row else self.main_config.get("daily_working_hours", 8.0)
                    project_hours[holiday_project_code][i] = hours_for_day
        
        prefix_projects, suffix_projects, display_map = [], [], {}
        for item in row_configs:
            code = item.get("project_code")
            if not code: continue
            display_map[code] = item.get("display_name", code)
            if item.get("is_prefix"):
                prefix_projects.append(code)
            elif item.get("is_suffix"):
                suffix_projects.append(code)

        projects_with_hours = set(project_hours.keys())
        prefix_set, suffix_set = set(prefix_projects), set(suffix_projects)
        other_projects = sorted(list(projects_with_hours - prefix_set - suffix_set))
        filtered_suffix_projects = [code for code in suffix_projects if code in projects_with_hours]
        final_project_order = prefix_projects + other_projects + filtered_suffix_projects
        
        self.table.setRowCount(len(final_project_order))

        for row, proj_code in enumerate(final_project_order):
            display_name = display_map.get(proj_code, proj_code)
            proj_item = QTableWidgetItem(display_name)
            self.table.setItem(row, 0, proj_item)
            hours_data = project_hours.get(proj_code, [0.0] * 7)
            for col, hours in enumerate(hours_data, start=1):
                hours_item = QTableWidgetItem()
                if hours > 0.005:
                    hours_item.setText(f"{hours:.2f}")
                hours_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, hours_item)

        num_project_rows = len(final_project_order)
        self.table.setRowCount(num_project_rows + 1)
        total_row_index = num_project_rows

        bold_font = QFont()
        bold_font.setBold(True)

        total_label_item = QTableWidgetItem("Total")
        total_label_item.setFont(bold_font)
        self.table.setItem(total_row_index, 0, total_label_item)

        for col in range(1, self.table.columnCount()):
            column_total = 0.0
            for row in range(num_project_rows):
                item = self.table.item(row, col)
                if item and item.text():
                    try:
                        column_total += float(item.text())
                    except ValueError:
                        pass

            total_item = QTableWidgetItem()
            if column_total > 0.005:
                total_item.setText(f"{column_total:.2f}")
            
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            total_item.setFont(bold_font)

            current_date = week_dates[col - 1]
            if current_date.weekday() not in [5, 6]:
                work_times_row = self.db.get_work_times_for_date(current_date.strftime("%Y-%m-%d"))
                required_hours = work_times_row[4] if work_times_row else self.main_config.get("daily_working_hours", 8.0)
                
                if column_total < required_hours and current_date not in actual_holidays_this_week:
                    total_item.setForeground(QColor("red"))

            self.table.setItem(total_row_index, col, total_item)

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()