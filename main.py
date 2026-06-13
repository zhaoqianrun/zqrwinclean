# coding=utf-8
import winsound
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import tempfile
import shutil
import ctypes
import sys
import glob
import concurrent.futures
import time
import threading
import json
from collections import defaultdict


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(__file__)


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin():
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return True
    except Exception:
        return False

def beep():
    try:
        winsound.MessageBeep()
    except RuntimeError:
        pass


def clean_temp():
    winlog = []
    failog = []
    temp = tempfile.gettempdir()
    cleaned = 0
    failed = 0
    path = os.path.join(os.environ['SystemRoot'], 'Temp')
    
    for file in os.listdir(temp):
        try:
            full_path = os.path.join(temp, file)
            if os.path.isfile(full_path):
                os.remove(full_path)
            else:
                shutil.rmtree(full_path)
            cleaned += 1
            winlog.append(f"文件：{file} - 删除成功")
        except WindowsError:
            failed += 1
            failog.append(f"文件：{file} - 删除失败")
    
    for file in os.listdir(path):
        try:
            full_path = os.path.join(path, file)
            if os.path.isfile(full_path):
                os.remove(full_path)
            else:
                shutil.rmtree(full_path)
            cleaned += 1
            winlog.append(f"文件：{file} - 删除成功")
        except WindowsError as e:
            failed += 1
            print(e)
            failog.append(f"文件：{file} - 删除失败")
    
    beep()
    messagebox.showinfo('清理报告', f'成功清理：{cleaned}\n文件正在被使用：{failed}')
    
    if winlog or failog:
        log_file = os.path.join(tempfile.gettempdir(), "WinTools_temp_log.txt")
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("=== 成功删除的文件 ===\n")
            f.write("\n".join(winlog[:100]))
            f.write("\n\n=== 删除失败的文件 ===\n")
            f.write("\n".join(failog[:100]))
        messagebox.showinfo("日志已保存", f"详细日志已保存到：\n{log_file}")

def collect_log_files(priority_dirs, full_scan=False):
    all_files = []
    
    if priority_dirs:
        for dir_path in priority_dirs:
            if os.path.exists(dir_path):
                try:
                    pattern = os.path.join(dir_path, "**", "*.log")
                    files = glob.glob(pattern, recursive=True)
                    all_files.extend(files)
                    print(f"在优先目录 {dir_path} 中找到 {len(files)} 个.log文件")
                except Exception as e:
                    print(f"搜索目录 {dir_path} 时出错: {e}")
    
    if full_scan:
        response = messagebox.askyesno("全盘扫描", 
                                       f"已在优先目录中找到 {len(all_files)} 个.log文件\n\n"
                                       "是否要全盘扫描所有.log文件？\n"
                                       "注意：全盘扫描可能很耗时，建议只在必要时使用。")
        if response:
            messagebox.showinfo("提示", "开始全盘扫描C:和D:盘，这可能需要几分钟时间...")
            
            def scan_drive(drive):
                try:
                    pattern = f"{drive}:\\**\\*.log"
                    return glob.glob(pattern, recursive=True)
                except Exception as e:
                    print(f"扫描 {drive}: 盘时出错: {e}")
                    return []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_c = executor.submit(scan_drive, "C")
                future_d = executor.submit(scan_drive, "D")
                
                c_files = future_c.result(timeout=300)
                d_files = future_d.result(timeout=300)
            
            all_files.extend(c_files)
            all_files.extend(d_files)
            
            all_files = list(set(all_files))
            messagebox.showinfo("扫描完成", f"全盘扫描完成，共找到 {len(all_files)} 个.log文件")
    
    return all_files

