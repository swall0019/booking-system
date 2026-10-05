import tkinter as tk
import database as db
from auth import AuthWindow
from main_window import MainWindow


def start_main_window(user):
    app = MainWindow(user)
    app.run()


def main():
    db.init_db()
    root = tk.Tk()
    AuthWindow(root, on_success=start_main_window)
    root.mainloop()


if __name__ == "__main__":
    main()