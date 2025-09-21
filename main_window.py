# main_window.py

import sys
import json
import os
import calendar
import shutil
from datetime import datetime, time, timedelta
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QSystemTrayIcon, QMenu, QMessageBox, QStyle, QDialog,
                             QTabWidget)
from PySide6.QtCore import QTimer, QTime, QDate, Qt
from PySide6.QtGui import QIcon, QAction
from database import Database
from popup import Popup
from settings_window import SettingsWindow
from reminder_settings_window import ReminderSettingsWindow
from about_window import AboutWindow
from general_tab import GeneralTab
from timesheet_tab import TimesheetTab
from travel_tab import TravelTab
from qa83_tab import QA83Tab

class MainWindow(QMainWindow):
    APP_VERSION = "0.0.1"
    HOLIDAY_FILE = 'holiday.json'
    DB_FILE = 'task_tracker.db'
    BACKUP_DIR = 'backups'
    app_icon = 'icon.ico'

    def __init__(self, app_icon=None):
        super().__init__()
        self.db = Database(self.DB_FILE)
        self.config = {}
        self.holidays = []
        self.reload_config()
        self.popup_schedule = []
        
        # If an app_icon object is provided, use it. Otherwise, try to load it from the path.
        # This ensures that even if the initial load in main.py fails and provides a generic icon,
        # the fallback notification will still use the correct QIcon if the file exists.
        self.app_icon = app_icon
        if self.app_icon.isNull():
            self.app_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserStop)
            self.app_icon = app_icon

        self.init_ui()
        self.create_tray_icon()
        self.general_tab.update_task_view()
        self.check_version()
        QTimer.singleShot(100, self.update_daily_working_times)
        QTimer.singleShot(1000, self.check_previous_day_workload)
        
        self.wake_check_timer = QTimer(self)
        self.wake_check_timer.timeout.connect(self.check_for_wake_up)
        self.last_check_time = datetime.now()
        self.wake_check_timer.start(5 * 60 * 1000)

        self.backup_check_timer = QTimer(self)
        self.backup_check_timer.timeout.connect(self._handle_weekly_backup)
        # Check on startup, then every hour
        QTimer.singleShot(2000, self._handle_weekly_backup) 
        self.backup_check_timer.start(60 * 60 * 1000) # 1 hour

    def _handle_weekly_backup(self):
        """Checks if a backup is needed and performs it."""
        now = datetime.now()
        # Monday is weekday 0
        if now.weekday() != 0:
            return

        today_str = now.strftime('%Y-%m-%d')
        last_backup_date = self.db.get_setting('last_backup_date')

        if last_backup_date == today_str:
            return # Backup for this Monday already done

        try:
            os.makedirs(self.BACKUP_DIR, exist_ok=True)
            backup_filename = f"task_tracker_backup_{today_str}.db"
            backup_path = os.path.join(self.BACKUP_DIR, backup_filename)

            shutil.copy2(self.DB_FILE, backup_path)
            
            self.db.set_setting('last_backup_date', today_str)
            self.tray_icon.showMessage(
                "Backup Successful",
                f"Database backed up to:\n{backup_path}",
                QSystemTrayIcon.MessageIcon.Information,
                10000
            )
            self._cleanup_old_backups()
        except Exception as e:
            self.tray_icon.showMessage(
                "Backup Failed",
                f"Could not back up the database.\nError: {e}",
                QSystemTrayIcon.MessageIcon.Warning,
                15000
            )

    def _cleanup_old_backups(self):
        """Removes the oldest backup files if the count exceeds the configured limit."""
        max_backups = self.config.get('max_backups_to_keep', 4)
        
        if not os.path.isdir(self.BACKUP_DIR):
            return

        try:
            backup_files = [
                f for f in os.listdir(self.BACKUP_DIR)
                if f.startswith('task_tracker_backup_') and f.endswith('.db')
            ]
            
            backup_files.sort()

            if len(backup_files) > max_backups:
                num_to_delete = len(backup_files) - max_backups
                files_to_delete = backup_files[:num_to_delete]

                for f in files_to_delete:
                    os.remove(os.path.join(self.BACKUP_DIR, f))
        except Exception as e:
             self.tray_icon.showMessage(
                "Backup Cleanup Failed",
                f"Could not remove old backups.\nError: {e}",
                QSystemTrayIcon.MessageIcon.Warning,
                15000
            )

    def reload_holidays(self):
        try:
            with open(self.HOLIDAY_FILE, 'r') as f:
                holiday_data = json.load(f)
                self.holidays = list(set(holiday_data.get("holidays", [])))
        except (FileNotFoundError, json.JSONDecodeError):
            self.holidays = []
        self.config['holidays'] = self.holidays

    def reload_config(self):
        with open('config.json', 'r') as f:
            self.config = json.load(f)
        self.reload_holidays()

    def init_ui(self):
        self.setWindowIcon(self.app_icon)
        self.setWindowTitle("Task Tracker")
        self.setMinimumSize(540, 400)
        
        self.tabs = QTabWidget()
        self.general_tab = GeneralTab(parent=self, db=self.db, config=self.config)
        self.timesheet_tab = TimesheetTab(parent=self, db=self.db, main_config=self.config)
        self.travel_tab = TravelTab(parent=self, db=self.db)
        self.qa83_tab = QA83Tab(parent=self, db=self.db)
        
        menu_bar = self.menuBar()
        style = self.style()
        file_menu = menu_bar.addMenu("&File")
        exit_icon = style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
        exit_action = QAction(exit_icon, "&Exit", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(exit_action)
        
        settings_menu = menu_bar.addMenu("&Settings")
        settings_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        edit_config_action = QAction(settings_icon, "General Configuration...", self)
        edit_config_action.triggered.connect(self._open_settings_window)
        settings_menu.addAction(edit_config_action)
        
        reminder_icon = style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion)
        edit_reminders_action = QAction(reminder_icon, "Reminder Settings...", self)
        edit_reminders_action.triggered.connect(self._open_reminder_settings_window)
        settings_menu.addAction(edit_reminders_action)

        settings_menu.addSeparator()
        
        qa83_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)
        self.qa83_settings_action = QAction(qa83_icon, "QA83 Report Settings...", self)
        self.qa83_settings_action.triggered.connect(self.qa83_tab._open_settings)
        settings_menu.addAction(self.qa83_settings_action)

        about_menu = menu_bar.addMenu("&About")
        about_icon = style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        about_action = QAction(about_icon, "&About Task Tracker", self)
        about_action.triggered.connect(self._show_about_dialog)
        about_menu.addAction(about_action)

        debug_menu = menu_bar.addMenu("&Debug")
        test_popup_action = QAction("Test Timed Popup", self)
        test_popup_action.triggered.connect(self._debug_test_popup)
        debug_menu.addAction(test_popup_action)

        show_schedule_action = QAction("Show Today's Schedule", self)
        show_schedule_action.triggered.connect(self._debug_show_schedule)
        debug_menu.addAction(show_schedule_action)

        self.setCentralWidget(self.tabs)
        
        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.timesheet_tab, "Timesheet")
        self.tabs.addTab(self.travel_tab, "Travel")
        self.tabs.addTab(self.qa83_tab, "QA83")
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.on_tab_changed(self.tabs.currentIndex())

    def on_tab_changed(self, index):
        """Handler for when the user switches tabs."""
        current_widget = self.tabs.widget(index)
        
        if current_widget == self.qa83_tab:
            self.qa83_tab.handle_tab_focus()
        elif current_widget == self.general_tab:
            self.general_tab.update_task_view()
        elif current_widget == self.timesheet_tab:
            self.timesheet_tab.update_timesheet_view()
        elif current_widget == self.travel_tab:
            self.travel_tab.update_travel_view()
    
    def _refresh_all_tabs(self):
        """Refreshes the data views in all relevant tabs."""
        self.general_tab.update_task_view()
        self.timesheet_tab.update_timesheet_view()
        self.travel_tab.update_travel_view()
        self.qa83_tab.update_qa83_view()

    def _show_about_dialog(self):
        about_dialog = AboutWindow(version=self.APP_VERSION, parent=self)
        about_dialog.exec()

    def check_version(self):
        stored_version = self.db.get_setting("app_version")
        if stored_version is None:
            self.db.set_setting("app_version", self.APP_VERSION)
        elif stored_version != self.APP_VERSION:
            self.db.set_setting("app_version", self.APP_VERSION)

    def _open_settings_window(self):
        settings_dialog = SettingsWindow(self)
        if settings_dialog.exec():
            self.reload_config()
            self.general_tab.config = self.config
            self.general_tab.update_task_view()
            QMessageBox.information(self, "Settings Updated", "General settings and holidays saved. Changes are now active.")
    
    def _open_reminder_settings_window(self):
        reminder_dialog = ReminderSettingsWindow(self)
        if reminder_dialog.exec():
            self.reload_config()
            QMessageBox.information(self, "Settings Updated", "Reminder settings saved. Changes will take effect on the next applicable day.")
    
    def _debug_test_popup(self):
        popup_date = self.general_tab.view_date
        popup_start_time = self.determine_start_time_for_date(popup_date).toPython()
        lookup_dt = datetime.combine(popup_date, popup_start_time)
        previous_task = self.db.get_task_before(lookup_dt)
        popup = Popup(self.db, previous_task, self.config, parent=self) 
        start_time = self.determine_start_time_for_date(self.general_tab.view_date)
        popup.start_time_edit.setTime(start_time)
        if popup.exec() == QDialog.DialogCode.Accepted:
            self.general_tab.update_task_view()

    def _debug_show_schedule(self):
        """Displays the current day's generated popup schedule in a message box."""
        if not self.popup_schedule:
            QMessageBox.information(self, "Debug: Popup Schedule", "No popup schedule has been generated for today.")
            return

        now = datetime.now()
        schedule_items = []
        for t in self.popup_schedule:
            if t < now:
                schedule_items.append(f"<i>{t.strftime('%H:%M')} (past)</i>")
            else:
                schedule_items.append(f"<b>{t.strftime('%H:%M')}</b>")

        schedule_str = " | ".join(schedule_items)        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Debug: Popup Schedule")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(f"The following popups are scheduled for today:<br><br>{schedule_str}")
        msg_box.exec()
    
    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        self.tray_icon.setToolTip("Task Tracker")
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_and_raise)
        tray_menu.addAction(show_action)
        add_task_action = QAction("Add task", self)
        add_task_action.triggered.connect(self.manual_popup)
        tray_menu.addAction(add_task_action)
        tray_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_and_raise()

    def show_and_raise(self):
        self.showNormal(); self.activateWindow()

    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange and self.windowState() & Qt.WindowState.WindowMinimized:
            self.hide()
        super().changeEvent(event)

    def closeEvent(self, event):
        notification_shown = self.db.get_setting("minimize_notification_shown")
        if not notification_shown or notification_shown != "true":
            self.tray_icon.showMessage("Minimized", "Task Tracker is running in the system tray.", QSystemTrayIcon.MessageIcon.Information, 10000)
            self.db.set_setting("minimize_notification_shown", "true")
        event.ignore(); self.hide()
        
    def is_working_day(self, date_obj):
        if date_obj.strftime('%A') not in self.config.get('working_days', []):
            return False
        if date_obj.strftime('%Y-%m-%d') in self.config.get('holidays', []):
            return False
        return True

    def _schedule_notification(self, trigger_time, title, message):
        now = datetime.now()
        if trigger_time > now:
            delay_ms = (trigger_time - now).total_seconds() * 1000
            QTimer.singleShot(int(delay_ms), lambda: self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 20000))

    def update_daily_working_times(self):
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")
        if not self.is_working_day(today.date()): return
        if self.db.get_work_times_for_date(today_str) is not None:
            self.schedule_popups_for_the_day()
            return
        
        now_time = today.time().replace(second=0, microsecond=0)
        lower_bound = time.fromisoformat(self.config['work_start_time_flexible']['lower'])
        upper_bound = time.fromisoformat(self.config['work_start_time_flexible']['upper'])
        effective_start_time = max(min(now_time, upper_bound), lower_bound)
        settings_snapshot = {k: self.config[k] for k in ['work_start_time_flexible', 'daily_working_hours', 'lunch_hour', 'working_days', 'holidays']}
        settings_snapshot['work_start_lower'] = settings_snapshot['work_start_time_flexible']['lower']
        settings_snapshot['work_start_upper'] = settings_snapshot['work_start_time_flexible']['upper']
        settings_snapshot['lunch_start'] = settings_snapshot['lunch_hour']['start']
        settings_snapshot['lunch_end'] = settings_snapshot['lunch_hour']['end']

        effective_start_time_str = effective_start_time.strftime("%H:%M:%S")
        self.db.add_work_times(today_str, effective_start_time_str, settings_snapshot)
        self.schedule_popups_for_the_day()

    def check_for_wake_up(self):
        now = datetime.now()
        if (now - self.last_check_time) > timedelta(minutes=10):
            self.update_daily_working_times()
        self.last_check_time = now

    def schedule_popups_for_the_day(self):
        self.popup_schedule.clear()
        QTimer.singleShot(0, self._generate_schedule)

    def _generate_schedule(self):
        today_str = datetime.now().strftime('%Y-%m-%d')
        today = datetime.now().date()
        work_times_row = self.db.get_work_times_for_date(today_str)
        if not work_times_row: return
        
        effective_start_time = datetime.strptime(f"{today_str} {work_times_row[1]}", "%Y-%m-%d %H:%M:%S")
        lunch_s_time = time.fromisoformat(work_times_row[5])
        lunch_e_time = time.fromisoformat(work_times_row[6])
        lunch_dur = datetime.combine(datetime.min, lunch_e_time) - datetime.combine(datetime.min, lunch_s_time)
        work_dur = timedelta(hours=work_times_row[4])
        workday_end_time = effective_start_time + work_dur + lunch_dur

        interval = timedelta(minutes=self.config['popup_interval_minutes'])
        lunch_start_dt = datetime.combine(today, lunch_s_time)
        
        schedule_candidates = set()
        next_popup_time = effective_start_time
        # Explicitly add a popup at the start of the lunch hour.
        schedule_candidates.add(lunch_start_dt)

        # Start the loop from the next interval to avoid a popup at the exact start time.
        next_popup_time += interval

        while next_popup_time < workday_end_time:
            if next_popup_time < lunch_start_dt or next_popup_time >= lunch_start_dt + lunch_dur:
                 schedule_candidates.add(next_popup_time)
            next_popup_time += interval
        schedule_candidates.add(workday_end_time)
        
        self.popup_schedule = sorted([t for t in schedule_candidates if effective_start_time <= t <= workday_end_time])
        
        if self.config.get('show_schedule_notification', True) and self.popup_schedule:
            times_str = " | ".join([t.strftime('%H:%M') for t in self.popup_schedule])
            self.tray_icon.showMessage("Popup Schedule", f"Today's popups: {times_str}", QSystemTrayIcon.MessageIcon.Information, 15000)
        
        self.schedule_next_popup_from_list()
        self.schedule_submission_reminders(today, effective_start_time, workday_end_time)

    def schedule_submission_reminders(self, today, start_dt, end_dt):
        reminders_cfg = self.config.get('reminders', {})
        offset_start = timedelta(hours=reminders_cfg.get('reminder_offset_hours_start', 1.0))
        offset_end = timedelta(hours=reminders_cfg.get('reminder_offset_hours_end', 1.0))
        
        def schedule_if_needed(key_enabled, key_day_or_date, day_type, msg):
            if reminders_cfg.get(key_enabled, False):
                if day_type == 'weekday' and today.strftime('%A') == reminders_cfg.get(key_day_or_date, ''):
                    self._schedule_notification(start_dt + offset_start, "Weekly Reminder", f"Remember to submit {msg}.")
                    self._schedule_notification(end_dt - offset_end, "Weekly Reminder", f"Last call to submit {msg}!")
                elif day_type == 'monthday':
                    target_day = min(reminders_cfg.get(key_day_or_date, 1), calendar.monthrange(today.year, today.month)[1])
                    reminder_date = today.replace(day=target_day)
                    while not self.is_working_day(reminder_date):
                        reminder_date -= timedelta(days=1)
                    if today == reminder_date:
                        self._schedule_notification(start_dt + offset_start, "Monthly Reminder", f"Remember to submit {msg}.")
                        self._schedule_notification(end_dt - offset_end, "Monthly Reminder", f"Last call for {msg}!")
        
        schedule_if_needed('weekly_timesheet_enabled', 'weekly_timesheet_day', 'weekday', "last week's timesheet")
        schedule_if_needed('monthly_claims_enabled', 'monthly_claims_day', 'monthday', "your QA83 and Travel claims")
        schedule_if_needed('monthly_timesheet_enabled', 'monthly_timesheet_day', 'monthday', "your timesheet for the month")

    def schedule_next_popup_from_list(self):
        next_time = self.get_next_popup_time()
        if next_time:
            delay_ms = max(0, (next_time - datetime.now()).total_seconds() * 1000)
            QTimer.singleShot(int(delay_ms), lambda: self.show_popup(scheduled_time=next_time))

    def get_next_popup_time(self):
        now = datetime.now()
        for popup_time in self.popup_schedule:
            if popup_time > now: return popup_time
        return None

    def show_popup(self, scheduled_time=None):
        if not self.is_working_time():
            self.schedule_next_popup_from_list()
            return

        # If this is a scheduled popup, check if its time slot is already filled.
        if scheduled_time:
            today_str = scheduled_time.strftime("%Y-%m-%d")
            try:
                current_index = self.popup_schedule.index(scheduled_time)
                
                slot_start_dt = None
                # For the first popup, the slot starts at the beginning of the workday.
                if current_index == 0:
                    work_times_row = self.db.get_work_times_for_date(today_str)
                    if work_times_row:
                        effective_start_time = datetime.strptime(f"{today_str} {work_times_row[1]}", "%Y-%m-%d %H:%M:%S")
                        slot_start_dt = effective_start_time
                # For subsequent popups, the slot starts at the time of the previous popup.
                else:
                    slot_start_dt = self.popup_schedule[current_index - 1]

                # If we have a valid slot to check...
                if slot_start_dt:
                    slot_end_dt = scheduled_time

                    # Check if this slot is fully occupied
                    tasks_today = self.db.get_tasks_for_date(today_str)
                    uncovered_duration_sec = (slot_end_dt - slot_start_dt).total_seconds()

                    for task in tasks_today:
                        task_start = datetime.combine(scheduled_time.date(), time.fromisoformat(task[2]))
                        task_end = datetime.combine(scheduled_time.date(), time.fromisoformat(task[3]))
                        overlap_start = max(slot_start_dt, task_start)
                        overlap_end = min(slot_end_dt, task_end)
                        if overlap_end > overlap_start:
                            uncovered_duration_sec -= (overlap_end - overlap_start).total_seconds()

                    # If the slot is filled (less than 1 second uncovered), skip the popup
                    if uncovered_duration_sec < 1:
                        self.schedule_next_popup_from_list()
                        return
            except (ValueError, IndexError):
                pass # Could not determine slot, proceed to show popup

        popup_date = datetime.now().date()
        popup_start_time = self.determine_start_time_for_date(popup_date).toPython()
        lookup_dt = datetime.combine(popup_date, popup_start_time)
        last_task = self.db.get_task_before(lookup_dt)
        popup = Popup(self.db, last_task, self.config, parent=self)
        start_time = self.determine_start_time_for_date(datetime.now().date())
        popup.start_time_edit.setTime(start_time)
        result = popup.exec()
        if result == QDialog.DialogCode.Accepted:
            self._refresh_all_tabs()
        elif result == QDialog.DialogCode.Rejected:
            next_time = self.get_next_popup_time()
            if next_time:
                self.tray_icon.showMessage("Task Skipped", f"Next popup is at {next_time.strftime('%H:%M')}.", QSystemTrayIcon.MessageIcon.Information, 5000)
        self.schedule_next_popup_from_list()

    def manual_popup(self, start_time=None, end_time=None, has_subsequent_task=False):
        popup_date = self.general_tab.view_date
        if start_time:
            popup_start_time = start_time
        else:
            popup_start_time = self.determine_start_time_for_date(popup_date).toPython()
        
        lookup_dt = datetime.combine(popup_date, popup_start_time)
        previous_task = self.db.get_task_before(lookup_dt)
        popup = Popup(self.db, previous_task, self.config, parent=self, is_manual_trigger=True)
        
        popup.date_edit.setDate(QDate(self.general_tab.view_date))

        if start_time:
            popup.start_time_edit.setTime(QTime(start_time.hour, start_time.minute))
            
            final_end_time = QTime(end_time.hour, end_time.minute)
            if has_subsequent_task:
                now_time = QTime.currentTime()
                if QTime(start_time.hour, start_time.minute) < now_time < final_end_time:
                    temp_time = now_time.addSecs(30)
                    final_end_time = QTime(temp_time.hour(), temp_time.minute())

            workday_end_py = popup._get_workday_end_time_for_date(self.general_tab.view_date)
            if workday_end_py:
                workday_end_qtime = QTime(workday_end_py.hour, workday_end_py.minute)
                final_end_time = min(final_end_time, workday_end_qtime)

            popup.end_time_edit.setTime(final_end_time)
        else:
            calculated_start_time = self.determine_start_time_for_date(self.general_tab.view_date)
            popup.start_time_edit.setTime(calculated_start_time)
        
        if popup.exec() == QDialog.DialogCode.Accepted:
            self._refresh_all_tabs()
            
    def popup_from_copied_task(self, copied_task_data):
        today = datetime.now().date()
        popup_start_time = self.determine_start_time_for_date(today).toPython()
        lookup_dt = datetime.combine(today, popup_start_time)
        previous_task = self.db.get_task_before(lookup_dt)
        
        popup = Popup(self.db, previous_task, self.config, parent=self, is_manual_trigger=True)
        
        today = datetime.now().date()
        start_time = self.determine_start_time_for_date(today)
        popup.date_edit.setDate(QDate(today))
        popup.start_time_edit.setTime(start_time)
        
        popup.project_code_input.setText(copied_task_data[4])
        popup.description_input.setHtml(copied_task_data[5])

        cat_list = copied_task_data[6].split(',') if copied_task_data[6] else []
        for cb in popup.category_checkboxes:
            cb.setChecked(cb.text() in cat_list)

        if popup.exec() == QDialog.DialogCode.Accepted:
            self._refresh_all_tabs()
            
    def determine_start_time_for_date(self, target_date):
        date_str = target_date.strftime('%Y-%m-%d')
        tasks_for_date = self.db.get_tasks_for_date(date_str)
        
        if not tasks_for_date:
            work_times = self.db.get_work_times_for_date(date_str)
            if work_times: return QTime.fromString(work_times[1], "HH:mm:ss")
            return QTime.fromString(self.config['work_start_time_flexible']['upper'], "HH:mm:ss")
        
        last_end_time = QTime.fromString(tasks_for_date[-1][3], "HH:mm:ss")
        lunch_start = QTime.fromString(self.config['lunch_hour']['start'], "HH:mm:ss")
        lunch_end = QTime.fromString(self.config['lunch_hour']['end'], "HH:mm:ss")
        return lunch_end if lunch_start <= last_end_time < lunch_end else last_end_time

    def is_working_time(self):
        today_str = datetime.now().strftime("%Y-%m-%d")
        work_times_row = self.db.get_work_times_for_date(today_str)
        if not work_times_row: return False
        
        start = datetime.strptime(work_times_row[1], '%H:%M:%S').time()
        effective_start_dt = datetime.strptime(f"{today_str} {work_times_row[1]}", "%Y-%m-%d %H:%M:%S")
        lunch_s = time.fromisoformat(work_times_row[5])
        lunch_e = time.fromisoformat(work_times_row[6])
        lunch_dur = datetime.combine(datetime.min, lunch_e) - datetime.combine(datetime.min, lunch_s)
        work_dur = timedelta(hours=work_times_row[4])
        workday_end_dt = effective_start_dt + work_dur + lunch_dur
        end = workday_end_dt.time()
        now_time = datetime.now().time()
        
        return start <= now_time <= end and not (lunch_s <= now_time < lunch_e)

    def check_previous_day_workload(self):
        if not self.config.get('reminders', {}).get('previous_day_workload_enabled', True): return
        
        previous_day = datetime.now().date() - timedelta(days=1)
        days_to_check = 7
        while not self.is_working_day(previous_day) and days_to_check > 0:
            previous_day -= timedelta(days=1)
            days_to_check -= 1
        if days_to_check <= 0: return

        last_tasks = self.db.get_tasks_for_date(previous_day.strftime("%Y-%m-%d"))
        if not last_tasks:
            self.tray_icon.showMessage("Workload Reminder", f"No tasks were saved on {previous_day.strftime('%A')}.", QSystemTrayIcon.MessageIcon.Warning, 10000)
            return

        total_work_seconds = sum((datetime.combine(previous_day, datetime.strptime(t[3], '%H:%M:%S').time()) - datetime.combine(previous_day, datetime.strptime(t[2], '%H:%M:%S').time())).total_seconds() for t in last_tasks)
        required_hours = self.config['daily_working_hours']
        if total_work_seconds / 3600 < required_hours:
            hours_worked = round(total_work_seconds / 3600, 2)
            self.tray_icon.showMessage("Workload Reminder", f"Only {hours_worked}h logged on {previous_day.strftime('%A')}, short of {required_hours}h.", QSystemTrayIcon.MessageIcon.Warning, 10000)