def clean_log(priority_dirs, days_old=7, full_scan=False):
    winlog = []
    failog = []
    protected_paths = [
        "C:\\Windows\\System32",
        "C:\\Windows\\SysWOW64",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\Windows\\WinSxS"
    ]
    cutoff_time = time.time() - (days_old * 86400)
    cleaned_count = 0
    failed_count = 0

    def is_protected(file_path):
        for protect_dir in protected_paths:
            if file_path.lower().startswith(protect_dir.lower()):
                return True
        return False

    def delete_one(file_path):
        nonlocal cleaned_count, failed_count, winlog, failog
        if is_protected(file_path):
            failed_count += 1
            failog.append(f"文件：{file_path} - 跳过（受保护路径）")
            return
        try:
            mtime = os.path.getmtime(file_path)
        except OSError:
            failed_count += 1
            failog.append(f"文件：{file_path} - 获取文件时间失败")
            return
        
        if mtime >= cutoff_time:
            failed_count += 1
            failog.append(f"文件：{file_path} - 跳过（文件较新）")
            return

        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            else:
                shutil.rmtree(file_path)
            cleaned_count += 1
            winlog.append(f"文件：{file_path} - 删除成功")
        except OSError as e:
            failed_count += 1
            failog.append(f"文件：{file_path} - 删除失败：{str(e)}")

    all_files = collect_log_files(priority_dirs, full_scan)
    
    if not all_files:
        messagebox.showinfo("提示", "没有找到任何.log文件")
        return
    
    response = messagebox.askyesno("确认删除", 
                                   f"共找到 {len(all_files)} 个.log文件\n"
                                   f"将删除 {days_old} 天前的文件\n\n"
                                   "是否继续清理？")
    if not response:
        return
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(delete_one, file) for file in all_files]
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            if completed % 100 == 0:
                print(f"进度: {completed}/{len(all_files)}")
    
    beep()
    
    result_msg = (f'成功清理：{cleaned_count} 个\n'
                  f'跳过/失败：{failed_count} 个\n'
                  f'总计处理：{len(all_files)} 个')
    
    messagebox.showinfo('日志清理报告', result_msg)
    
    if winlog or failog:
        log_file = os.path.join(tempfile.gettempdir(), "WinTools_log_log.txt")
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("=== 清理报告 ===\n")
            f.write(result_msg + "\n\n")
            f.write("=== 成功删除的文件 ===\n")
            f.write("\n".join(winlog[:200]))
            f.write("\n\n=== 跳过/失败的文件 ===\n")
            f.write("\n".join(failog[:200]))
        messagebox.showinfo("日志已保存", f"详细日志已保存到：\n{log_file}")


