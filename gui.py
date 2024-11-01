import sys
import csv
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QComboBox, QTabWidget, QProgressBar, 
                             QStyleFactory, QSplitter, QFrame, QTreeWidget, QTreeWidgetItem,
                             QHeaderView, QMenu, QAction, QFileDialog, QMessageBox, QLineEdit,
                             QGridLayout, QDialog, QFormLayout, QShortcut, QSizePolicy, QScrollArea,
                             QSystemTrayIcon)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor, QPalette, QKeySequence, QIcon, QPixmap, QPainter
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QSplineSeries, QPieSeries
from monitor import SystemMonitor
from debugger import debugger
import psutil

class UpdateThread(QThread):
    update_signal = pyqtSignal(dict)

    def run(self):
        while True:
            stats = SystemMonitor.get_system_stats()
            self.update_signal.emit(stats)
            self.msleep(1000)  # עדכון כל שנייה

class ModernProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2196F3;
                border-radius: 5px;
                background-color: #E0E0E0;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 3px;
            }
        """)

class StatWidget(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #2196F3;
                border-radius: 10px;
                background-color: #FFFFFF;
            }
        """)
        layout = QVBoxLayout(self)
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.title_label.setStyleSheet("color: #2196F3;")
        self.value_label = QLabel("0.00")
        self.value_label.setFont(QFont("Arial", 24))
        self.value_label.setStyleSheet("color: #212121;")
        self.progress_bar = ModernProgressBar()
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.progress_bar)

    def update_value(self, value):
        if isinstance(value, (int, float)):
            self.value_label.setText(f"{value:.2f}")
            if value <= 100:
                self.progress_bar.setValue(int(value))
                self.animate_value(value)
        else:
            self.value_label.setText(str(value))
            self.progress_bar.setValue(0)

    def animate_value(self, value):
        animation = QPropertyAnimation(self.progress_bar, b"value")
        animation.setDuration(500)
        animation.setStartValue(self.progress_bar.value())
        animation.setEndValue(int(value))
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.start()

class ModernChartWidget(QChartView):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.chart = QChart()
        self.chart.setTitle(title)
        self.chart.setTitleFont(QFont("Arial", 14, QFont.Bold))
        self.chart.setTitleBrush(QColor("#2196F3"))
        self.setChart(self.chart)
        self.series = QSplineSeries()
        self.chart.addSeries(self.series)
        self.chart.createDefaultAxes()
        self.chart.axes(Qt.Horizontal)[0].setRange(0, 60)
        self.chart.axes(Qt.Vertical)[0].setRange(0, 100)
        self.chart.setBackgroundBrush(QColor("#FFFFFF"))
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.data_points = []

    def update_chart(self, value):
        self.data_points.append(value)
        if len(self.data_points) > 60:
            self.data_points.pop(0)
        self.series.clear()
        for i, point in enumerate(self.data_points):
            self.series.append(i, point)

class ProcessTreeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Add search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search processes...")
        self.search_input.textChanged.connect(self.filter_processes)
        layout.addWidget(self.search_input)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["PID", "Name", "CPU %", "Memory %"])
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.tree)

    def update_processes(self, processes):
        self.tree.clear()
        for process in processes:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, str(process['pid']))
            item.setText(1, process['name'])
            cpu_percent = process['cpu_percent']
            item.setText(2, f"{cpu_percent:.2f}" if cpu_percent is not None else "N/A")
            memory_percent = process['memory_percent']
            item.setText(3, f"{memory_percent:.2f}" if memory_percent is not None else "N/A")
        self.filter_processes()

    def filter_processes(self):
        search_text = self.search_input.text().lower()
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setHidden(search_text not in item.text(1).lower())

    def show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if item is not None:
            menu = QMenu()
            kill_action = QAction("Kill Process", self)
            kill_action.triggered.connect(lambda: self.kill_process(item.text(0)))
            menu.addAction(kill_action)
            menu.exec_(self.tree.viewport().mapToGlobal(position))

    def kill_process(self, pid):
        # Implement process killing logic here
        print(f"Killing process with PID: {pid}")

