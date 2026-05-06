# coding=utf-8
import winsound
import os
import tkinter as tk
from tkinter import ttk, messagebox
import tempfile
import shutil
import ctypes
import sys
import glob
import concurrent.futures


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False
def request_admin():
    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return result > 32
    except Exception:
        return False

def beep():
    try:
        winsound.MessageBeep()
    except RuntimeError:
        pass

def clean_temp():
    temp = tempfile.gettempdir()
    cleaned = 0
    failed = 0
    path = (os.path.join(os.environ['SystemRoot'], 'Temp'))
    for file in os.listdir(temp):
        try:
            if os.path.isfile(os.path.join(temp, file)) :
                os.remove(os.path.join(temp, file))
            else :
                shutil.rmtree(os.path.join(temp, file))
            cleaned += 1
        except WindowsError :
            failed += 1
    for file in os.listdir(path):
        try:
            if os.path.isfile(os.path.join(path, file)) :
                os.remove(os.path.join(path, file))
            else :
                shutil.rmtree(os.path.join(path, file))
            cleaned += 1
        except WindowsError as e:
            failed += 1
            print(e)
    beep()
    messagebox.showinfo('清理报告','成功清理：'+str(cleaned)+'\n'+'文件正在被使用：'+str(failed))

def clean_log():
    files_to_delete = glob.glob(r"C:\**\*.log", recursive=True)
    path2 = (os.path.join(os.environ['SystemRoot'], 'Logs'))
    fd = 0
    wd = 0
    def delete_one(file_path):
        nonlocal fd, wd
        try:
            os.remove(file_path)
            wd += 1
        except OSError:
            fd += 1
    print(files_to_delete)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        executor.map(delete_one, files_to_delete)

    files_to_delete = glob.glob(r"D:\**\*.log", recursive=True)
    print(files_to_delete)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        executor.map(delete_one, files_to_delete)
    for file in os.listdir(path2):
        try:
            if os.path.isfile(os.path.join(path2, file)) :
                os.remove(os.path.join(path2, file))
            else :
                shutil.rmtree(os.path.join(path2, file))
            wd += 1
        except WindowsError as e:
            fd += 1
            print(e)
    beep()
    messagebox.showinfo('清理报告', '成功清理：' + str(wd) + '\n' + '文件正在被使用：' + str(fd))

def main():
    root = tk.Tk()
    root.title("清理工具")
    root.geometry("300x200")
    ttk.Button(text='清理临时文件', command=clean_temp).pack(pady=10)
    ttk.Button(text='清理日志', command=clean_log).pack(pady=10)
    root.mainloop()

if not is_admin():
    success = request_admin()
    if not success:
        print("错误", "需要管理员权限才能清理系统临时文件。")
    sys.exit()
main()