class LogCleaner:
    def __init__(self):
        self.priority_dirs = []
        self.auto_discovered_dirs = []
        self.config_file = os.path.join(get_base_path(), "youxian.json")
        self.load_config()
    
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.priority_dirs = config.get('priority_dirs', [])
                    self.auto_discovered_dirs = config.get('auto_discovered_dirs', [])
        except Exception as e:
            print(f"加载配置失败: {e}")
            self.priority_dirs = []
            self.auto_discovered_dirs = []
    
    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'priority_dirs': self.priority_dirs,
                    'auto_discovered_dirs': self.auto_discovered_dirs
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def scan_for_log_directories(self, root_paths=None, min_log_count=3):
        if root_paths is None:
            root_paths = ["C:\\Users", "C:\\ProgramData", "D:\\"]
        
        log_dirs = defaultdict(int)
        
        for root_path in root_paths:
            if not os.path.exists(root_path):
                continue
                
            try:
                pattern = os.path.join(root_path, "**", "*.log")
                for log_file in glob.glob(pattern, recursive=True):
                    dir_path = os.path.dirname(log_file)
                    log_dirs[dir_path] += 1
                    
                    parent_dir = os.path.dirname(dir_path)
                    if parent_dir != root_path:
                        log_dirs[parent_dir] += 1
            except Exception as e:
                print(f"扫描 {root_path} 时出错: {e}")
        
        discovered = []
        for dir_path, count in log_dirs.items():
            if count >= min_log_count and dir_path not in self.priority_dirs:
                discovered.append({
                    'path': dir_path,
                    'log_count': count,
                    'size': self.get_directory_size(dir_path)
                })
        
        discovered.sort(key=lambda x: x['log_count'], reverse=True)
        return discovered
    
    def get_directory_size(self, dir_path):
        total_size = 0
        try:
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    if file.endswith('.log'):
                        try:
                            total_size += os.path.getsize(os.path.join(root, file))
                        except:
                            pass
        except:
            pass
        return total_size / (1024 * 1024)
    
    def auto_manage_directories(self, parent):
        dialog = tk.Toplevel(parent)
        dialog.title("自动管理优先目录 - WinTools")
        dialog.geometry("750x550")
        dialog.transient(parent)
        dialog.grab_set()
        
        info_text = ("自动扫描会查找包含.log文件的目录，并自动添加到优先列表\n"
                    "同时会移除那些已经没有任何.log文件的目录")
        ttk.Label(dialog, text=info_text, foreground="blue", wraplength=650).pack(pady=5)
        
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        left_frame = ttk.LabelFrame(main_frame, text="当前优先目录", width=300)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        left_listbox_frame = ttk.Frame(left_frame)
        left_listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        left_scrollbar = ttk.Scrollbar(left_listbox_frame)
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        left_listbox = tk.Listbox(left_listbox_frame, yscrollcommand=left_scrollbar.set, selectmode=tk.EXTENDED)
        left_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scrollbar.config(command=left_listbox.yview)
        
        for dir_path in self.priority_dirs:
            left_listbox.insert(tk.END, dir_path)
        
        left_btn_frame = ttk.Frame(left_frame)
        left_btn_frame.pack(pady=5)
        
        def select_all_left():
            left_listbox.select_set(0, tk.END)
        
        def deselect_all_left():
            left_listbox.selection_clear(0, tk.END)
        
        ttk.Button(left_btn_frame, text="全选", command=select_all_left, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_btn_frame, text="取消全选", command=deselect_all_left, width=8).pack(side=tk.LEFT, padx=2)
        
        right_frame = ttk.LabelFrame(main_frame, text="自动发现的目录（包含.log文件）", width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        right_top_frame = ttk.Frame(right_frame)
        right_top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        def select_all_right():
            for item in tree.get_children():
                tree.selection_add(item)
        
        def deselect_all_right():
            tree.selection_remove(*tree.selection())
        
        ttk.Button(right_top_frame, text="全选检测到的目录", command=select_all_right, width=15).pack(side=tk.LEFT, padx=2)
        ttk.Button(right_top_frame, text="取消全选", command=deselect_all_right, width=10).pack(side=tk.LEFT, padx=2)
        
        columns = ('目录', '日志数', '大小(MB)')
        tree = ttk.Treeview(right_frame, columns=columns, show='headings', selectmode='extended')
        
        tree.heading('目录', text='目录路径')
        tree.heading('日志数', text='日志文件数')
        tree.heading('大小(MB)', text='日志总大小(MB)')
        
        tree.column('目录', width=350)
        tree.column('日志数', width=80)
        tree.column('大小(MB)', width=100)
        
        tree_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=tree_scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        discovered_dirs = []
        
        def scan_and_display():
            for item in tree.get_children():
                tree.delete(item)
            
            progress_label = ttk.Label(dialog, text="正在扫描，请稍候...", foreground="green")
            progress_label.pack()
            dialog.update()
            
            def scan_thread():
                nonlocal discovered_dirs
                discovered_dirs = self.scan_for_log_directories(min_log_count=3)
                dialog.after(0, lambda: update_tree())
                dialog.after(0, progress_label.destroy)
            
            def update_tree():
                for item in discovered_dirs:
                    tree.insert('', tk.END, values=(
                        item['path'],
                        item['log_count'],
                        f"{item['size']:.2f}"
                    ))
            
            threading.Thread(target=scan_thread, daemon=True).start()
        
        def add_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("提示", "请先选择要添加的目录")
                return
            
            added_count = 0
            for item in selected:
                values = tree.item(item)['values']
                dir_path = values[0]
                if dir_path not in self.priority_dirs:
                    self.priority_dirs.append(dir_path)
                    left_listbox.insert(tk.END, dir_path)
                    added_count += 1
            
            if added_count > 0:
                self.save_config()
                messagebox.showinfo("成功", f"已添加 {added_count} 个目录到优先列表")
        
        def remove_selected():
            selected = left_listbox.curselection()
            if not selected:
                messagebox.showwarning("提示", "请先选择要移除的目录")
                return
            
            removed_count = 0
            for index in reversed(selected):
                dir_path = left_listbox.get(index)
                if dir_path in self.priority_dirs:
                    self.priority_dirs.remove(dir_path)
                    left_listbox.delete(index)
                    removed_count += 1
            
            if removed_count > 0:
                self.save_config()
                messagebox.showinfo("成功", f"已移除 {removed_count} 个目录")
        
        def remove_empty_dirs():
            empty_dirs = []
            
            for dir_path in self.priority_dirs[:]:
                if os.path.exists(dir_path):
                    try:
                        log_files = glob.glob(os.path.join(dir_path, "**", "*.log"), recursive=True)
                        if not log_files:
                            empty_dirs.append(dir_path)
                    except:
                        empty_dirs.append(dir_path)
                else:
                    empty_dirs.append(dir_path)
            
            if not empty_dirs:
                messagebox.showinfo("提示", "没有发现空的目录")
                return
            
            result = messagebox.askyesno("确认删除", 
                                        f"发现 {len(empty_dirs)} 个目录不再包含.log文件：\n\n" + 
                                        "\n".join(empty_dirs[:10]) + 
                                        ("\n..." if len(empty_dirs) > 10 else "") +
                                        "\n\n是否从优先列表中移除这些目录？")
            
            if result:
                for dir_path in empty_dirs:
                    if dir_path in self.priority_dirs:
                        self.priority_dirs.remove(dir_path)
                        for i in range(left_listbox.size()):
                            if left_listbox.get(i) == dir_path:
                                left_listbox.delete(i)
                                break
                
                self.save_config()
                messagebox.showinfo("完成", f"已移除 {len(empty_dirs)} 个目录")
        
        ttk.Button(btn_frame, text="开始扫描", command=scan_and_display).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="添加选中", command=add_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="移除选中", command=remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清理空目录", command=remove_empty_dirs).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        dialog.after(100, scan_and_display)
        dialog.wait_window()
    
    def manage_directories(self, parent):
        dialog = tk.Toplevel(parent)
        dialog.title("手动管理优先目录 - WinTools")
        dialog.geometry("550x450")
        dialog.transient(parent)
        dialog.grab_set()
        
        ttk.Label(dialog, text="手动添加/删除优先搜索的目录", 
                  foreground="blue").pack(pady=5)
        
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        dir_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, selectmode=tk.EXTENDED)
        dir_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=dir_listbox.yview)
        
        for dir_path in self.priority_dirs:
            dir_listbox.insert(tk.END, dir_path)
        
        select_frame = ttk.Frame(dialog)
        select_frame.pack(pady=5)
        
        def select_all():
            dir_listbox.select_set(0, tk.END)
        
        def deselect_all():
            dir_listbox.selection_clear(0, tk.END)
        
        ttk.Button(select_frame, text="全选", command=select_all, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(select_frame, text="取消全选", command=deselect_all, width=10).pack(side=tk.LEFT, padx=5)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def add_directory():
            dir_path = tk.filedialog.askdirectory(title="选择要优先搜索的目录")
            if dir_path and dir_path not in self.priority_dirs:
                self.priority_dirs.append(dir_path)
                dir_listbox.insert(tk.END, dir_path)
                self.save_config()
        
        def remove_directory():
            selected = dir_listbox.curselection()
            if not selected:
                messagebox.showwarning("提示", "请先选择要移除的目录")
                return
            
            removed_count = 0
            for index in reversed(selected):
                removed = dir_listbox.get(index)
                if removed in self.priority_dirs:
                    self.priority_dirs.remove(removed)
                    dir_listbox.delete(index)
                    removed_count += 1
            
            if removed_count > 0:
                self.save_config()
                messagebox.showinfo("成功", f"已移除 {removed_count} 个目录")
        
        ttk.Button(btn_frame, text="添加目录", command=add_directory).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="删除选中", command=remove_directory).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        dialog.wait_window()


