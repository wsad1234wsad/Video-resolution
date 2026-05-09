import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import fnmatch
import threading
import queue
import platform
import subprocess
from datetime import datetime
import cv2  # 用于获取视频分辨率
import re   # 用于解析自定义分辨率输入


class FileSearchTool:
    def __init__(self, root):
        self.root = root
        self.root.title("文件搜索工具 v4.0 - 支持视频分辨率搜索")
        self.root.geometry("1000x720")

        # 保存初始磁盘列表
        self.system_disks = self.get_disk_list()

        self.setup_ui()

        # 搜索控制变量
        self.search_thread = None
        self.stop_event = threading.Event()
        self.result_queue = queue.Queue()

        # 启动队列检查
        self.root.after(100, self.check_queue)

    def get_disk_list(self):
        """获取所有可用磁盘"""
        disk_list = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            disk = f"{letter}:\\"
            if os.path.exists(disk):
                disk_list.append(disk)
        return disk_list

    def setup_ui(self):
        """创建用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 文件夹选择区域
        folder_frame = ttk.LabelFrame(main_frame, text="搜索目录")
        folder_frame.pack(fill=tk.X, pady=5)

        # 磁盘选择框
        disk_frame = ttk.Frame(folder_frame)
        disk_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(disk_frame, text="选择磁盘:").pack(side=tk.LEFT, padx=5)

        # 磁盘列表框（带滚动条）
        disk_container = ttk.Frame(disk_frame)
        disk_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.disk_listbox = tk.Listbox(
            disk_container,
            height=4,
            selectmode=tk.MULTIPLE,
            exportselection=False
        )
        scrollbar = ttk.Scrollbar(disk_container, orient=tk.VERTICAL, command=self.disk_listbox.yview)
        self.disk_listbox.config(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.disk_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 填充磁盘列表（只添加系统磁盘）
        for disk in self.system_disks:
            self.disk_listbox.insert(tk.END, disk)

        # 目录操作按钮
        btn_frame = ttk.Frame(folder_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="添加文件夹",
                   command=self.browse_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清除选择",
                   command=self.clear_selection).pack(side=tk.LEFT, padx=5)

        # 文件过滤
        filter_frame = ttk.LabelFrame(main_frame, text="文件过滤")
        filter_frame.pack(fill=tk.X, pady=5)

        # 关键字搜索区域
        keyword_frame = ttk.Frame(filter_frame)
        keyword_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(keyword_frame, text="关键字搜索:").pack(side=tk.LEFT, padx=5)
        self.keyword_var = tk.StringVar()
        ttk.Entry(keyword_frame, textvariable=self.keyword_var, width=30).pack(side=tk.LEFT, padx=5)

        # 关键字搜索选项
        self.match_case_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(keyword_frame, text="区分大小写", variable=self.match_case_var).pack(side=tk.LEFT, padx=5)

        self.search_mode_var = tk.StringVar(value="contains")
        mode_combo = ttk.Combobox(keyword_frame, textvariable=self.search_mode_var, width=12)
        mode_combo['values'] = ('包含', '前缀', '后缀', '精确匹配')
        mode_combo.pack(side=tk.LEFT, padx=5)

        # 文件类型选择
        file_type_frame = ttk.Frame(filter_frame)
        file_type_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(file_type_frame, text="文件类型:").pack(side=tk.LEFT, padx=5)
        self.filetype_var = tk.StringVar()
        filetype_combo = ttk.Combobox(file_type_frame, textvariable=self.filetype_var, width=20)
        filetype_combo['values'] = ('所有文件', '图片文件', '视频文件',
                                    '音频文件', '文档文件', '自定义')
        filetype_combo.current(0)
        filetype_combo.pack(side=tk.LEFT, padx=5)

        # 文件大小过滤
        size_frame = ttk.Frame(filter_frame)
        size_frame.pack(fill=tk.X, padx=5, pady=2)

        # 最小大小设置
        min_size_frame = ttk.Frame(size_frame)
        min_size_frame.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(min_size_frame, text="最小大小:").pack(side=tk.LEFT, padx=5)
        self.min_size_var = tk.StringVar()
        min_size_entry = ttk.Entry(min_size_frame, textvariable=self.min_size_var, width=8)
        min_size_entry.pack(side=tk.LEFT, padx=5)

        self.min_unit_var = tk.StringVar(value="KB")
        min_unit_combo = ttk.Combobox(min_size_frame, textvariable=self.min_unit_var, width=4)
        min_unit_combo['values'] = ('B', 'KB', 'MB', 'GB')
        min_unit_combo.pack(side=tk.LEFT, padx=5)

        # 最大大小设置
        max_size_frame = ttk.Frame(size_frame)
        max_size_frame.pack(side=tk.LEFT, padx=5)

        ttk.Label(max_size_frame, text="最大大小:").pack(side=tk.LEFT, padx=5)
        self.max_size_var = tk.StringVar()
        max_size_entry = ttk.Entry(max_size_frame, textvariable=self.max_size_var, width=8)
        max_size_entry.pack(side=tk.LEFT, padx=5)

        self.max_unit_var = tk.StringVar(value="GB")
        max_unit_combo = ttk.Combobox(max_size_frame, textvariable=self.max_unit_var, width=4)
        max_unit_combo['values'] = ('B', 'KB', 'MB', 'GB')
        max_unit_combo.pack(side=tk.LEFT, padx=5)

        # 视频分辨率过滤
        resolution_frame = ttk.Frame(filter_frame)
        resolution_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(resolution_frame, text="视频分辨率:").pack(side=tk.LEFT, padx=5)
        
        # 最小分辨率
        min_res_frame = ttk.Frame(resolution_frame)
        min_res_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(min_res_frame, text="最小:").pack(side=tk.LEFT)
        self.min_width_var = tk.StringVar()
        ttk.Entry(min_res_frame, textvariable=self.min_width_var, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(min_res_frame, text="x").pack(side=tk.LEFT)
        self.min_height_var = tk.StringVar()
        ttk.Entry(min_res_frame, textvariable=self.min_height_var, width=5).pack(side=tk.LEFT, padx=2)
        
        # 最大分辨率
        max_res_frame = ttk.Frame(resolution_frame)
        max_res_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(max_res_frame, text="最大:").pack(side=tk.LEFT)
        self.max_width_var = tk.StringVar()
        ttk.Entry(max_res_frame, textvariable=self.max_width_var, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(max_res_frame, text="x").pack(side=tk.LEFT)
        self.max_height_var = tk.StringVar()
        ttk.Entry(max_res_frame, textvariable=self.max_height_var, width=5).pack(side=tk.LEFT, padx=2)
        
        # 自定义分辨率格式
        custom_res_frame = ttk.Frame(resolution_frame)
        custom_res_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(custom_res_frame, text="或自定义:").pack(side=tk.LEFT)
        self.custom_res_var = tk.StringVar()
        ttk.Entry(custom_res_frame, textvariable=self.custom_res_var, width=15, 
                 tooltip="格式: 1920x1080 或 1920x1080-3840x2160").pack(side=tk.LEFT, padx=2)
        
        # 控制按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="开始搜索", command=self.start_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="停止搜索", command=self.stop_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="高级设置", command=self.show_advanced_settings).pack(side=tk.LEFT, padx=5)

        # 结果列表
        result_frame = ttk.LabelFrame(main_frame, text="搜索结果")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        columns = ("name", "path", "size", "unit", "resolution", "modified", "created", "type")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings", selectmode="extended")

        # 设置列标题
        self.result_tree.heading("name", text="文件名", command=lambda: self.sort_column("name", False))
        self.result_tree.heading("path", text="路径", command=lambda: self.sort_column("path", False))
        self.result_tree.heading("size", text="大小", command=lambda: self.sort_column("size", False))
        self.result_tree.heading("unit", text="单位", command=lambda: self.sort_column("unit", False))
        self.result_tree.heading("resolution", text="分辨率", command=lambda: self.sort_column("resolution", False))
        self.result_tree.heading("modified", text="修改日期", command=lambda: self.sort_column("modified", False))
        self.result_tree.heading("created", text="创建日期", command=lambda: self.sort_column("created", False))
        self.result_tree.heading("type", text="类型", command=lambda: self.sort_column("type", False))

        # 设置列宽
        self.result_tree.column("name", width=150)
        self.result_tree.column("path", width=200)
        self.result_tree.column("size", width=70)
        self.result_tree.column("unit", width=40)
        self.result_tree.column("resolution", width=80)
        self.result_tree.column("modified", width=100)
        self.result_tree.column("created", width=100)
        self.result_tree.column("type", width=70)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_tree.pack(fill=tk.BOTH, expand=True)

        # 右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="打开文件", command=self.open_file)
        self.context_menu.add_command(label="打开所在位置", command=self.open_location)
        self.context_menu.add_command(label="删除文件", command=self.delete_file)
        self.context_menu.add_command(label="复制文件路径", command=self.copy_file_path)
        self.context_menu.add_command(label="查看详细信息", command=self.show_file_details)
        self.result_tree.bind("<Button-3>", self.show_context_menu)

        # 添加双击打开文件功能
        self.result_tree.bind("<Double-1>", self.on_double_click)

        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, padx=10, pady=5)

    def browse_folder(self):
        """选择搜索文件夹并添加到磁盘列表"""
        folder_path = filedialog.askdirectory(title="选择搜索目录", mustexist=True)
        if folder_path:
            # 确保路径格式正确
            folder_path = os.path.normpath(folder_path) + os.sep
            # 添加到列表框（如果不存在）
            if folder_path not in self.disk_listbox.get(0, tk.END):
                self.disk_listbox.insert(tk.END, folder_path)

    def clear_selection(self):
        """清除所有手动添加的文件夹，保留系统磁盘"""
        # 获取当前列表中的所有项
        all_items = list(self.disk_listbox.get(0, tk.END))

        # 删除所有非系统磁盘项
        for item in all_items:
            if item not in self.system_disks:
                # 找到该项的索引位置
                idx = self.disk_listbox.get(0, tk.END).index(item)
                self.disk_listbox.delete(idx)

    def get_selected_paths(self):
        """获取所有选择的搜索路径"""
        selected_indices = self.disk_listbox.curselection()
        return [self.disk_listbox.get(i) for i in selected_indices]

    def parse_resolution_input(self):
        """
        解析分辨率输入，返回最小和最大分辨率元组
        格式: (min_width, min_height, max_width, max_height)
        """
        # 首先检查自定义分辨率输入
        custom_res = self.custom_res_var.get().strip()
        if custom_res:
            # 支持格式: 1920x1080 或 1920x1080-3840x2160
            if '-' in custom_res:
                parts = custom_res.split('-')
                if len(parts) == 2:
                    min_part = parts[0].strip()
                    max_part = parts[1].strip()
                    
                    min_match = re.match(r'(\d+)\s*x\s*(\d+)', min_part)
                    max_match = re.match(r'(\d+)\s*x\s*(\d+)', max_part)
                    
                    if min_match and max_match:
                        return (
                            int(min_match.group(1)), int(min_match.group(2)),
                            int(max_match.group(1)), int(max_match.group(2))
                        )
            
            # 单一分辨率格式
            match = re.match(r'(\d+)\s*x\s*(\d+)', custom_res)
            if match:
                width = int(match.group(1))
                height = int(match.group(2))
                return (width, height, width, height)
        
        # 使用单独的最小/最大分辨率输入框
        min_width = self.min_width_var.get().strip()
        min_height = self.min_height_var.get().strip()
        max_width = self.max_width_var.get().strip()
        max_height = self.max_height_var.get().strip()
        
        min_w = int(min_width) if min_width else 0
        min_h = int(min_height) if min_height else 0
        max_w = int(max_width) if max_width else float('inf')
        max_h = int(max_height) if max_height else float('inf')
        
        return (min_w, min_h, max_w, max_h)

    def get_video_resolution(self, file_path):
        """
        获取视频文件的分辨率
        返回: (width, height) 或 (None, None) 如果无法获取
        """
        try:
            # 使用OpenCV获取视频信息
            cap = cv2.VideoCapture(file_path)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
                return width, height
        except Exception as e:
            print(f"获取视频分辨率失败 {file_path}: {e}")
        
        return None, None

    def check_resolution_match(self, file_path, resolution_filters):
        """
        检查视频文件是否匹配分辨率要求
        """
        if not resolution_filters or not any(resolution_filters):
            return True  # 没有分辨率过滤要求
            
        # 只对视频文件检查分辨率
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.mpeg', 
                          '.mpg', '.m4v', '.3gp', '.webm', '.ogv', '.ts', '.m2ts'}
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext not in video_extensions:
            return True  # 非视频文件，跳过分辨率检查
            
        min_width, min_height, max_width, max_height = resolution_filters
        
        # 获取视频实际分辨率
        actual_width, actual_height = self.get_video_resolution(file_path)
        if actual_width is None or actual_height is None:
            return False  # 无法获取分辨率，不匹配
            
        # 检查分辨率是否在范围内
        return (min_width <= actual_width <= max_width and 
                min_height <= actual_height <= max_height)

    def start_search(self):
        """开始搜索文件"""
        search_paths = self.get_selected_paths()
        if not search_paths:
            messagebox.showerror("错误", "请选择至少一个搜索目录")
            return

        # 验证路径
        invalid_paths = [p for p in search_paths if not os.path.exists(p)]
        if invalid_paths:
            messagebox.showerror("错误", f"以下路径无效:\n{', '.join(invalid_paths)}")
            return

        # 重置搜索
        self.stop_event.clear()
        self.result_tree.delete(*self.result_tree.get_children())
        self.status_var.set("搜索中...")

        # 获取搜索参数
        file_types = self.get_file_types()
        min_size = self.get_size_in_bytes(self.min_size_var.get(), self.min_unit_var.get())
        max_size = self.get_size_in_bytes(self.max_size_var.get(), self.max_unit_var.get())
        keyword = self.keyword_var.get().strip()
        match_case = self.match_case_var.get()
        search_mode = self.search_mode_var.get()
        resolution_filters = self.parse_resolution_input()

        # 启动搜索线程
        self.search_thread = threading.Thread(
            target=self.perform_search,
            args=(search_paths, file_types, min_size, max_size, keyword, match_case, search_mode, resolution_filters),
            daemon=True
        )
        self.search_thread.start()

    def match_keyword(self, filename, keyword, match_case, search_mode):
        """检查文件名是否匹配关键字条件"""
        # 如果关键字为空，始终返回True（匹配所有文件）
        if not keyword:
            return True

        # 处理大小写设置
        if not match_case:
            filename = filename.lower()
            keyword = keyword.lower()

        # 应用不同的搜索模式
        if search_mode == "包含":
            return keyword in filename
        elif search_mode == "前缀":
            return filename.startswith(keyword)
        elif search_mode == "后缀":
            return filename.endswith(keyword)
        elif search_mode == "精确匹配":
            return filename == keyword
        else:
            return True  # 默认返回True

    def get_file_types(self):
        """获取文件类型过滤条件"""
        selected = self.filetype_var.get()

        # 扩展的常见格式
        image_formats = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.tiff',
                         '*.webp', '*.heif', '*.psd', '*.svg', '*.raw', '*.ico',
                         '*.nef', '*.cr2', '*.arw', '*.dng']

        video_formats = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.flv', '*.wmv',
                         '*.mpeg', '*.mpg', '*.m4v', '*.3gp', '*.f4v', '*.vob',
                         '*.ogv', '*.rm', '*.rmvb', '*.ts', '*.m2ts', '*.mts',
                         '*.asf', '*.amv', '*.divx', '*.mxf', '*.webm']

        audio_formats = ['*.mp3', '*.wav', '*.flac', '*.aac', '*.ogg', '*.wma',
                         '*.m4a', '*.ape', '*.alac', '*.ac3', '*.dts', '*.opus',
                         '*.amr', '*.mid', '*.midi', '*.aif', '*.aiff']

        document_formats = ['*.doc', '*.docx', '*.pdf', '*.txt', '*.xls', '*.xlsx',
                            '*.ppt', '*.pptx', '*.rtf', '*.ods', '*.odp',
                            '*.csv', '*.html', '*.htm', '*.epub', '*.mobi']

        file_types = {
            '所有文件': ['*.*'],
            '图片文件': image_formats,
            '视频文件': video_formats,
            '音频文件': audio_formats,
            '文档文件': document_formats,
            '自定义': []
        }

        # 处理自定义类型
        if selected == '自定义':
            custom = self.get_custom_file_types()
            if custom:
                return [fmt.strip() for fmt in custom.split(';')]
            return ['*.*']
        elif selected in file_types:
            return file_types[selected]
        else:
            return selected.split(';') if ';' in selected else [selected]

    def get_custom_file_types(self):
        """获取用户自定义文件类型"""
        return filedialog.askstring("自定义文件类型", 
                                   "输入文件扩展名（用分号分隔）:\n例如: *.mp4;*.avi;*.mkv")

    def get_size_in_bytes(self, size_str, unit):
        """将大小字符串转换为字节"""
        if not size_str or not size_str.replace('.', '', 1).isdigit():
            return 0

        try:
            size_val = float(size_str)
            unit = unit.upper()

            if unit == "B":
                return int(size_val)
            elif unit == "KB":
                return int(size_val * 1024)
            elif unit == "MB":
                return int(size_val * 1024 * 1024)
            elif unit == "GB":
                return int(size_val * 1024 * 1024 * 1024)
            else:
                return int(size_val)
        except ValueError:
            return 0

    def format_file_size(self, size_in_bytes):
        """格式化文件大小（自动选择合适单位）"""
        if size_in_bytes is None:
            return "0", "B"

        kb = size_in_bytes / 1024
        mb = kb / 1024
        gb = mb / 1024

        if gb >= 1:
            return f"{gb:.2f}", "GB"
        elif mb >= 1:
            return f"{mb:.2f}", "MB"
        elif kb >= 1:
            return f"{kb:.2f}", "KB"
        else:
            return f"{size_in_bytes}", "B"

    def perform_search(self, search_paths, file_types, min_size, max_size, keyword, match_case, search_mode, resolution_filters):
        """执行文件搜索"""
        try:
            for folder_path in search_paths:
                if self.stop_event.is_set():
                    break

                for root, _, files in os.walk(folder_path):
                    if self.stop_event.is_set():
                        break

                    for file in files:
                        if self.stop_event.is_set():
                            break

                        file_path = os.path.join(root, file)

                        try:
                            # 获取文件信息
                            stat = os.stat(file_path)
                            file_size = stat.st_size
                            modified_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                            created_time = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M")

                            # 检查文件大小
                            if min_size and file_size < min_size:
                                continue
                            if max_size and file_size > max_size:
                                continue

                            # 检查文件类型
                            match_found = False
                            file_base = file.lower()

                            # 如果是"所有文件"，跳过类型检查
                            if file_types == ['*.*']:
                                match_found = True
                            else:
                                for pattern in file_types:
                                    if fnmatch.fnmatch(file_base, pattern.lower()):
                                        match_found = True
                                        break

                            if not match_found:
                                continue

                            # 检查关键字匹配
                            if not self.match_keyword(file, keyword, match_case, search_mode):
                                continue

                            # 检查分辨率匹配
                            if not self.check_resolution_match(file_path, resolution_filters):
                                continue

                            # 格式化文件大小
                            size_str, size_unit = self.format_file_size(file_size)

                            # 获取分辨率信息（如果是视频文件）
                            resolution_str = ""
                            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', 
                                              '.mpeg', '.mpg', '.m4v', '.3gp', '.webm'}
                            file_ext = os.path.splitext(file)[1].lower()
                            
                            if file_ext in video_extensions:
                                width, height = self.get_video_resolution(file_path)
                                if width and height:
                                    resolution_str = f"{width}x{height}"

                            # 添加到结果队列
                            result = (
                                file,
                                root,
                                size_str,
                                size_unit,
                                resolution_str,
                                modified_time,
                                created_time,
                                file_ext
                            )
                            self.result_queue.put(result)

                        except Exception as e:
                            print(f"访问文件错误 {file_path}: {e}")

            self.result_queue.put(("STATUS", "搜索完成"))
        except Exception as e:
            self.result_queue.put(("STATUS", f"搜索错误: {str(e)}"))

    def check_queue(self):
        """检查并处理结果队列"""
        try:
            while not self.result_queue.empty():
                result = self.result_queue.get_nowait()

                if result[0] == "STATUS":
                    self.status_var.set(result[1])
                    if "完成" in result[1] or "停止" in result[1]:
                        self.search_thread = None
                        # 添加找到的文件数量统计
                        count = len(self.result_tree.get_children())
                        self.status_var.set(f"{result[1]}，找到 {count} 个文件")
                else:
                    self.result_tree.insert("", "end", values=result)

        except queue.Empty:
            pass

        self.root.after(100, self.check_queue)

    def stop_search(self):
        """停止搜索"""
        if self.search_thread and self.search_thread.is_alive():
            self.stop_event.set()
            self.status_var.set("搜索已停止")
            count = len(self.result_tree.get_children())
            self.status_var.set(f"搜索已停止，找到 {count} 个文件")

    def sort_column(self, column, reverse):
        """对列进行排序"""
        data = [
            (self.result_tree.set(child, column), child)
            for child in self.result_tree.get_children("")
        ]

        # 特殊处理大小和分辨率列
        if column == "size":
            try:
                data.sort(key=lambda x: float(x[0]), reverse=reverse)
            except:
                data.sort(reverse=reverse)
        elif column == "resolution":
            # 按分辨率数值排序 (1920x1080 -> 1920 * 1080=面积)
            try:
                data.sort(key=lambda x: self.get_resolution_value(x[0]), reverse=reverse)
            except:
                data.sort(reverse=reverse)
        else:
            data.sort(reverse=reverse)

        for index, (_, child) in enumerate(data):
            self.result_tree.move(child, "", index)

        self.result_tree.heading(column, command=lambda: self.sort_column(column, not reverse))

    def get_resolution_value(self, resolution_str):
        """将分辨率字符串转换为可排序的数值"""
        if not resolution_str or 'x' not in resolution_str:
            return 0
        
        try:
            width, height = map(int, resolution_str.split('x'))
            return width * height  # 使用面积作为排序依据
        except:
            return 0

    def show_context_menu(self, event):
        """显示右键菜单"""
        item = self.result_tree.identify_row(event.y)
        if item:
            self.result_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def open_file(self):
        """打开选定文件"""
        selected = self.result_tree.selection()
        if not selected:
            return

        for item in selected:
            values = self.result_tree.item(item, "values")
            if values:
                file_path = os.path.join(values[1], values[0])
                self.open_with_default_app(file_path)

    def open_location(self):
        """打开文件所在位置"""
        selected = self.result_tree.selection()
        if not selected:
            return

        for item in selected:
            values = self.result_tree.item(item, "values")
            if values:
                folder_path = values[1]
                self.open_folder_in_explorer(folder_path)

    def open_folder_in_explorer(self, folder_path):
        """在文件资源管理器中打开文件夹"""
        try:
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":
                subprocess.call(["open", folder_path])
            else:
                subprocess.call(["xdg-open", folder_path])
        except Exception as e:
            messagebox.showerror("打开错误", f"无法打开位置: {str(e)}")

    def delete_file(self):
        """删除选定文件"""
        selected = self.result_tree.selection()
        if not selected:
            return

        confirm = messagebox.askyesno("确认删除", "确定要删除选定的文件吗？此操作不可恢复！")
        if not confirm:
            return

        for item in selected:
            values = self.result_tree.item(item, "values")
            if values:
                file_path = os.path.join(values[1], values[0])

                try:
                    os.remove(file_path)
                    self.result_tree.delete(item)
                except Exception as e:
                    messagebox.showerror("删除错误", f"无法删除文件: {str(e)}")

    def copy_file_path(self):
        """复制文件路径到剪贴板"""
        selected = self.result_tree.selection()
        if not selected:
            return

        paths = []
        for item in selected:
            values = self.result_tree.item(item, "values")
            if values:
                file_path = os.path.join(values[1], values[0])
                paths.append(file_path)

        if paths:
            self.root.clipboard_clear()
            self.root.clipboard_append("\n".join(paths))
            messagebox.showinfo("复制成功", f"已复制{len(paths)}个文件路径到剪贴板")

    def show_file_details(self):
        """显示文件详细信息"""
        selected = self.result_tree.selection()
        if not selected:
            return

        # 只显示第一个选中文件的详细信息
        item = selected[0]
        values = self.result_tree.item(item, "values")
        if values:
            file_path = os.path.join(values[1], values[0])
            
            try:
                stat = os.stat(file_path)
                file_size = stat.st_size
                size_str, size_unit = self.format_file_size(file_size)
                
                # 获取更多信息（如果是视频文件）
                extra_info = ""
                video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
                file_ext = os.path.splitext(file_path)[1].lower()
                
                if file_ext in video_extensions:
                    width, height = self.get_video_resolution(file_path)
                    if width and height:
                        extra_info = f"\n分辨率: {width}x{height}"
                        
                        # 尝试获取视频时长
                        try:
                            cap = cv2.VideoCapture(file_path)
                            if cap.isOpened():
                                fps = cap.get(cv2.CAP_PROP_FPS)
                                frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                                if fps > 0 and frame_count > 0:
                                    duration = frame_count / fps
                                    minutes = int(duration // 60)
                                    seconds = int(duration % 60)
                                    extra_info += f"\n时长: {minutes}分{seconds}秒"
                                cap.release()
                        except:
                            pass
                
                messagebox.showinfo("文件详细信息", 
                                   f"文件名: {values[0]}\n"
                                   f"路径: {values[1]}\n"
                                   f"大小: {size_str} {size_unit}\n"
                                   f"修改时间: {values[5]}\n"
                                   f"创建时间: {values[6]}\n"
                                   f"类型: {values[7]}"
                                   + extra_info)
            except Exception as e:
                messagebox.showerror("错误", f"无法获取文件信息: {str(e)}")

    def open_with_default_app(self, file_path):
        """使用系统默认应用打开文件"""
        if not os.path.exists(file_path):
            messagebox.showerror("错误", f"文件不存在:\n{file_path}")
            return

        try:
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":
                subprocess.call(["open", file_path])
            else:
                subprocess.call(["xdg-open", file_path])
        except Exception as e:
            messagebox.showerror("打开错误", f"无法打开文件: {str(e)}\n请检查是否安装了相关应用程序")

    def show_advanced_settings(self):
        """显示高级设置对话框"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("高级设置")
        settings_window.geometry("400x300")
        settings_window.transient(self.root)
        settings_window.grab_set()

        ttk.Label(settings_window, text="高级搜索设置", font=("Arial", 12, "bold")).pack(pady=10)
        
        # 添加一些高级设置选项
        ttk.Checkbutton(settings_window, text="跳过系统隐藏文件").pack(anchor=tk.W, padx=20, pady=5)
        ttk.Checkbutton(settings_window, text="跳过系统保护文件").pack(anchor=tk.W, padx=20, pady=5)
        ttk.Checkbutton(settings_window, text="启用深度搜索（较慢）").pack(anchor=tk.W, padx=20, pady=5)
        
        ttk.Separator(settings_window, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(settings_window, text="视频解析设置:").pack(anchor=tk.W, padx=20, pady=5)
        ttk.Checkbutton(settings_window, text="快速视频解析（可能不准确）").pack(anchor=tk.W, padx=30, pady=2)
        ttk.Checkbutton(settings_window, text="解析视频元数据").pack(anchor=tk.W, padx=30, pady=2)
        
        ttk.Button(settings_window, text="保存设置", command=settings_window.destroy).pack(pady=20)

    def on_double_click(self, event):
        """处理双击事件打开文件"""
        selected_items = self.result_tree.selection()
        if selected_items:
            item = selected_items[0]
            values = self.result_tree.item(item, "values")
            if values:
                file_path = os.path.join(values[1], values[0])
                self.open_with_default_app(file_path)


if __name__ == "__main__":
    root = tk.Tk()
    app = FileSearchTool(root)
    root.mainloop()