import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
import os
import subprocess
import tempfile

DJI_IRP_PATH = r"D:\\ctx\\Documents\\UAV\\temperReader\\dji_thermal_sdk_v1.5_20240507\\sample\\bin\\windows\\release_x64\\dji_irp.exe"

class ThermalImageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Thermal Image Viewer")
        self.root.geometry("1000x600")  # 调整窗口大小

        # 数据初始化
        self.jpg_path = None
        self.temperature_matrix = None
        self.image = None
        self.highest_region = None
        self.highest_temp_info = None

        # 创建界面
        self.setup_ui()

    def setup_ui(self):
        """创建用户界面"""
        # 主框架
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 图像显示区域
        self.canvas = tk.Canvas(self.main_frame, width=640, height=480, bg="grey")
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)

        # 侧边框架
        self.sidebar_frame = tk.Frame(self.main_frame, width=300)
        self.sidebar_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        # 导入按钮
        self.import_btn = tk.Button(self.sidebar_frame, text="导入 JPG 文件", command=self.import_jpg, width=20)
        self.import_btn.pack(pady=10)

        # 详细信息
        self.info_label = tk.Label(self.sidebar_frame, text="详细信息", anchor="nw", justify="left", width=40, height=10)
        self.info_label.pack(pady=10, fill=tk.BOTH, expand=True)

        # 日志显示框
        self.log_frame = tk.Frame(self.sidebar_frame)
        self.log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(self.log_frame, height=15, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar = tk.Scrollbar(self.log_frame, command=self.log_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=self.scrollbar.set)

    def log(self, message):
        """日志信息追加显示"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

    def import_jpg(self):
        """选择 JPG 文件并处理"""
        self.jpg_path = filedialog.askopenfilename(
            title="选择 JPG 文件",
            filetypes=(("JPG 文件", "*.jpg"), ("所有文件", "*.*"))
        )
        if not self.jpg_path:
            return

        self.log(f"加载文件: {self.jpg_path}")

        raw_path = self.process_with_dji_irp(self.jpg_path)

        if raw_path and os.path.exists(raw_path):
            self.temperature_matrix = self.extract_temperature_from_raw(raw_path)
            os.remove(raw_path)

            self.image = cv2.imread(self.jpg_path)
            self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)

            # 找到全图最高温度点
            self.highest_temp_info = self.find_highest_temperature_point()

            self.display_image()
            self.display_highest_temp_info()
            self.canvas.bind("<Button-1>", self.on_mouse_click)
    # def import_jpg(self):
    #     """选择 JPG 文件并处理"""
    #     self.jpg_path = filedialog.askopenfilename(
    #         title="选择 JPG 文件",
    #         filetypes=(("JPG 文件", "*.jpg"), ("所有文件", "*.*"))
    #     )
    #     if not self.jpg_path:
    #         return

    #     self.log(f"加载文件: {self.jpg_path}")

    #     raw_path = self.process_with_dji_irp(self.jpg_path)

    #     if raw_path and os.path.exists(raw_path):
    #         self.temperature_matrix = self.extract_temperature_from_raw(raw_path)
    #         os.remove(raw_path)

    #         self.image = cv2.imread(self.jpg_path)
    #         self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)

    #         # 查找最高平均温度区域
    #         self.highest_region, self.highest_temp_info = self.find_highest_average_temperature_region(50, 50)

    #         self.display_image()
    #         self.display_highest_temp_info()
    #         self.canvas.bind("<Button-1>", self.on_mouse_click)

    def process_with_dji_irp(self, jpg_path):
        """调用 DJI IRP 工具生成 RAW 文件"""
        try:
            raw_path = tempfile.mktemp(suffix=".raw")
            command = [
                DJI_IRP_PATH,
                "-s", jpg_path,
                "-a", "measure",
                "-o", raw_path
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                messagebox.showerror("错误", f"Dji_irp.exe 处理失败:\n{result.stderr}")
                return None
            #self.log("RAW 文件生成成功")
            return raw_path
        except Exception as e:
            messagebox.showerror("错误", f"调用 DJI IRP 工具失败: {e}")
            return None

    def extract_temperature_from_raw(self, raw_path):
        """从 RAW 文件中提取温度数据"""
        try:
            dtype = np.int16
            data = np.fromfile(raw_path, dtype=dtype)
            width, height = 640, 512
            if data.size != width * height:
                raise ValueError("RAW 文件大小与图像分辨率不匹配")
            self.log("温度数据提取成功")
            return data.reshape((height, width)) / 10.0
        except Exception as e:
            messagebox.showerror("错误", f"提取温度数据失败: {e}")
            return None

    def find_highest_temperature_point(self):
        """找到全图的温度最高点"""
        if self.temperature_matrix is None:
            return None, None

        temp_matrix = self.temperature_matrix
        highest_temp = np.max(temp_matrix)
        highest_temp_point = np.unravel_index(np.argmax(temp_matrix), temp_matrix.shape)
        self.log(f"最高温度: {highest_temp:.1f}°C, 坐标: ({highest_temp_point[1]}, {highest_temp_point[0]})")

        highest_temp_info = {
            "highest_point": (highest_temp_point[1], highest_temp_point[0]),
            "highest_temp": highest_temp
        }
        return highest_temp_info
    # def find_highest_average_temperature_region(self, region_width, region_height):
    #     """找到平均温度最高的区域"""
    #     if self.temperature_matrix is None:
    #         return None, None

    #     temp_matrix = self.temperature_matrix
    #     max_avg_temp = -np.inf
    #     best_region = (0, 0)
    #     highest_temp = -np.inf
    #     highest_temp_point = (0, 0)

    #     for y in range(temp_matrix.shape[0] - region_height + 1):
    #         for x in range(temp_matrix.shape[1] - region_width + 1):
    #             region = temp_matrix[y:y+region_height, x:x+region_width]
    #             avg_temp = np.mean(region)

    #             # 更新最高平均温度区域
    #             if avg_temp > max_avg_temp:
    #                 max_avg_temp = avg_temp
    #                 best_region = (x, y)

    #             # 更新最高温度点
    #             max_temp_in_region = np.max(region)
    #             if max_temp_in_region > highest_temp:
    #                 highest_temp = max_temp_in_region
    #                 highest_temp_point = np.unravel_index(np.argmax(region), region.shape)
    #                 highest_temp_point = (x + highest_temp_point[1], y + highest_temp_point[0])

    #     highest_temp_info = {
    #         "highest_point": highest_temp_point,
    #         "highest_temp": highest_temp,
    #         "average_temp": max_avg_temp
    #     }
    #     self.log(f"最高温度: {highest_temp:.1f}°C, 平均温度: {max_avg_temp:.1f}°C")
    #     return best_region, highest_temp_info

    def display_image(self):
        """在界面上显示图像，并标记全图最高温度点"""
        if self.image is not None:
            img = self.image.copy()

            if self.highest_temp_info:
                x, y = self.highest_temp_info["highest_point"]
                cv2.circle(img, (x, y), 15, (0, 0, 255), 3)  # 标记最高温度点
                cv2.putText(
                    img, f"{self.highest_temp_info['highest_temp']:.1f}",
                    (x + 20, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3
                )

            img_resized = cv2.resize(img, (640, 480))
            img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)

            # Convert to a format Tkinter can handle
            self.tk_image = tk.PhotoImage(data=cv2.imencode('.png', img_rgb)[1].tobytes())
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
    # def display_image(self):
    #     """在界面上显示图像，并标记最高平均温度区域"""
    #     if self.image is not None:
    #         img = self.image.copy()

    #         if self.highest_region:
    #             x, y = self.highest_region
    #             region_width, region_height = 50, 50
    #             cv2.rectangle(
    #                 img,
    #                 (x, y),
    #                 (x + region_width, y + region_height),
    #                 (0, 0, 255),  # 红色框
    #                 2
    #             )

    #         img_resized = cv2.resize(img, (640, 480))
    #         img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)

    #         # Convert to a format Tkinter can handle
    #         self.tk_image = tk.PhotoImage(data=cv2.imencode('.png', img_rgb)[1].tobytes())
    #         self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

    #         #self.tk_image = tk.PhotoImage(data=cv2.imencode('.png', img_resized)[1].tobytes())
    #         #self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

    def display_highest_temp_info(self):
        """显示最高温度点的详细信息"""
        if self.highest_temp_info:
            info = self.highest_temp_info
            text = (
                f"最高温度点坐标: {info['highest_point'][0]}, {info['highest_point'][1]}\n"
                f"最高温度: {info['highest_temp']:.1f}°C"
            )
            self.info_label.config(text=text)
    # def display_highest_temp_info(self):
    #     """显示最高温度区域的详细信息"""
    #     if self.highest_temp_info:
    #         info = self.highest_temp_info
    #         text = (
    #         f"最高温度点坐标: {info['highest_point'][0]}, {info['highest_point'][1]}\n"
    #         f"最高温度: {info['highest_temp']:.1f}°C\n"
    #         f"区域平均温度: {info['average_temp']:.1f}°C"
    #     )
    #         self.info_label.config(text=text)

    def on_mouse_click(self, event):
        """鼠标点击事件：显示温度信息"""
        if self.temperature_matrix is None or self.image is None:
            return

        x = int(event.x * self.temperature_matrix.shape[1] / 640)
        y = int(event.y * self.temperature_matrix.shape[0] / 480)

        if 0 <= x < self.temperature_matrix.shape[1] and 0 <= y < self.temperature_matrix.shape[0]:
            temperature = self.temperature_matrix[y, x]
            self.log(f"点击坐标: ({x}, {y}), 温度: {temperature:.1f}°C")
        else:
            self.log("点击范围超出图像边界")

if __name__ == "__main__":
    root = tk.Tk()
    app = ThermalImageApp(root)
    root.mainloop()