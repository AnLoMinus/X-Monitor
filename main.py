from gui import run_gui
from debugger import debugger

def main():
    try:
        debugger.log("Starting system monitoring GUI v0.9.2", level='info')
        run_gui()
        debugger.log("System monitoring GUI closed", level='info')
    except Exception as e:
        debugger.log(f"An error occurred: {str(e)}", level='error')

if __name__ == "__main__":
    main()
