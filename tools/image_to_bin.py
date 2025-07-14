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

class DitheringConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("1-bit Dithering Converter with Resize")
        self.geometry("800x600")
        
        # 儲存原始圖片及轉換結果
        self.original_image = None   # 載入的原始 PIL Image (RGB)
        self.resized_image = None    # 根據設定尺寸縮放後的圖片
        self.converted_image = None  # 轉換後的 1-bit 圖片 (PIL, mode "1")
        
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
        
        # 預覽區
        self.lbl_preview = tk.Label(self, text="預覽區", bg="gray", width=400, height=300)
        self.lbl_preview.pack(pady=10)
    
    def load_image(self):
        path = filedialog.askopenfilename(title="選取圖片檔",
                                          filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp")])
        if path:
            try:
                # 載入圖片並轉換為 RGB
                self.original_image = Image.open(path).convert("RGB")
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
        preview.thumbnail((400, 300))
        self.preview_photo = ImageTk.PhotoImage(preview)
        self.lbl_preview.config(image=self.preview_photo)
    
    def save_image(self):
        if self.converted_image is None:
            messagebox.showwarning("警告", "請先載入並預覽圖片轉換結果")
            return
        path = filedialog.asksaveasfilename(title="儲存 .bin 檔案",
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
