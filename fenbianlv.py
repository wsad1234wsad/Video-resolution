import os
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import shutil
import time
from datetime import datetime

class VideoSearcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("本地视频搜索器")
        self.geometry("1200x600")

        # 搜索范围
        self.paths = []
        tk.Label(self, text="搜索范围:").pack(anchor="w")
        frame_paths = tk.Frame(self)
        frame_paths.pack(fill="x", padx=5, pady=2)
        self.path_listbox = tk.Listbox(frame_paths, height=3, selectmode=tk.MULTIPLE)
        self.path_listbox.pack(side="left", fill="x", expand=True)
        tk.Button(frame_paths, text="添加", command=self.add_path).pack(side="left", padx=2)
        tk.Button(frame_paths, text="移除", command=self.remove_path).pack(side="left", padx=2)

        # 视频格式
        tk.Label(self, text="视频格式:").pack(anchor="w")
        frame_format = tk.Frame(self)
        frame_format.pack(fill="x", padx=5, pady=2)
        self.format_vars = {}
        formats = ["mp4","mkv","avi","mov","flv","wmv","m4v","webm","mpeg","mpg"]
        for fmt in formats:
            var = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(frame_format, text=fmt, variable=var)
            cb.pack(side="left")
            self.format_vars[fmt] = var

        # 筛选条件
        frame_filters = tk.Frame(self)
        frame_filters.pack(fill="x", padx=5, pady=2)
        tk.Label(frame_filters, text="最小宽度:").grid(row=0, column=0)
        self.min_width_entry = tk.Entry(frame_filters, width=6)
        self.min_width_entry.grid(row=0, column=1)
        tk.Label(frame_filters, text="最小高度:").grid(row=0, column=2)
        self.min_height_entry = tk.Entry(frame_filters, width=6)
        self.min_height_entry.grid(row=0, column=3)
        tk.Label(frame_filters, text="最小FPS:").grid(row=0, column=4)
        self.min_fps_entry = tk.Entry(frame_filters, width=6)
        self.min_fps_entry.grid(row=0, column=5)
        tk.Label(frame_filters, text="码率范围(kbps):").grid(row=0, column=6)
        self.min_bitrate_entry = tk.Entry(frame_filters, width=6)
        self.min_bitrate_entry.grid(row=0, column=7)
        tk.Label(frame_filters, text="-").grid(row=0, column=8)
        self.max_bitrate_entry = tk.Entry(frame_filters, width=6)
        self.max_bitrate_entry.grid(row=0, column=9)
        tk.Label(frame_filters, text="文件大小范围(MB):").grid(row=0, column=10)
        self.min_size_entry = tk.Entry(frame_filters, width=6)
        self.min_size_entry.grid(row=0, column=11)
        tk.Label(frame_filters, text="-").grid(row=0, column=12)
        self.max_size_entry = tk.Entry(frame_filters, width=6)
        self.max_size_entry.grid(row=0, column=13)

        # 控制按钮
        frame_buttons = tk.Frame(self)
        frame_buttons.pack(fill="x", pady=5)
        self.progress = ttk.Progressbar(frame_buttons, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=5)
        self.search_button = tk.Button(frame_buttons, text="开始搜索", command=self.start_search)
        self.search_button.pack(side="left", padx=5)
        self.stop_flag = False
        self.stop_button = tk.Button(frame_buttons, text="停止", state="disabled", command=self.stop_search)
        self.stop_button.pack(side="left", padx=5)

        # 结果表格
        columns = ("name", "size", "created", "resolution", "fps", "bitrate", "path")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c, False))
            self.tree.column(col, width=120, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # 右键菜单
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="复制", command=self.copy_files)
        self.menu.add_command(label="剪切", command=self.cut_files)
        self.menu.add_command(label="删除", command=self.delete_files)

    def add_path(self):
        path = filedialog.askdirectory()
        if path:
            self.paths.append(path)
            self.path_listbox.insert("end", path)

    def remove_path(self):
        selected = list(self.path_listbox.curselection())
        for i in reversed(selected):
            self.path_listbox.delete(i)
            self.paths.pop(i)

    def start_search(self):
        self.stop_flag = False
        self.search_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.tree.delete(*self.tree.get_children())
        threading.Thread(target=self.search_files).start()

    def stop_search(self):
        self.stop_flag = True

    def search_files(self):
        formats = [f for f,v in self.format_vars.items() if v.get()]
        min_w = int(self.min_width_entry.get() or 0)
        min_h = int(self.min_height_entry.get() or 0)
        min_fps = float(self.min_fps_entry.get() or 0)
        min_br = int(self.min_bitrate_entry.get() or 0)
        max_br = int(self.max_bitrate_entry.get() or 1e12)
        min_sz = int(self.min_size_entry.get() or 0)*1024*1024
        max_sz = int(self.max_size_entry.get() or 1e12)*1024*1024

        files = []
        for path in self.paths:
            for root, dirs, filenames in os.walk(path):
                for f in filenames:
                    if self.stop_flag:
                        break
                    if f.lower().split(".")[-1] in formats:
                        files.append(os.path.join(root,f))

        self.progress["maximum"] = len(files)
        for i, filepath in enumerate(files):
            if self.stop_flag:
                break
            meta = self.get_metadata(filepath)
            if not meta:
                continue
            w,h,fps,br = meta
            size = os.path.getsize(filepath)
            if w < min_w or h < min_h or fps < min_fps or br < min_br or br > max_br or size < min_sz or size > max_sz:
                continue
            created = time.ctime(os.path.getctime(filepath))
            self.tree.insert("", "end", values=(os.path.basename(filepath), f"{size//1024//1024} MB", created, f"{w}x{h}", f"{fps:.2f}", f"{br//1000}", filepath))
            self.progress["value"] = i+1
        self.search_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def get_metadata(self, filepath):
        try:
            cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                   "stream=width,height,r_frame_rate,bit_rate", "-of", "default=noprint_wrappers=1:nokey=1", filepath]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 4:
                w,h,fps_str,br = lines[:4]
                fps = eval(fps_str) if "/" in fps_str else float(fps_str)
                return int(w), int(h), float(fps), int(br or 0)
        except:
            return None

    def on_double_click(self, event):
        item = self.tree.selection()[0]
        col = self.tree.identify_column(event.x)
        path = self.tree.item(item, "values")[-1]
        if col == "#7":
            subprocess.Popen(f'explorer /select,"{path}"')
        else:
            os.startfile(path)

    def sort_column(self, col, reverse):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        if col in ("size", "bitrate"):
            data = [(int(v.split()[0]) if v else 0, k) for v, k in data]
        elif col == "fps":
            data = [(float(v) if v else 0, k) for v, k in data]
        elif col == "created":
            data = [(datetime.strptime(v, "%a %b %d %H:%M:%S %Y"), k) for v,k in data]
        data.sort(reverse=reverse)
        for index,(val,k) in enumerate(data):
            self.tree.move(k, "", index)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def show_context_menu(self, event):
        try:
            self.tree.selection_set(self.tree.identify_row(event.y))
            self.menu.post(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def copy_files(self):
        files = [self.tree.item(i, "values")[-1] for i in self.tree.selection()]
        dest = filedialog.askdirectory()
        if dest:
            for f in files:
                shutil.copy(f, dest)

    def cut_files(self):
        files = [self.tree.item(i, "values")[-1] for i in self.tree.selection()]
        dest = filedialog.askdirectory()
        if dest:
            for f in files:
                shutil.move(f, dest)

    def delete_files(self):
        files = [self.tree.item(i, "values")[-1] for i in self.tree.selection()]
        if messagebox.askyesno("确认", "确定要删除选中文件吗？"):
            for f in files:
                os.remove(f)

if __name__ == "__main__":
    app = VideoSearcher()
    app.mainloop()