class CPUCoreWidget(QWidget):
    def __init__(self, core_count, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        self.core_charts = []
        for i in range(core_count):
            chart = ModernChartWidget(f"Core {i} Usage")
            self.core_charts.append(chart)
            layout.addWidget(chart, i // 2, i % 2)

    def update_cores(self, core_usages):
        for i, usage in enumerate(core_usages):
            self.core_charts[i].update_chart(usage)

class RAMWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # RAM usage over time chart
        self.ram_chart = ModernChartWidget("RAM Usage Over Time")
        layout.addWidget(self.ram_chart)
        
        # RAM distribution pie chart
        self.pie_chart = QChartView()
        self.pie_chart.setRenderHint(QPainter.Antialiasing)
        self.pie_series = QPieSeries()
        chart = QChart()
        chart.addSeries(self.pie_series)
        chart.setTitle("RAM Distribution")
        self.pie_chart.setChart(chart)
        layout.addWidget(self.pie_chart)
        
        # RAM details tree
        self.ram_details = QTreeWidget()
        self.ram_details.setHeaderLabels(["Property", "Value"])
        self.ram_details.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(self.ram_details)

    def update_ram(self, ram_info):
        self.ram_chart.update_chart(ram_info['percent'])
        
        # Update pie chart
        self.pie_series.clear()
        self.pie_series.append("Used", ram_info['used'])
        self.pie_series.append("Available", ram_info['available'])
        
        # Update RAM details tree
        self.ram_details.clear()
        for key, value in ram_info.items():
            item = QTreeWidgetItem(self.ram_details)
            item.setText(0, key)
            if key in ['total', 'available', 'used', 'free', 'cached', 'buffers', 'shared']:
                item.setText(1, f"{value:.2f} GB")
            elif key == 'percent':
                item.setText(1, f"{value:.2f}%")
            else:
                item.setText(1, str(value))

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        layout = QFormLayout(self)
        
        self.update_interval = QComboBox()
        self.update_interval.addItems(["1 second", "5 seconds", "10 seconds", "30 seconds"])
        layout.addRow("Update Interval:", self.update_interval)
        
        self.theme = QComboBox()
        self.theme.addItems(["Dark", "Light"])
        layout.addRow("Theme:", self.theme)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.accept)
        layout.addRow(self.save_button)

class ResizableSection(QWidget):
    def __init__(self, title, content_widget, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar
        title_bar = QWidget()
        title_bar.setStyleSheet("background-color: #2196F3; color: white; border-top-left-radius: 10px; border-top-right-radius: 10px;")
        title_layout = QHBoxLayout(title_bar)
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        title_layout.addWidget(title_label)
        layout.addWidget(title_bar)

        # Content
        content_widget.setStyleSheet("background-color: #FFFFFF; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px;")
        layout.addWidget(content_widget)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("border: 1px solid #2196F3; border-radius: 10px;")

class DashboardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setSpacing(20)

        self.cpu_widget = ResizableSection("CPU Usage", StatWidget("CPU Usage (%)"))
        self.ram_widget = ResizableSection("RAM Usage", StatWidget("RAM Usage (%)"))
        self.disk_widget = ResizableSection("Disk Usage", StatWidget("Disk Usage (%)"))
        self.cpu_temp_widget = ResizableSection("CPU Temperature", StatWidget("CPU Temperature (°C)"))
        self.network_sent_widget = ResizableSection("Network Sent", StatWidget("Network Sent (MB)"))
        self.network_received_widget = ResizableSection("Network Received", StatWidget("Network Received (MB)"))

        layout.addWidget(self.cpu_widget, 0, 0)
        layout.addWidget(self.ram_widget, 0, 1)
        layout.addWidget(self.disk_widget, 1, 0)
        layout.addWidget(self.cpu_temp_widget, 1, 1)
        layout.addWidget(self.network_sent_widget, 2, 0)
        layout.addWidget(self.network_received_widget, 2, 1)

    def update_stats(self, stats):
        self.cpu_widget.findChild(StatWidget).update_value(stats['CPU Usage (%)'])
        self.ram_widget.findChild(StatWidget).update_value(stats['RAM Usage (%)'])
        self.disk_widget.findChild(StatWidget).update_value(stats['Disk Usage (%)'])
        self.cpu_temp_widget.findChild(StatWidget).update_value(stats.get('CPU Temperature (°C)', 'N/A'))
        self.network_sent_widget.findChild(StatWidget).update_value(stats['Network Sent (MB)'])
        self.network_received_widget.findChild(StatWidget).update_value(stats['Network Received (MB)'])

class SystemMonitorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Monitor v0.9.2")
        self.setGeometry(100, 100, 1400, 900)
        self.setup_modern_theme()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # אזור תצוגה ראשי
        self.main_area = QTabWidget()
        self.main_area.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2196F3;
                background: white;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: #E3F2FD;
                color: #2196F3;
                padding: 8px 16px;
                border: 1px solid #BBDEFB;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #2196F3;
                color: white;
            }
        """)
        main_layout.addWidget(self.main_area)

        # יצירת לשוניות באזור התצוגה הראשי
        self.create_main_tabs()

        # יצירת תפריט
        self.create_menu()

        # יצירת קיצורי מקלדת
        self.create_shortcuts()

        self.statusBar().showMessage("Ready")
        self.statusBar().setStyleSheet("background-color: #E3F2FD; color: #2196F3;")

        # Set up system tray icon for notifications
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.png"))  # Replace with your icon
        self.tray_icon.setVisible(True)

        self.update_thread = UpdateThread()
        self.update_thread.update_signal.connect(self.update_stats)
        self.update_thread.start()

        self.stats_history = []

        debugger.log("GUI initialized", level='info')

    def setup_modern_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F5F5;
            }
            QLabel {
                color: #212121;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QLineEdit {
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                padding: 4px;
            }
        """)

    def create_main_tabs(self):
        # לוח בקרה מרכזי
        self.dashboard = DashboardWidget()
        self.main_area.addTab(self.dashboard, "💻 Dashboard")

        # לשונית גרפים
        charts_tab = QWidget()
        charts_layout = QVBoxLayout(charts_tab)
        self.cpu_chart = ModernChartWidget("CPU Usage Over Time")
        self.ram_chart = ModernChartWidget("RAM Usage Over Time")
        self.network_chart = ModernChartWidget("Network Usage Over Time")
        self.disk_io_chart = ModernChartWidget("Disk I/O Over Time")
        charts_layout.addWidget(self.cpu_chart)
        charts_layout.addWidget(self.ram_chart)
        charts_layout.addWidget(self.network_chart)
        charts_layout.addWidget(self.disk_io_chart)
        self.main_area.addTab(charts_tab, "📊 Charts")

        # לשונית תהליכים
        self.process_tree = ProcessTreeWidget()
        self.main_area.addTab(self.process_tree, "🔍 Processes")

        # לשונית ליבות מעבד
        cpu_cores_tab = CPUCoreWidget(psutil.cpu_count())
        self.main_area.addTab(cpu_cores_tab, "💻 CPU Cores")

        # לשונית פרטי זיכרון RAM
        ram_tab = RAMWidget()
        self.main_area.addTab(ram_tab, "🧠 RAM Details")

        # לשונית דיסק
        disk_tab = QWidget()
        disk_layout = QVBoxLayout(disk_tab)
        disk_layout.addWidget(self.dashboard.disk_widget)
        self.main_area.addTab(disk_tab, "💾 Disk")

    def create_menu(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu('File')
        export_action = QAction('Export Data', self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        # View Menu
        view_menu = menubar.addMenu('View')
        for i in range(self.main_area.count()):
            tab_name = self.main_area.tabText(i)
            tab_action = QAction(tab_name, self)
            tab_action.triggered.connect(lambda checked, index=i: self.main_area.setCurrentIndex(index))
            view_menu.addAction(tab_action)
        
        # Settings Menu
        settings_menu = menubar.addMenu('Settings')
        settings_action = QAction('Open Settings', self)
        settings_action.triggered.connect(self.open_settings)
        settings_menu.addAction(settings_action)

    def open_settings(self):
        settings_dialog = SettingsDialog(self)
        if settings_dialog.exec_():
            # Handle settings changes here
            update_interval = settings_dialog.update_interval.currentText()
            theme = settings_dialog.theme.currentText()
            # Apply the new settings
            self.apply_settings(update_interval, theme)

    def apply_settings(self, update_interval, theme):
        # Apply update interval
        interval_map = {"1 second": 1000, "5 seconds": 5000, "10 seconds": 10000, "30 seconds": 30000}
        self.update_thread.msleep(interval_map[update_interval])
        
        # Apply theme
        if theme == "Dark":
            self.setup_dark_theme()
        else:
            self.setup_light_theme()

    def setup_light_theme(self):
        # Implement light theme here
        pass

    def create_shortcuts(self):
        for i in range(1, 5):  # Create shortcuts for the first 4 tabs
            QShortcut(QKeySequence(f"Ctrl+{i}"), self, lambda i=i: self.main_area.setCurrentIndex(i-1))

    def update_stats(self, stats=None):
        if stats is None:
            stats = SystemMonitor.get_system_stats()
        
        self.dashboard.update_stats(stats)

        self.cpu_chart.update_chart(stats['CPU Usage (%)'])
        self.ram_chart.update_chart(stats['RAM Usage (%)'])
        self.network_chart.update_chart(stats['Network Sent (MB)'] + stats['Network Received (MB)'])
        self.disk_io_chart.update_chart(stats['Disk Read (MB/s)'] + stats['Disk Write (MB/s)'])

        self.process_tree.update_processes(stats['processes'])

        cpu_cores_tab = self.main_area.widget(self.main_area.indexOf(self.main_area.findChild(CPUCoreWidget)))
        if cpu_cores_tab:
            cpu_cores_tab.update_cores(stats['CPU Core Usage'])

        ram_tab = self.main_area.widget(self.main_area.indexOf(self.main_area.findChild(RAMWidget)))
        if ram_tab:
            ram_tab.update_ram(stats['RAM Details'])

        self.stats_history.append(stats)
        if len(self.stats_history) > 3600:  # שמירת היסטוריה של שעה
            self.stats_history.pop(0)

        self.check_alerts(stats)

        self.statusBar().showMessage(f"Last update: {SystemMonitor.get_current_time()}")
        debugger.log("Stats updated in GUI", level='debug')

    def check_alerts(self, stats):
        if stats['CPU Usage (%)'] > 90:
            self.show_alert("High CPU Usage", f"CPU usage is at {stats['CPU Usage (%)']:.2f}%")
        if stats['RAM Usage (%)'] > 90:
            self.show_alert("High RAM Usage", f"RAM usage is at {stats['RAM Usage (%)']:.2f}%")

    def show_alert(self, title, message):
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.Warning)

    def export_data(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Export Data", "", "CSV Files (*.csv)")
        if file_name:
            with open(file_name, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.stats_history[0].keys())
                writer.writeheader()
                for stats in self.stats_history:
                    writer.writerow(stats)
            QMessageBox.information(self, "Export Successful", f"Data exported to {file_name}")

def run_gui():
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create('Fusion'))
    window = SystemMonitorGUI()
    window.show()
    app.exec_()
