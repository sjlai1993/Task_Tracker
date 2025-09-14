# Task Tracker

A comprehensive desktop application for meticulous time and task management, designed for professionals in project-based environments. It automates task logging reminders, generates detailed reports, and provides multiple views to analyze your work.

---

## Key Features

*   **Intelligent Task Logging:**
    *   Automatic pop-up reminders at configurable intervals to log your work.
    *   Manual task logging for specific time slots or from copied templates.
    *   Smart time-slot detection, avoiding lunch breaks and overlapping entries.
*   **Daily Timeline View:**
    *   Visualizes your day with recorded tasks and unrecorded time gaps.
    *   Easily edit, delete, or duplicate tasks directly from the timeline.
    *   Override the day's start time for flexible work schedules.
*   **Weekly Timesheet:**
    *   Aggregates hours worked per project for a clear weekly overview.
    *   Highlights weekends and holidays.
    *   Copyable table for easy data export.
*   **Monthly QA83 Reporting:**
    *   A dedicated tab to manage tasks for monthly QA83 reports.
    *   Merge multiple task entries into a single, cohesive description.
    *   Track and set task completion percentages.
    *   Generate a professional HTML report ready for submission.
*   **Travel Log:**
    *   Automatically filters and displays all travel-related tasks for the month.
*   **Configuration & Customization:**
    *   In-app settings to define working hours, lunch breaks, holidays, and working days.
    *   Customize project categories, software lists, and reminder schedules.
*   **System Integration:**
    *   Minimizes to the system tray for unobtrusive operation.
    *   Provides notifications for reminders and application events.
*   **Data Integrity:**
    *   Automated weekly backups of the task database.
    *   Manages the number of backups to conserve disk space.

## Screenshots

![alt text](image.png)

**Example Screenshots:**
*   *General Tab: Shows the daily timeline with recorded and unrecorded slots.*
*   *QA83 Tab: Displays the monthly report view with merged tasks and progress.*
*   *Task Popup: The dialog for logging a new task.*

## Technology Stack

*   **Language:** Python
*   **GUI Framework:** PySide6
*   **Database:** SQLite3

## Setup and Installation

To run the application from the source code, follow these steps.

1.  **Prerequisites:**
    *   Python 3.9+

2.  **Clone the repository (or download the source files):**
    ```bash
    git clone <repository-url>
    cd Task-Tracker
    ```

3.  **Install dependencies:**
    ```bash
    pip install PySide6
    ```

4.  **Run the application:**
    ```bash
    python main.py
    ```
    The application will create `task_tracker.db` and several `.json` configuration files in the same directory on its first run.

## Building an Executable

To package the application into a single `.exe` file for Windows, you can use PyInstaller.

1.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```

2.  **Build the executable:**
    Run the following command from the project's root directory. This command includes the application icon and version information for a professional appearance in Windows.

    ```bash
    pyinstaller TaskTracker.spec
    ```

## Configuration Files

The application uses several `.json` files to store settings. Most of these can be configured through the in-app settings menus (`Settings > ...`).

*   `config.json`: Main application settings (working hours, popups, reminders, etc.).
*   `holiday.json`: List of public holidays.
*   `QA83.json`: Settings specific to the QA83 report (e.g., user's name, designation).
*   `timesheet.json`: Configuration for the weekly timesheet view (e.g., project display order).
*   `travel.json`: Defines categories to be considered for the travel log.

## Author

*   Lai Shi Jian


