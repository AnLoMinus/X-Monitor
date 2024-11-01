import psutil
import time
import os
from datetime import datetime
from debugger import debugger

class SystemMonitor:
    @staticmethod
    def get_system_stats():
        cpu_usage = psutil.cpu_percent(interval=None)
        cpu_core_usage = psutil.cpu_percent(interval=None, percpu=True)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_io = psutil.net_io_counters()
        disk_io = psutil.disk_io_counters()
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.as_dict(attrs=['pid', 'name', 'cpu_percent', 'memory_percent'])
                pinfo['cpu_percent'] = pinfo['cpu_percent'] if pinfo['cpu_percent'] is not None else 0.0
                pinfo['memory_percent'] = pinfo['memory_percent'] if pinfo['memory_percent'] is not None else 0.0
                processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        ram_details = {
            'total': ram.total / (1024**3),
            'available': ram.available / (1024**3),
            'used': ram.used / (1024**3),
            'free': ram.free / (1024**3),
            'percent': ram.percent,
            'cached': getattr(ram, 'cached', 0) / (1024**3),
            'buffers': getattr(ram, 'buffers', 0) / (1024**3),
            'shared': getattr(ram, 'shared', 0) / (1024**3),
        }
        
        return {
            'CPU Usage (%)': cpu_usage,
            'CPU Core Usage': cpu_core_usage,
            'RAM Usage (%)': ram.percent,
            'RAM Used (GB)': ram.used / (1024**3),
            'RAM Total (GB)': ram.total / (1024**3),
            'Disk Usage (%)': disk.percent,
            'Disk Used (GB)': disk.used / (1024**3),
            'Disk Total (GB)': disk.total / (1024**3),
            'Network Sent (MB)': net_io.bytes_sent / (1024**2),
            'Network Received (MB)': net_io.bytes_recv / (1024**2),
            'Disk Read (MB/s)': disk_io.read_bytes / (1024**2),
            'Disk Write (MB/s)': disk_io.write_bytes / (1024**2),
            'processes': processes,
            'RAM Details': ram_details
        }

    @staticmethod
    def get_services():
        services = []
        for service in psutil.win_service_iter():
            try:
                service_info = service.as_dict()
                services.append({
                    'name': service_info['name'],
                    'status': service_info['status']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return services

    @staticmethod
    def get_current_time():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def clear_screen():
        # פונקציה לניקוי המסך בהתאם למערכת ההפעלה
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def monitor(interval=1, duration=None):
        start_time = time.time()
        while True:
            SystemMonitor.clear_screen()  # ניקוי המסך לפני כל הדפסה
            stats = SystemMonitor.get_system_stats()
            print(f"System Stats at {SystemMonitor.get_current_time()}:")
            for key, value in stats.items():
                if key != 'processes':
                    print(f"{key}: {value:.2f}")
            print("-" * 40)
            
            # הוספת לוג לכל איטרציה
            debugger.log(f"System stats recorded: {stats}", level='debug')
            
            if duration and (time.time() - start_time) >= duration:
                break
            
            time.sleep(interval)
