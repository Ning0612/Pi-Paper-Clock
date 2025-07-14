# display_manager.py
from display_utils import draw_scaled_text, draw_image, display_rotated_screen
from netutils import get_local_time
from file_manager import list_files, get_image_path

def update_page_weather(current_weather, weather_forecast, display_image_path, partial_update):
    def draw(canvas):
        t = get_local_time()
        date_str = "{:02d}/{:02d}".format(t[1], t[2])
        time_str = "{:02d}:{:02d}".format(t[3], t[4])
        
        if weather_forecast[0][0][-2:] != str(t[2]):
            weather_forecast.insert(0, ("{:02d}-{:02d}".format(t[1], t[2]), current_weather[0], current_weather[1], -1))
            
        draw_scaled_text(canvas, date_str, 3, 10, 3, 0)
        draw_scaled_text(canvas, time_str, 3, 40, 3, 0)
        
        if current_weather and current_weather[1] != "Unknown":
            weather_icon_path = "/image/weather_icons/{}.bin".format(current_weather[1])
            draw_image(canvas, weather_icon_path, 32, 32, 130, 0)
            draw_scaled_text(canvas, "{:02d}".format(int(current_weather[0])), 130, 32, 2, 0)
            draw_scaled_text(canvas, "o", 157, 25, 1, 0)
            
        if weather_forecast and weather_forecast[0][3] >= 0:
            draw_scaled_text(canvas, "{}%".format(int(weather_forecast[0][3])), 133, 53, 1, 0)
            
        if weather_forecast:
            offset = 0
            for weather in weather_forecast[1:5]:
                icon_path = "/image/weather_icons/{}.bin".format(weather[2])
                draw_image(canvas, icon_path, 32, 32, 8 + offset, 80)
                draw_scaled_text(canvas, "{:02d}".format(int(weather[1])), 15 + offset, 72, 1, 0)
                draw_scaled_text(canvas, "o", 30 + offset, 67, 1, 0)
                draw_scaled_text(canvas, "{}%".format(int(weather[3])), 15 + offset, 115, 1, 0)
                offset += 40
                
        draw_image(canvas, display_image_path, 128, 128, 168, 0)
        
    display_rotated_screen(draw, angle=90, partial_update=partial_update)

def update_page_time_image(display_image_path, partial_update):
    def draw(canvas):
        t = get_local_time()
        date_str = "{:02d}/{:02d}".format(t[1], t[2])
        time_str = "{:02d}:{:02d}".format(t[3], t[4])
        draw_scaled_text(canvas, date_str, 3, 20, 4, 0)
        draw_scaled_text(canvas, time_str, 3, 70, 4, 0)
        draw_image(canvas, display_image_path, 128, 128, 168, 0)
    display_rotated_screen(draw, angle=90, partial_update=partial_update)


def update_page_birthday(partial_update):
    def draw(canvas):
        t = get_local_time()
        date_str = "{:02d}/{:02d}".format(t[1], t[2])
        time_str = "{:02d}:{:02d}".format(t[3], t[4])
        draw_scaled_text(canvas, date_str, 3, 10, 4, 0)
        draw_scaled_text(canvas, time_str, 3, 44, 4, 0)
        draw_scaled_text(canvas, "Happy", 15, 80, 2, 0)
        draw_scaled_text(canvas, "Birthday!", 15, 100, 2, 0)

        image_dir = "/image/events/birthday"
        file_list = list_files(image_dir)
        image_path = get_image_path(image_dir, file_list, offset=0)
        if image_path:
            draw_image(canvas, image_path, 128, 128, 168, 0)
        else:
            draw_scaled_text(canvas, "No image", 20, 140, 2, 0)
            
    display_rotated_screen(draw, angle=90, partial_update=partial_update)


def update_page_loading(partial_update):
    def draw(canvas):
        image_dir = "/image/login"
        file_list = list_files(image_dir)
        image_path = get_image_path(image_dir, file_list, offset=0)
        if image_path:
            draw_image(canvas, image_path, 296, 128, 0, 0)
        else:
            draw_scaled_text(canvas, "No image", 20, 20, 2, 0)
    display_rotated_screen(draw, angle=90, partial_update=partial_update)