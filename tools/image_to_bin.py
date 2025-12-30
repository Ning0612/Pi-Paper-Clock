#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
1-bit Dithering Converter with Resize and Preview

功能：
  1. 載入任意圖片後，根據使用者設定的輸出尺寸 (resize) 先縮放圖片
  2. 利用 Floyd–Steinberg 誤差擴散（dithering）轉換圖片成 1-bit 黑白圖
  3. 即時預覽轉換後的結果
  4. 儲存 .bin 檔案（僅包含 1-bit 像素資料，不含檔頭），可上傳至 Pico 後用 framebuf.MONO_HLSB 顯示

注意：
  - 此程式為桌面應用，請在 PC 上執行
  - 輸出尺寸設定可以改善預覽效能，因為轉換運算量依圖片尺寸而定
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageOps
import numpy as np
import os

class DitheringConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("1-bit Dithering Converter with Resize")
        self.geometry("800x600")
        
        # 儲存原始圖片及轉換結果
        self.original_image = None   # 載入的原始 PIL Image (RGB)
        self.resized_image = None    # 根據設定尺寸縮放後的圖片
        self.converted_image = None  # 轉換後的 1-bit 圖片 (PIL, mode "1")
        self.current_filename = None # 記錄當前載入的檔案名稱
        
        # 縮放相關變數
        self.zoom_factor = 1.0       # 縮放倍數
        self.min_zoom = 0.1          # 最小縮放倍數
        self.max_zoom = 5.0          # 最大縮放倍數
        self.base_preview = None     # 基礎預覽圖片 (未縮放)
        self.zoomed_preview = None   # 縮放後的預覽圖片
        
        # 平移相關變數
        self.pan_offset_x = 0        # X軸平移偏移量
        self.pan_offset_y = 0        # Y軸平移偏移量
        self.is_panning = False      # 是否正在平移
        self.pan_start_x = 0         # 平移開始的X座標
        self.pan_start_y = 0         # 平移開始的Y座標
        
        # Canvas相關變數
        self.canvas_width = 400      # 畫布寬度
        self.canvas_height = 300     # 畫布高度
        
        # 輸出尺寸設定 (單位：像素)
        self.out_width = tk.IntVar(value=128)
        self.out_height = tk.IntVar(value=128)
        
        self.create_widgets()
    
    def create_widgets(self):
        # 控制區
        frm_controls = tk.Frame(self)
        frm_controls.pack(pady=10)
        
        btn_load = tk.Button(frm_controls, text="選取圖片", command=self.load_image)
        btn_load.grid(row=0, column=0, padx=5)
        
        tk.Label(frm_controls, text="輸出寬度:").grid(row=0, column=1, padx=5)
        self.ent_width = tk.Entry(frm_controls, textvariable=self.out_width, width=5)
        self.ent_width.grid(row=0, column=2, padx=5)
        
        tk.Label(frm_controls, text="輸出高度:").grid(row=0, column=3, padx=5)
        self.ent_height = tk.Entry(frm_controls, textvariable=self.out_height, width=5)
        self.ent_height.grid(row=0, column=4, padx=5)
        
        btn_update = tk.Button(frm_controls, text="更新預覽", command=self.update_preview)
        btn_update.grid(row=0, column=5, padx=5)
        
        btn_save = tk.Button(frm_controls, text="儲存 .bin 檔案", command=self.save_image)
        btn_save.grid(row=0, column=6, padx=5)
        
        # 縮放控制區
        frm_zoom = tk.Frame(self)
        frm_zoom.pack(pady=5)
        
        tk.Label(frm_zoom, text="縮放: Ctrl+滾輪 | 平移: 中鍵拖拽 | ").pack(side=tk.LEFT)
        self.lbl_zoom = tk.Label(frm_zoom, text="100%", fg="blue")
        self.lbl_zoom.pack(side=tk.LEFT)
        
        btn_reset_zoom = tk.Button(frm_zoom, text="重設縮放", command=self.reset_zoom_and_update)
        btn_reset_zoom.pack(side=tk.LEFT, padx=(10, 0))
        
        # 預覽區容器（使用Frame包裝以便動態調整大小）
        self.preview_frame = tk.Frame(self, bg="lightgray")
        self.preview_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        # 預覽Canvas（取代Label以支援平移和縮放）
        self.preview_canvas = tk.Canvas(self.preview_frame, bg="gray", highlightthickness=1)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 綁定滑鼠事件
        self.bind_mouse_events()
    
    def bind_mouse_events(self):
        """綁定滑鼠事件（縮放和平移）"""
        # 縮放事件
        self.preview_canvas.bind("<Control-Button-4>", self.on_zoom_in)    # Linux 向上滾輪
        self.preview_canvas.bind("<Control-Button-5>", self.on_zoom_out)   # Linux 向下滾輪
        self.preview_canvas.bind("<Control-MouseWheel>", self.on_mouse_wheel) # Windows 滾輪
        
        # 平移事件（中鍵）
        self.preview_canvas.bind("<Button-2>", self.on_pan_start)          # 中鍵按下
        self.preview_canvas.bind("<B2-Motion>", self.on_pan_move)          # 中鍵拖拽
        self.preview_canvas.bind("<ButtonRelease-2>", self.on_pan_end)     # 中鍵釋放
        
        # 讓 Canvas 可以接收鍵盤事件
        self.preview_canvas.bind("<Button-1>", lambda e: self.preview_canvas.focus_set())
        self.preview_canvas.bind("<Enter>", lambda e: self.preview_canvas.focus_set())
        
        # 視窗大小改變事件
        self.preview_canvas.bind("<Configure>", self.on_canvas_configure)
        
        # 整個視窗的快捷鍵
        self.bind("<Control-Button-4>", self.on_zoom_in)
        self.bind("<Control-Button-5>", self.on_zoom_out)
        self.bind("<Control-MouseWheel>", self.on_mouse_wheel)
    
    def on_mouse_wheel(self, event):
        """處理 Windows 系統的滑鼠滾輪事件"""
        if event.state & 0x4:  # 檢查是否按下 Ctrl 鍵
            if event.delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
    
    def on_zoom_in(self, event):
        """處理放大縮放事件"""
        self.zoom_in()
    
    def on_zoom_out(self, event):
        """處理縮小縮放事件"""
        self.zoom_out()
    
    def zoom_in(self):
        """放大預覽圖片"""
        if self.base_preview is None:
            return
        
        new_zoom = min(self.zoom_factor * 1.25, self.max_zoom)
        if new_zoom != self.zoom_factor:
            self.zoom_factor = new_zoom
            self.apply_zoom()
    
    def zoom_out(self):
        """縮小預覽圖片"""
        if self.base_preview is None:
            return
        
        new_zoom = max(self.zoom_factor / 1.25, self.min_zoom)
        if new_zoom != self.zoom_factor:
            self.zoom_factor = new_zoom
            self.apply_zoom()
    
    def apply_zoom(self):
        """套用縮放到預覽圖片"""
        if self.base_preview is None:
            return
        
        # 計算縮放後的尺寸
        original_width, original_height = self.base_preview.size
        new_width = int(original_width * self.zoom_factor)
        new_height = int(original_height * self.zoom_factor)
        
        # 縮放圖片
        if self.zoom_factor == 1.0:
            # 避免不必要的縮放操作
            self.zoomed_preview = self.base_preview
        else:
            # 使用高品質的縮放演算法
            resample = Image.Resampling.LANCZOS
            self.zoomed_preview = self.base_preview.resize((new_width, new_height), resample)
        
        # 更新Canvas顯示
        self.update_canvas_display()
        
        # 更新縮放比例顯示
        self.update_zoom_display()
    
    def update_zoom_display(self):
        """更新縮放比例顯示"""
        zoom_percent = int(self.zoom_factor * 100)
        self.lbl_zoom.config(text=f"{zoom_percent}%")
    
    def reset_zoom(self):
        """重設縮放倍數和平移"""
        self.zoom_factor = 1.0
        self.zoomed_preview = None
        self.pan_offset_x = 0
        self.pan_offset_y = 0
    
    def reset_zoom_and_update(self):
        """重設縮放倍數並更新顯示"""
        self.reset_zoom()
        self.apply_zoom()
    
    def on_pan_start(self, event):
        """開始平移操作"""
        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.preview_canvas.config(cursor="fleur")
    
    def on_pan_move(self, event):
        """執行平移操作"""
        if not self.is_panning:
            return
        
        # 計算滑鼠移動距離
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        
        # 更新平移偏移量
        self.pan_offset_x += dx
        self.pan_offset_y += dy
        
        # 更新起始座標
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        
        # 重新繪製
        self.update_canvas_display()
    
    def on_pan_end(self, event):
        """結束平移操作"""
        self.is_panning = False
        self.preview_canvas.config(cursor="")
    
    def on_canvas_configure(self, event):
        """畫布大小改變時的處理"""
        # 更新畫布尺寸
        old_width = getattr(self, 'canvas_width', 400)
        old_height = getattr(self, 'canvas_height', 300)
        
        self.canvas_width = event.width
        self.canvas_height = event.height
        
        # 只有當尺寸真正改變且圖片已載入時才重新處理
        if (abs(old_width - event.width) > 10 or abs(old_height - event.height) > 10) and self.original_image is not None:
            # 重新計算基礎預覽圖片的自適應縮放
            self.reprocess_base_preview()
        
        # 當畫布改變大小時，重新計算顯示
        self.update_canvas_display()
    
    def update_canvas_display(self):
        """更新Canvas顯示"""
        if self.zoomed_preview is None:
            # 清除畫布
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(
                self.canvas_width // 2, 
                self.canvas_height // 2,
                text="預覽區\n載入圖片以開始",
                fill="darkgray",
                font=("Arial", 12),
                justify=tk.CENTER
            )
            return
        
        # 清除畫布
        self.preview_canvas.delete("all")
        
        # 創建PhotoImage
        self.preview_photo = ImageTk.PhotoImage(self.zoomed_preview)
        
        # 計算圖片在畫布中的位置（居中+平移偏移）
        img_width, img_height = self.zoomed_preview.size
        center_x = self.canvas_width // 2 + self.pan_offset_x
        center_y = self.canvas_height // 2 + self.pan_offset_y
        
        # 在畫布上繪製圖片
        self.preview_canvas.create_image(
            center_x, center_y,
            image=self.preview_photo,
            anchor=tk.CENTER
        )
    
    def fit_image_to_canvas(self, canvas_width, canvas_height):
        """將圖片自適應縮放以適應畫布大小"""
        if self.base_preview is None:
            return
        
        # 獲取圖片原始尺寸
        img_width, img_height = self.base_preview.size
        
        # 計算縮放比例，保持寬高比且完全顯示在畫布內
        scale_w = (canvas_width * 0.9) / img_width  # 預留10%邊距
        scale_h = (canvas_height * 0.9) / img_height
        scale = min(scale_w, scale_h, 1.0)  # 不放大，只縮小
        
        # 如果圖片比畫布小，保持原尺寸
        if scale >= 1.0:
            return
        
        # 應用縮放
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        if new_width > 0 and new_height > 0:
            self.base_preview = self.base_preview.resize(
                (new_width, new_height), 
                Image.Resampling.LANCZOS
            )
    
    def reprocess_base_preview(self):
        """重新處理基礎預覽圖片以適應新的畫布大小"""
        if self.converted_image is None:
            return
        
        # 重新從轉換後的圖片生成預覽
        preview = self.converted_image.convert("L")
        self.base_preview = preview.copy()
        
        # 使用新的畫布尺寸進行自適應縮放
        self.fit_image_to_canvas(self.canvas_width, self.canvas_height)
        
        # 重新應用當前縮放
        self.apply_zoom()
    
    def load_image(self):
        path = filedialog.askopenfilename(title="選取圖片檔",
                                          filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp")])
        if path:
            try:
                # 載入圖片並轉換為 RGB
                self.original_image = Image.open(path).convert("RGB")
                # 記錄檔案名稱（不含副檔名）
                self.current_filename = os.path.splitext(os.path.basename(path))[0]
                # 重設縮放狀態
                self.reset_zoom()
                self.update_preview()
            except Exception as e:
                messagebox.showerror("錯誤", f"載入圖片失敗：{e}")
    
    def update_preview(self):
        if self.original_image is None:
            return
        
        # 取得輸出尺寸
        w = self.out_width.get()
        h = self.out_height.get()
        if w <= 0 or h <= 0:
            messagebox.showwarning("警告", "輸出尺寸必須大於 0")
            return
        
        # 將原始圖片縮放至指定尺寸，這樣處理速度會更快
        self.resized_image = self.original_image.copy().resize((w, h), Image.Resampling.LANCZOS)
        
        # 使用 Floyd–Steinberg 誤差擴散轉換為 1-bit 圖片
        im_bw = self.resized_image.convert("1", dither=Image.FLOYDSTEINBERG)
        self.converted_image = im_bw
        
        # 預覽：轉回 L 模式顯示，並縮放至預覽區大小
        preview = im_bw.convert("L")
        # 可選：若覺得預覽效果較佳，可加上反轉：
        # preview = ImageOps.invert(preview)
        
        # 儲存基礎預覽圖片（根據當前畫布大小進行自適應縮放）
        self.base_preview = preview.copy()
        # 獲取當前畫布大小，如果還沒初始化則使用預設值
        canvas_w = self.canvas_width if hasattr(self, 'canvas_width') and self.canvas_width > 0 else 400
        canvas_h = self.canvas_height if hasattr(self, 'canvas_height') and self.canvas_height > 0 else 300
        # 使用自適應縮放，保持寬高比
        self.fit_image_to_canvas(canvas_w, canvas_h)
        
        # 重設縮放並套用
        self.reset_zoom()
        self.apply_zoom()
    
    def save_image(self):
        if self.converted_image is None:
            messagebox.showwarning("警告", "請先載入並預覽圖片轉換結果")
            return
        
        # 預設檔名：使用原始檔名加上 .bin 副檔名
        default_filename = f"{self.current_filename}.bin" if self.current_filename else "output.bin"
        
        path = filedialog.asksaveasfilename(title="儲存 .bin 檔案",
                                            initialfile=default_filename,
                                            defaultextension=".bin",
                                            filetypes=[("Bin Files", "*.bin")])
        if path:
            try:
                # 取得 1-bit 圖片的原始位元資料
                data = self.converted_image.tobytes()
                with open(path, "wb") as f:
                    f.write(data)
                messagebox.showinfo("完成", f"檔案已儲存到 {path}")
            except Exception as e:
                messagebox.showerror("錯誤", f"儲存檔案失敗：{e}")

if __name__ == "__main__":
    app = DitheringConverterApp()
    app.mainloop()