def main():
    log_cleaner = LogCleaner()
    
    def start_clean_temp():
        threading.Thread(target=clean_temp, daemon=True).start()
    
    def start_clean_log():
        days = simpledialog.askinteger("清理设置", 
                                       "删除几天前的.log文件？\n(默认7天)",
                                       initialvalue=7,
                                       minvalue=1,
                                       maxvalue=365)
        if days is None:
            return
        
        full_scan = messagebox.askyesno("搜索范围", 
                                        "是否进行全盘搜索？\n\n"
                                        "是：全盘搜索C:和D:盘\n"
                                        "否：仅搜索优先目录\n\n"
                                        "提示：可以在'自动管理'中添加常用目录")
        
        threading.Thread(target=clean_log, 
                        args=(log_cleaner.priority_dirs, days, full_scan),
                        daemon=True).start()
    
    def auto_manage():
        log_cleaner.auto_manage_directories(root)
    
    def manual_manage():
        log_cleaner.manage_directories(root)
    
    beep()
    root = tk.Tk()
    root.title("WinTools")
    root.geometry("400x300")
    
    try:
        root.iconbitmap(default='logo.ico')
    except:
        pass
    
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    title_label = ttk.Label(main_frame, text="WinTools", 
                            font=('Arial', 14, 'bold'))
    title_label.pack(pady=10)
    
    ttk.Button(main_frame, text='清理临时文件', 
               command=start_clean_temp, width=25).pack(pady=8)
    
    ttk.Button(main_frame, text='清理日志文件', 
               command=start_clean_log, width=25).pack(pady=8)
    
    ttk.Button(main_frame, text='自动管理优先目录', 
               command=auto_manage, width=25).pack(pady=8)
    
    ttk.Button(main_frame, text='手动管理优先目录', 
               command=manual_manage, width=25).pack(pady=8)
    
    def update_status():
        count = len(log_cleaner.priority_dirs)
        status_label.config(text=f"当前优先目录数量: {count}")
        root.after(1000, update_status)
    
    status_label = ttk.Label(main_frame, text="当前优先目录数量: 0", foreground="green")
    status_label.pack(pady=10)
    update_status()
    
    copyright_label = ttk.Label(main_frame, text="© 2024 WinTools", 
                                font=('Arial', 8))
    copyright_label.pack(side=tk.BOTTOM, pady=5)
    
    root.mainloop()


if __name__ == "__main__":
    if not is_admin():
        success = request_admin()
        if not success:
            print("需要管理员权限才能清理系统临时文件。")
            messagebox.showerror("错误", "需要管理员权限才能清理系统临时文件。")
        sys.exit()
    main()
