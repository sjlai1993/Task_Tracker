# main_window.py

import sys
import json
import os
from datetime import datetime, time, timedelta
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QSystemTrayIcon, QMenu, QMessageBox, QStyle, QDialog,
                             QTabWidget)
from PySide6.QtCore import QTimer, QTime, QDate, Qt
from PySide6.QtGui import QIcon, QAction
from database import Database
from popup import Popup
from settings_window import SettingsWindow
from about_window import AboutWindow
from general_tab import GeneralTab
from timesheet_tab import TimesheetTab
from travel_tab import TravelTab
from qa83_tab import QA83Tab

class MainWindow(QMainWindow):
    APP_VERSION = "A01"
    HOLIDAY_FILE = 'holiday.json'

    def __init__(self):
        super().__init__()
        self.db = Database()
        self.config = {}
        self.holidays = []
        self.reload_config()
        self.popup_schedule = []
        self.load_app_icon()
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

    def load_app_icon(self):
        script_dir = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(script_dir, "icon.png")
        self.app_icon = QIcon()
        if os.path.exists(icon_path):
            self.app_icon.addFile(icon_path)
        else:
            style = self.style()
            self.app_icon = style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

    def init_ui(self):
        self.setWindowIcon(self.app_icon)
        self.setWindowTitle("Task Tracker")
        self.setMinimumSize(540, 400)
        
        menu_bar = self.menuBar()
        style = self.style()
        file_menu = menu_bar.addMenu("&File")
        exit_icon = style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
        exit_action = QAction(exit_icon, "&Exit", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(exit_action)
        settings_menu = menu_bar.addMenu("&Settings")
        settings_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        edit_config_action = QAction(settings_icon, "Edit Configuration...", self)
        edit_config_action.triggered.connect(self._open_settings_window)
        settings_menu.addAction(edit_config_action)
        about_menu = menu_bar.addMenu("&About")
        about_icon = style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        about_action = QAction(about_icon, "&About Task Tracker", self)
        about_action.triggered.connect(self._show_about_dialog)
        about_menu.addAction(about_action)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.general_tab = GeneralTab(parent=self, db=self.db, config=self.config)
        timesheet_tab = TimesheetTab(parent=self, db=self.db, main_config=self.config)
        travel_tab = TravelTab(parent=self, db=self.db)
        # =====================================================================
        # === MODIFIED SECTION START (Pass db to QA83Tab) ===
        # =====================================================================
        qa83_tab = QA83Tab(parent=self, db=self.db)
        # =====================================================================
        # === MODIFIED SECTION END ===
        # =====================================================================

        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(timesheet_tab, "Timesheet")
        self.tabs.addTab(travel_tab, "Travel")
        self.tabs.addTab(qa83_tab, "QA83")

    def _show_about_dialog(self):
        about_dialog = AboutWindow(version=self.APP_VERSION, parent=self)
        about_dialog.exec()

    def check_version(self):
        stored_version = self.db.get_setting("app_version")
        if stored_version is None:
            print(f"First run detected. Saving version {self.APP_VERSION} to database.")
            self.db.set_setting("app_version", self.APP_VERSION)
        elif stored_version != self.APP_VERSION:
            print(f"App updated from v{stored_version} to v{self.APP_VERSION}.")
            self.db.set_setting("app_version", self.APP_VERSION)

    def _open_settings_window(self):
        settings_dialog = SettingsWindow(self)
        if settings_dialog.exec():
            self.reload_config()
            self.general_tab.config = self.config
            self.general_tab.update_task_view()
            QMessageBox.information(self, "Settings Updated", "Settings and holidays saved. Changes are now active.")

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
            self.tray_icon.showMessage("Task Tracker Minimized", "...", QSystemTrayIcon.MessageIcon.NoIcon, 10000)
            self.db.set_setting("minimize_notification_shown", "true")
        event.ignore(); self.hide()

    def update_daily_working_times(self):
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")
        if today.strftime('%A') not in self.config['working_days'] or today_str in self.config['holidays']: return
        if self.db.get_work_times_for_date(today_str) is not None:
            self.schedule_popups_for_the_day()
            return
        now_time = today.time()
        lower_bound = time.fromisoformat(self.config['work_start_time_flexible']['lower'])
        upper_bound = time.fromisoformat(self.config['work_start_time_flexible']['upper'])
        effective_start_time = now_time
        if now_time < lower_bound:
            effective_start_time = lower_bound
        elif now_time > upper_bound:
            effective_start_time = upper_bound
        settings_snapshot = {
            'work_start_lower': self.config['work_start_time_flexible']['lower'],
            'work_start_upper': self.config['work_start_time_flexible']['upper'],
            'daily_working_hours': self.config['daily_working_hours'],
            'lunch_start': self.config['lunch_hour']['start'],
            'lunch_end': self.config['lunch_hour']['end'],
            'working_days': self.config['working_days'],
            'holidays': self.config['holidays']
        }
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
        work_times_row = self.db.get_work_times_for_date(today_str)
        if not work_times_row: return
        effective_start_time = datetime.strptime(f"{today_str} {work_times_row[1]}", "%Y-%m-%d %H:%M:%S")
        lunch_s = time.fromisoformat(work_times_row[5])
        lunch_e = time.fromisoformat(work_times_row[6])
        lunch_dur = datetime.combine(datetime.min, lunch_e) - datetime.combine(datetime.min, lunch_s)
        work_dur = timedelta(hours=work_times_row[4])
        workday_end_time = effective_start_time + work_dur + lunch_dur
        lunch_start = datetime.strptime(f"{today_str} {work_times_row[5]}", "%Y-%m-%d %H:%M:%S")
        lunch_end = datetime.strptime(f"{today_str} {work_times_row[6]}", "%Y-%m-%d %H:%M:%S")
        interval = timedelta(minutes=self.config['popup_interval_minutes'])
        self.popup_schedule = []
        next_popup_time = effective_start_time
        while next_popup_time < datetime.now(): next_popup_time += interval
        while next_popup_time <= workday_end_time:
            if not (lunch_start < next_popup_time < lunch_end):
                self.popup_schedule.append(next_popup_time)
            next_popup_time += interval
        self.schedule_next_popup_from_list()

    def schedule_next_popup_from_list(self):
        next_time = self.get_next_popup_time()
        if next_time:
            delay_ms = (next_time - datetime.now()).total_seconds() * 1000
            QTimer.singleShot(int(delay_ms), self.show_popup)

    def get_next_popup_time(self):
        now = datetime.now()
        for popup_time in self.popup_schedule:
            if popup_time > now: return popup_time
        return None

    def show_popup(self):
        if not self.is_working_time():
            self.schedule_next_popup_from_list()
            return
        last_task = self.db.get_last_task()
        popup = Popup(self.db, last_task, self.config, parent=self)
        start_time = self.determine_start_time(last_task)
        popup.start_time_edit.setTime(start_time)
        result = popup.exec()
        if result == QDialog.DialogCode.Accepted:
            self.general_tab.update_task_view()
        elif result == QDialog.DialogCode.Rejected:
            next_time = self.get_next_popup_time()
            if next_time:
                self.tray_icon.showMessage("Task Skipped", f"Next popup is at {next_time.strftime('%H:%M:%S')}.", QSystemTrayIcon.MessageIcon.NoIcon, 5000)
        self.schedule_next_popup_from_list()

    def manual_popup(self):
        last_task = self.db.get_last_task()
        popup = Popup(self.db, last_task, self.config, parent=self, is_manual_trigger=True)
        start_time = self.determine_start_time(last_task)
        popup.date_edit.setDate(QDate(self.general_tab.view_date))
        popup.start_time_edit.setTime(start_time)
        if popup.exec() == QDialog.DialogCode.Accepted:
            self.general_tab.update_task_view()
            
    def determine_start_time(self, last_task):
        view_qdate = QDate(self.general_tab.view_date)
        tasks_for_view_date = self.db.get_tasks_for_date(self.general_tab.view_date.strftime('%Y-%m-%d'))
        if not tasks_for_view_date:
            work_times = self.db.get_work_times_for_date(self.general_tab.view_date.strftime('%Y-%m-%d'))
            if work_times:
                return QTime.fromString(work_times[1], "HH:mm:ss")
            else:
                return QTime.fromString(self.config['work_start_time_flexible']['upper'], "HH:mm:ss")
        last_task_on_day = tasks_for_view_date[-1]
        last_end_time = QTime.fromString(last_task_on_day[3], "HH:mm:ss")
        lunch_start = QTime.fromString(self.config['lunch_hour']['start'], "HH:mm:ss")
        lunch_end = QTime.fromString(self.config['lunch_hour']['end'], "HH:mm:ss")
        if lunch_start <= last_end_time < lunch_end: return lunch_end
        return last_end_time

    def is_working_time(self):
        today_str = datetime.now().strftime("%Y-%m-%d")
        work_times_row = self.db.get_work_times_for_date(today_str)
        if not work_times_row: return False
        start = datetime.strptime(work_times_row[1], '%H:%M:%S').time()
        effective_start_time = datetime.strptime(f"{today_str} {work_times_row[1]}", "%Y-%m-%d %H:%M:%S")
        lunch_s = time.fromisoformat(work_times_row[5])
        lunch_e = time.fromisoformat(work_times_row[6])
        lunch_dur = datetime.combine(datetime.min, lunch_e) - datetime.combine(datetime.min, lunch_s)
        work_dur = timedelta(hours=work_times_row[4])
        workday_end_time = effective_start_time + work_dur + lunch_dur
        end = workday_end_time.time()
        now_time = datetime.now().time()
        if not (start <= now_time <= end): return False
        lunch_start = datetime.strptime(work_times_row[5], '%H:%M:%S').time()
        lunch_end = datetime.strptime(work_times_row[6], '%H:%M:%S').time()
        if lunch_start <= now_time < lunch_end: return False
        return True

    def check_previous_day_workload(self):
        today = datetime.now().date()
        previous_day = today - timedelta(days=1)
        days_to_check = 7
        while (previous_day.strftime('%A') not in self.config['working_days'] or \
              previous_day.strftime('%Y-%m-%d') in self.config['holidays']) and days_to_check > 0:
            previous_day -= timedelta(days=1)
            days_to_check -= 1
        if days_to_check <= 0: return
        last_tasks = self.db.get_tasks_for_date(previous_day.strftime("%Y-%m-%d"))
        if not last_tasks:
            self.tray_icon.showMessage("Gentle Reminder", f"No tasks saved on {previous_day.strftime('%A')}.", QSystemTrayIcon.MessageIcon.NoIcon, 10000)
            return
        total_work_seconds = 0
        for task in last_tasks:
            try:
                start_time = datetime.strptime(task[2], '%H:%M:%S').time()
                end_time = datetime.strptime(task[3], '%H:%M:%S').time()
                total_work_seconds += (datetime.combine(previous_day, end_time) - datetime.combine(previous_day, start_time)).total_seconds()
            except (ValueError, IndexError): continue
        if total_work_seconds / 3600 < self.config['daily_working_hours']:
            hours_worked = round(total_work_seconds / 3600, 2)
            self.tray_icon.showMessage("Gentle Reminder", f"Only {hours_worked}h is logged on {previous_day.strftime('%A')}, short of {self.config['daily_working_hours']}h.", QSystemTrayIcon.MessageIcon.NoIcon, 10000)