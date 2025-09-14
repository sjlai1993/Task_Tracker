# reminder_settings_window.py

import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFormLayout,
                             QSpinBox, QDoubleSpinBox, QMessageBox, QLabel, 
                             QCheckBox, QComboBox, QGroupBox)

class ReminderSettingsWindow(QDialog):
    CONFIG_FILE = 'config.json'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Reminder Settings")
        self.setMinimumWidth(450)
        self.config = {}

        self.init_ui()
        self._load_settings()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        reminders_group = QGroupBox("Submission & Workload Reminders")
        reminders_layout = QFormLayout(reminders_group)
        
        # =====================================================================
        # === MODIFIED SECTION START (Add new checkbox widget) ===
        # =====================================================================
        self.prev_day_workload_check = QCheckBox("Remind if previous day's hours are unfulfilled")
        reminders_layout.addRow(self.prev_day_workload_check)
        reminders_layout.addRow(QLabel("--- Submission Reminders ---")) # A separator
        # =====================================================================
        # === MODIFIED SECTION END ===
        # =====================================================================

        self.weekly_reminder_check = QCheckBox("Enable weekly timesheet reminder")
        self.weekly_reminder_day = QComboBox()
        self.weekly_reminder_day.addItems(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        
        weekly_layout = QHBoxLayout()
        weekly_layout.addWidget(self.weekly_reminder_check)
        weekly_layout.addWidget(QLabel("on"))
        weekly_layout.addWidget(self.weekly_reminder_day)
        weekly_layout.addStretch()
        reminders_layout.addRow(weekly_layout)

        self.monthly_reminder_check = QCheckBox("Enable monthly claims (QA83/Travel) reminder")
        self.monthly_reminder_day = QSpinBox()
        self.monthly_reminder_day.setRange(1, 28)
        
        monthly_layout = QHBoxLayout()
        monthly_layout.addWidget(self.monthly_reminder_check)
        monthly_layout.addWidget(QLabel("on day"))
        monthly_layout.addWidget(self.monthly_reminder_day)
        monthly_layout.addStretch()
        reminders_layout.addRow(monthly_layout)

        self.monthly_timesheet_check = QCheckBox("Enable monthly timesheet submission reminder")
        self.monthly_timesheet_day = QSpinBox()
        self.monthly_timesheet_day.setRange(1, 28)

        monthly_ts_layout = QHBoxLayout()
        monthly_ts_layout.addWidget(self.monthly_timesheet_check)
        monthly_ts_layout.addWidget(QLabel("on day"))
        monthly_ts_layout.addWidget(self.monthly_timesheet_day)
        monthly_ts_layout.addStretch()
        reminders_layout.addRow(monthly_ts_layout)

        self.reminder_offset_start = QDoubleSpinBox()
        self.reminder_offset_start.setRange(0.0, 4.0)
        self.reminder_offset_start.setSingleStep(0.5)
        self.reminder_offset_start.setSuffix(" hours")
        reminders_layout.addRow("Remind after work start:", self.reminder_offset_start)

        self.reminder_offset_end = QDoubleSpinBox()
        self.reminder_offset_end.setRange(0.0, 4.0)
        self.reminder_offset_end.setSingleStep(0.5)
        self.reminder_offset_end.setSuffix(" hours")
        reminders_layout.addRow("Remind before work end:", self.reminder_offset_end)

        main_layout.addWidget(reminders_group)
        
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
            
            reminders_cfg = self.config.get('reminders', {})
            # =====================================================================
            # === MODIFIED SECTION START (Load new setting) ===
            # =====================================================================
            self.prev_day_workload_check.setChecked(reminders_cfg.get('previous_day_workload_enabled', True))
            # =====================================================================
            # === MODIFIED SECTION END ===
            # =====================================================================
            self.weekly_reminder_check.setChecked(reminders_cfg.get('weekly_timesheet_enabled', True))
            self.weekly_reminder_day.setCurrentText(reminders_cfg.get('weekly_timesheet_day', "Monday"))
            self.monthly_reminder_check.setChecked(reminders_cfg.get('monthly_claims_enabled', True))
            self.monthly_reminder_day.setValue(reminders_cfg.get('monthly_claims_day', 15))
            self.monthly_timesheet_check.setChecked(reminders_cfg.get('monthly_timesheet_enabled', True))
            self.monthly_timesheet_day.setValue(reminders_cfg.get('monthly_timesheet_day', 28))
            self.reminder_offset_start.setValue(reminders_cfg.get('reminder_offset_hours_start', 1.0))
            self.reminder_offset_end.setValue(reminders_cfg.get('reminder_offset_hours_end', 1.0))
        except (FileNotFoundError, KeyError) as e:
            QMessageBox.critical(self, "Error", f"Could not load {self.CONFIG_FILE}: {e}")
            self.close()

    def _save_settings(self):
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            QMessageBox.critical(self, "Error", f"Could not read {self.CONFIG_FILE}. Cannot save.")
            return

        self.config['reminders'] = {
            # =====================================================================
            # === MODIFIED SECTION START (Save new setting) ===
            # =====================================================================
            'previous_day_workload_enabled': self.prev_day_workload_check.isChecked(),
            # =====================================================================
            # === MODIFIED SECTION END ===
            # =====================================================================
            'weekly_timesheet_enabled': self.weekly_reminder_check.isChecked(),
            'weekly_timesheet_day': self.weekly_reminder_day.currentText(),
            'monthly_claims_enabled': self.monthly_reminder_check.isChecked(),
            'monthly_claims_day': self.monthly_reminder_day.value(),
            'monthly_timesheet_enabled': self.monthly_timesheet_check.isChecked(),
            'monthly_timesheet_day': self.monthly_timesheet_day.value(),
            'reminder_offset_hours_start': self.reminder_offset_start.value(),
            'reminder_offset_hours_end': self.reminder_offset_end.value()
        }
        
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            QMessageBox.information(self, "Success", "Reminder settings saved successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save {self.CONFIG_FILE}: {e}")