# settings_window.py

import json
from datetime import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFormLayout,
                             QSpinBox, QDoubleSpinBox, QTimeEdit, QTextEdit, QMessageBox,
                             QLabel, QCheckBox)
from PySide6.QtCore import QTime

class SettingsWindow(QDialog):
    CONFIG_FILE = 'config.json'
    HOLIDAY_FILE = 'holiday.json'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit General Configuration")
        self.setMinimumWidth(500)
        self.config = {}

        self.init_ui()
        self._load_settings()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.start_lower = QTimeEdit()
        self.start_upper = QTimeEdit()
        self.daily_hours = QDoubleSpinBox()
        self.lunch_start = QTimeEdit()
        self.lunch_end = QTimeEdit()
        self.popup_interval = QSpinBox()
        self.popup_autoclose = QSpinBox()
        self.schedule_notify_checkbox = QCheckBox("Show daily schedule as a notification on startup")
        # =====================================================================
        # === MODIFIED SECTION START (Add max backups widget) ===
        # =====================================================================
        self.max_backups = QSpinBox()
        # =====================================================================
        # === MODIFIED SECTION END ===
        # =====================================================================
        self.holidays = QTextEdit()
        self.categories = QTextEdit()
        self.side_description = QTextEdit()

        day_checkbox_layout = QHBoxLayout()
        self.day_checkboxes = []
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day in days_of_week:
            checkbox = QCheckBox(day)
            self.day_checkboxes.append(checkbox)
            day_checkbox_layout.addWidget(checkbox)
        day_checkbox_layout.addStretch()

        self.daily_hours.setRange(1.0, 16.0); self.daily_hours.setSingleStep(0.5)
        self.popup_interval.setRange(5, 120)
        self.popup_autoclose.setRange(0, 60); self.popup_autoclose.setSuffix(" minutes (0 to disable)")
        # =====================================================================
        # === MODIFIED SECTION START (Configure max backups widget) ===
        # =====================================================================
        self.max_backups.setRange(1, 52) # From 1 backup to a full year's worth
        self.max_backups.setToolTip("The number of weekly backup files to keep.")
        # =====================================================================
        # === MODIFIED SECTION END ===
        # =====================================================================
        self.holidays.setPlaceholderText("One date per line, e.g., 2025-12-25")
        self.holidays.setFixedHeight(100)
        self.categories.setPlaceholderText("One category per line")
        self.categories.setFixedHeight(100)
        self.side_description.setPlaceholderText("One line per entry for the 'Additional Codes' popup.")
        self.side_description.setFixedHeight(100)
        
        start_time_layout = QHBoxLayout()
        start_time_layout.addWidget(self.start_lower); start_time_layout.addWidget(QLabel("to")); start_time_layout.addWidget(self.start_upper)
        form_layout.addRow("Flexible Start Time:", start_time_layout)
        form_layout.addRow("Daily Working Hours:", self.daily_hours)
        lunch_time_layout = QHBoxLayout()
        lunch_time_layout.addWidget(self.lunch_start); lunch_time_layout.addWidget(QLabel("to")); lunch_time_layout.addWidget(self.lunch_end)
        form_layout.addRow("Lunch Hour:", lunch_time_layout)
        form_layout.addRow("Popup Interval (minutes):", self.popup_interval)
        form_layout.addRow("Popup Autoclose:", self.popup_autoclose)
        form_layout.addRow("", self.schedule_notify_checkbox)
        # =====================================================================
        # === MODIFIED SECTION START (Add max backups widget to layout) ===
        # =====================================================================
        form_layout.addRow("Max DB Backups to Keep:", self.max_backups)
        # =====================================================================
        # === MODIFIED SECTION END ===
        # =====================================================================
        form_layout.addRow("Working Days:", day_checkbox_layout)
        form_layout.addRow("Holidays (YYYY-MM-DD):", self.holidays)
        form_layout.addRow("Project Categories:", self.categories)
        form_layout.addRow("Additional Codes:", self.side_description)
        main_layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        save_button = QPushButton("Save")
        save_button.setDefault(True)
        save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(save_button)
        main_layout.addLayout(button_layout)

        self.setFixedSize(self.sizeHint())

    def _load_settings(self):
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                self.config = json.load(f)
            
            with open(self.HOLIDAY_FILE, 'r') as f:
                holiday_data = json.load(f)
                holidays_list = holiday_data.get("holidays", [])

            self.start_lower.setTime(QTime.fromString(self.config['work_start_time_flexible']['lower'], "HH:mm:ss"))
            self.start_upper.setTime(QTime.fromString(self.config['work_start_time_flexible']['upper'], "HH:mm:ss"))
            self.daily_hours.setValue(self.config['daily_working_hours'])
            self.lunch_start.setTime(QTime.fromString(self.config['lunch_hour']['start'], "HH:mm:ss"))
            self.lunch_end.setTime(QTime.fromString(self.config['lunch_hour']['end'], "HH:mm:ss"))
            self.popup_interval.setValue(self.config['popup_interval_minutes'])
            self.popup_autoclose.setValue(self.config.get('popup_autoclose_minutes', 2))
            self.schedule_notify_checkbox.setChecked(self.config.get('show_schedule_notification', True))
            # =====================================================================
            # === MODIFIED SECTION START (Load max backups value) ===
            # =====================================================================
            self.max_backups.setValue(self.config.get('max_backups_to_keep', 4))
            # =====================================================================
            # === MODIFIED SECTION END ===
            # =====================================================================
            
            saved_working_days = self.config.get('working_days', [])
            for checkbox in self.day_checkboxes:
                checkbox.setChecked(checkbox.text() in saved_working_days)
            self.holidays.setText("\n".join(holidays_list))
            self.categories.setText("\n".join(self.config['project_categories']))
            self.side_description.setText("\n".join(self.config.get('side_description', [])))
        except (FileNotFoundError, KeyError) as e:
            QMessageBox.critical(self, "Error", f"Could not load configuration files: {e}")
            self.close()

    def _save_settings(self):
        holiday_lines = self.holidays.toPlainText().splitlines()
        valid_holidays = []
        for line in [line.strip() for line in holiday_lines if line.strip()]:
            try:
                datetime.strptime(line, "%Y-%m-%d")
                valid_holidays.append(line)
            except ValueError:
                QMessageBox.warning(self, "Invalid Date Format", f"Invalid holiday date '{line}'. Please use YYYY-MM-DD.")
                return

        work_start_lower = self.start_lower.time()
        lunch_start = self.lunch_start.time()
        if lunch_start <= work_start_lower:
            QMessageBox.warning(self, "Invalid Time Configuration", "Lunch Hour must start after the Flexible Start Time.")
            return

        self.config['work_start_time_flexible']['lower'] = work_start_lower.toString("HH:mm:ss")
        self.config['work_start_time_flexible']['upper'] = self.start_upper.time().toString("HH:mm:ss")
        self.config['daily_working_hours'] = self.daily_hours.value()
        self.config['lunch_hour']['start'] = lunch_start.toString("HH:mm:ss")
        self.config['lunch_hour']['end'] = self.lunch_end.time().toString("HH:mm:ss")
        self.config['popup_interval_minutes'] = self.popup_interval.value()
        self.config['popup_autoclose_minutes'] = self.popup_autoclose.value()
        self.config['show_schedule_notification'] = self.schedule_notify_checkbox.isChecked()
        # =====================================================================
        # === MODIFIED SECTION START (Save max backups value) ===
        # =====================================================================
        self.config['max_backups_to_keep'] = self.max_backups.value()
        # =====================================================================
        # === MODIFIED SECTION END ===
        # =====================================================================
        self.config['working_days'] = [cb.text() for cb in self.day_checkboxes if cb.isChecked()]
        
        def text_to_list(widget):
            return [line.strip() for line in widget.toPlainText().splitlines() if line.strip()]

        self.config['project_categories'] = text_to_list(self.categories)
        self.config['side_description'] = self.side_description.toPlainText().splitlines()
        
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            with open(self.HOLIDAY_FILE, 'w') as f:
                json.dump({"holidays": sorted(list(set(valid_holidays)))}, f, indent=2)

            QMessageBox.information(self, "Success", "Configuration saved successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save configuration files: {e}")