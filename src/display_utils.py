# display_utils.py
import framebuf

def get_pixel(buf, x, y, width):
    bytes_per_line = width // 8
    index = (x // 8) + y * bytes_per_line
    bit = 7 - (x % 8)
    return 0 if ((buf[index] >> bit) & 0x01) == 0 else 1

def set_pixel(buf, x, y, width, color):
    bytes_per_line = width // 8
    index = (x // 8) + y * bytes_per_line
    bit = 7 - (x % 8)
    if color == 0:
        buf[index] &= ~(1 << bit)
    else:
        buf[index] |= (1 << bit)

def rotate_buffer_270(src, src_width, src_height):
    dest_width = src_height
    dest = bytearray(len(src))
    for i in range(len(dest)):
        dest[i] = 0xff
    for y in range(src_height):
        for x in range(src_width):
            dx = (src_height - 1) - y
            dy = x
            pixel = get_pixel(src, x, y, src_width)
            set_pixel(dest, dx, dy, dest_width, pixel)
    return dest

def rotate_buffer_180(src, src_width, src_height):
    dest = bytearray(len(src))
    for i in range(len(dest)):
        dest[i] = 0xff
    for y in range(src_height):
        for x in range(src_width):
            dx = (src_width - 1) - x
            dy = (src_height - 1) - y
            pixel = get_pixel(src, x, y, src_width)
            set_pixel(dest, dx, dy, src_width, pixel)
    return dest

def rotate_buffer_90_clockwise(src, src_width, src_height):
    dest_width = src_height
    dest = bytearray(len(src))
    for i in range(len(dest)):
        dest[i] = 0xff
    for y in range(src_height):
        for x in range(src_width):
            dx = y
            dy = (src_width - 1) - x
            pixel = get_pixel(src, x, y, src_width)
            set_pixel(dest, dx, dy, dest_width, pixel)
    return dest

def rotate_buffer(src, src_width, src_height, angle):
    if angle == 90:
        return rotate_buffer_90_clockwise(src, src_width, src_height)
    elif angle == 180:
        return rotate_buffer_180(src, src_width, src_height)
    elif angle == 270:
        return rotate_buffer_270(src, src_width, src_height)
    else:
        raise ValueError("Unsupported rotation angle")

def draw_scaled_text(canvas, text, x, y, scale, color=0):
    orig_char_width = 8
    orig_char_height = 8
    orig_width = len(text) * orig_char_width
    orig_height = orig_char_height

    temp_buf = bytearray((orig_width * orig_height) // 8)
    temp_fb = framebuf.FrameBuffer(temp_buf, orig_width, orig_height, framebuf.MONO_HLSB)
    temp_fb.fill(0xff)
    temp_fb.text(text, 0, 0, color)

    scaled_width = orig_width * scale
    scaled_height = orig_height * scale
    scaled_buf = bytearray((scaled_width * scaled_height) // 8)
    for i in range(len(scaled_buf)):
        scaled_buf[i] = 0xff

    for py in range(orig_height):
        for px in range(orig_width):
            p = temp_fb.pixel(px, py)
            if p == 0:
                for sy in range(scale):
                    for sx in range(scale):
                        set_pixel(scaled_buf, px * scale + sx, py * scale + sy, scaled_width, 0)
    scaled_fb = framebuf.FrameBuffer(scaled_buf, scaled_width, scaled_height, framebuf.MONO_HLSB)
    canvas.blit(scaled_fb, x, y)

def draw_image(canvas, image_path, src_width, src_height, x, y):
    try:
        with open(image_path, "rb") as f:
            img_data = f.read()
        expected_length = (src_width * src_height) // 8
        if len(img_data) != expected_length:
            print(f"圖片資料長度不符: {image_path}。預期長度: {expected_length}, 實際長度: {len(img_data)}")
            return
        img_fb = framebuf.FrameBuffer(bytearray(img_data), src_width, src_height, framebuf.MONO_HLSB)
        canvas.blit(img_fb, x, y)
    except OSError as e:
        print(f"讀取圖片檔案失敗: {image_path} - {e}")
    except Exception as e:
        print(f"處理圖片時發生未知錯誤: {image_path} - {e}")

def clear_region(canvas, x1, y1, x2, y2):
    width = x2 - x1
    height = y2 - y1
    canvas.fill_rect(x1, y1, width, height, 1)

def display_rotated_screen(draw_callback, angle=90, partial_update=False):
    import framebuf
    from epaper import EPD_2in9
    if angle in [90, 270]:
        canvas_width = 296
        canvas_height = 128
    elif angle == 180:
        canvas_width = 128
        canvas_height = 296
    else:
        raise ValueError("不支援此旋轉角度")
    canvas_buf = bytearray(canvas_width * canvas_height // 8)
    canvas = framebuf.FrameBuffer(canvas_buf, canvas_width, canvas_height, framebuf.MONO_HLSB)
    for i in range(len(canvas_buf)):
        canvas_buf[i] = 0xff
    draw_callback(canvas)
    native_buf = rotate_buffer(canvas_buf, canvas_width, canvas_height, angle)
    epd = EPD_2in9()
    epd.init()
    
    if partial_update:
        epd.display_Partial(native_buf)
    else:
        epd.display_Base(native_buf)