from __future__ import annotations

import random
from typing import Any
from pathlib import Path
from dataclasses import dataclass, field

import glm
import math
import pyray as pr

SCREEN_WIDTH = 480
SCREEN_HEIGHT = 960

UNIT = 40

GRID_WIDTH = SCREEN_WIDTH // UNIT
GRID_HEIGHT = SCREEN_HEIGHT // UNIT

KEY_RIGHT = getattr(pr, "KEY_D", 68)
KEY_LEFT = getattr(pr, "KEY_A", 65)
KEY_DOWN = getattr(pr, "KEY_S", 83)
KEY_SPACE = getattr(pr, "KEY_SPACE", 32)
KEY_LEFT_ROTATE = getattr(pr, "KEY_Q", 81)
KEY_RIGHT_ROTATE = getattr(pr, "KEY_E", 69)

GAP = 2
PALETTE = [
    pr.Color(0, 0, 0, 255),        # 0: Empty
    pr.Color(0, 220, 255, 255),    # 1: I - Cyan
    pr.Color(255, 210, 0, 255),    # 2: O - Yellow
    pr.Color(180, 70, 255, 255),   # 3: T - Purple
    pr.Color(80, 255, 140, 255),   # 4: S - Green
    pr.Color(255, 60, 90, 255),    # 5: Z - Red
    pr.Color(255, 140, 30, 255),   # 6: L - Orange
    pr.Color(60, 120, 255, 255),   # 7: J - Blue
]
type_arr = ['T', 'O', 'S', 'Z', 'L', 'J', 'I']
shape_map = {
        'T': ((0,0), (0,-1), (-1,0), (1,0)),
        'O': ((0,0), (-1,0), (-1,1), (0,1)),
        'S': ((0,0), (1,0), (0,1), (-1,1)),
        'Z': ((0,0), (-1,0), (0,1), (1,1)),
        'L': ((0,0), (0,-1), (0,1), (1,1)),
        'J': ((0,0), (0,-1), (0,1), (-1,1)),
        'I': ((0,0), (0,-1), (0,1), (0,2)),
        }

low = [0.0, 0.0]
cutoff = 70.0 / 44100.0
k = cutoff / (cutoff + 0.1591549431)

audio_metrics = {"raw_energy": 0.0, "smoothed_energy": 0.0}

def draw_cell(x: int, y: int, color_idx: int, audio_energy: float = 0.0):
    if color_idx <= 0 or color_idx >= len(PALETTE):
        return
    base_color = PALETTE[color_idx]
    px = int(x * UNIT + GAP)
    py = int(y * UNIT + GAP)
    size = UNIT - GAP * 2
    energy_boost = int(audio_energy * 40)
    highlight = pr.Color(
        min(base_color.r + 60 + energy_boost, 255),
        min(base_color.g + 60 + energy_boost, 255),
        min(base_color.b + 60 + energy_boost, 255),
        255
    )
    dark = pr.Color(
        max(base_color.r // 2, 0),
        max(base_color.g // 2, 0),
        max(base_color.b // 2, 0),
        255
    )
    pr.draw_rectangle(px + 3, py + 3, size, size, pr.Color(0, 0, 0, 110))
    pr.draw_rectangle(px, py, size, size, base_color)
    pr.draw_rectangle(px + 2, py + 2, size - 4, 3, highlight)
    pr.draw_rectangle(px + 2, py + 2, 3, size - 4, highlight)
    pr.draw_rectangle(px + 2, py + size - 5, size - 4, 3, dark)
    pr.draw_rectangle(px + size - 5, py + 2, 3, size - 4, dark)
    pr.draw_rectangle_lines_ex(
        pr.Rectangle(px, py, size, size),
        1,
        pr.Color(5, 5, 15, 220)
    )

def draw_ghost_cell(x: int, y: int, color_idx: int):
    if color_idx <= 0 or color_idx >= len(PALETTE):
        return
    base_color = PALETTE[color_idx]
    px = int(x * UNIT + GAP)
    py = int(y * UNIT + GAP)
    size = UNIT - GAP * 2
    ghost_fill = pr.Color(base_color.r, base_color.g, base_color.b, 45)
    pr.draw_rectangle(px, py, size, size, ghost_fill)
    ghost_border = pr.Color(base_color.r, base_color.g, base_color.b, 140)
    pr.draw_rectangle_lines_ex(
        pr.Rectangle(px, py, size, size),
        2,
        ghost_border
    )

@pr.ffi.callback("void(void *, unsigned int)")
def audio_process_effect_lpf(buffer: Any, frames: int) -> None:
    buffer_data = pr.ffi.cast("float *", buffer)

    for i in range(0, frames * 2, 2):
        left = float(buffer_data[i])
        right = float(buffer_data[i + 1])

        low[0] += k * (left - low[0])
        low[1] += k * (right - low[1])

        buffer_data[i] = low[0]
        buffer_data[i + 1] = low[1]

@pr.ffi.callback("void(void *, unsigned int)")
def audio_process_energy(buffer: Any, frames: int) -> None:
    buffer_data = pr.ffi.cast("float *", buffer)
    sq_sum = 0.0
    total_samples = frames * 2
    for i in range(total_samples):
        val = float(buffer_data[i])
        sq_sum += val * val
    audio_metrics["raw_energy"] = math.sqrt(sq_sum / total_samples)

def rotate(x, y, angle):
    rotation = [(x,y), (-y,x), (-x,-y), (y,-x)]
    return rotation[angle % 4]

class Tetris:
    def __init__(self, music):
        self.GAME_STATE = True
        self.score = 0
        self.grid_data = [[ 0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.x = 4
        self.y = 1
        self.rotation = 0 # 0, 1, 2, 3
        self.color_idx = random.randint(1, 6)
        self.type = type_arr[random.randint(0, 6)]

        self.fall_y = self.y

        # animated
        self.x_ren = 4
        self.y_ren = 1

        # music and fx
        self.music = music
        self.music_vol = 0.8

        # mouse
        self.mouse_pos = (pr.get_mouse_x(), pr.get_mouse_y())

    def freeze(self, fx_clear):
        for (dx, dy) in self.get_shape():
            self.grid_data[self.y+dy][self.x+dx] = self.color_idx
        for i in range(GRID_HEIGHT):
            if 0 not in self.grid_data[i]:
                del self.grid_data[i]
                self.grid_data.insert(0, [0 for _ in range(GRID_WIDTH)])
                self.score += 10
                pr.play_sound(fx_clear)

        # update new peices
        self.x = 4
        self.y = 1
        self.rotation = 0
        self.color_idx = random.randint(1, 6)
        self.type = type_arr[random.randint(0, 6)]

        self.fall_y = self.y
        self.score += 4

        if self.collision_check_rotate()["neural"]:
            print("GAME OVER")
            self.GAME_STATE = False
            self.music_vol = 1
            pr.set_music_volume(self.music, self.music_vol)
            pr.attach_audio_stream_processor(self.music.stream, audio_process_effect_lpf)

    def get_shape(self):
        if self.type == 'O':
            return shape_map['O']
        return [rotate(x, y, self.rotation) for x, y in shape_map[self.type]]

    def fall_pos(self):
        max_y = self.y+1
        while True:
            checks_clear = all(0 <= max_y+dy < GRID_HEIGHT and self.grid_data[max_y+dy][self.x+dx] == 0
            for (dx, dy) in self.get_shape())
            if checks_clear:
                max_y += 1
            else:
                break
        return max_y-1

    def collision_check(self):
        collision = {"left": True, "right": True, "down": True, "up": True}
        direction = {"left": (-1,0), "right": (1,0), "down": (0,1), "up": (0,-1)}
        for key, (j, i) in direction.items():
                checks_clear = all(0 <= self.x+dx+j < GRID_WIDTH and 0 <= self.y+dy+i < GRID_HEIGHT
                and self.grid_data[self.y+dy+i][self.x+dx+j] == 0 for (dx, dy) in self.get_shape())
                if checks_clear:
                    collision[key] = False
        return collision

    def collision_check_rotate(self):
        collision = {"left": True, "right": True, "neural": True}
        rotation_dir = {"left": -1, "right": 1, "neural": 0}
        for key, d in rotation_dir.items():
            checks_clear = all(0 <= self.x+x < GRID_WIDTH and 0 <= self.y+y < GRID_HEIGHT
                               and self.grid_data[self.y+y][self.x+x] == 0
                               for (x, y) in [rotate(dx, dy, self.rotation+d) for (dx, dy) in shape_map[self.type]])
            if checks_clear:
                collision[key] = False
        return collision

    def draw_cell(self, x, y, color=0):
        if color == 0: color = PALETTE[self.color_idx]
        cell = pr.Rectangle(x*UNIT, y*UNIT, UNIT, UNIT)
        pr.draw_rectangle_gradient_ex(cell, color, color, pr.DARKGRAY, color)
        self.draw_cell_boxed(x, y, pr.RAYWHITE)

    def draw_cell_boxed(self, x, y, color=0):
        if color == 0: color = PALETTE[self.color_idx]
        cell = pr.Rectangle(x*UNIT, y*UNIT, UNIT, UNIT)
        pr.draw_rectangle_lines_ex(cell, 1, color)


def main() -> None:
    pr.init_window(SCREEN_WIDTH, SCREEN_HEIGHT, "Tetris")
    pr.init_audio_device()
    pr.set_target_fps(120)

    resources = Path(__file__).resolve().parent / "../../resources"
    shader_path = resources / "shaders/reactive.fs"
    shader = pr.load_shader("", str(shader_path))

    musics = [music_path for music_path in (resources / "music").iterdir() if music_path.suffix == ".mp3"]
    music = pr.load_music_stream(str(resources / musics[random.randint(0, len(musics)-1)]))
    fx_set = pr.load_sound(str(resources / "fx/shoot.ogg"))
    fx_clear = pr.load_sound(str(resources / "fx/power-up.ogg"))

    u_energy_loc = pr.get_shader_location(shader, "u_energy")
    u_time_loc = pr.get_shader_location(shader, "u_time")
    target = pr.load_render_texture(SCREEN_WIDTH, SCREEN_HEIGHT)

    pr.play_music_stream(music)
    pr.attach_audio_stream_processor(music.stream, audio_process_energy)

    block = Tetris(music)
    pr.set_music_volume(block.music, block.music_vol)

    base_fall_speed = 1.0
    energy_multiplier = 25.0
    while not pr.window_should_close():
        pr.update_music_stream(music)
        audio_metrics["smoothed_energy"] += (audio_metrics["raw_energy"] - audio_metrics["smoothed_energy"]) * 0.2

        pr.set_shader_value(shader, u_energy_loc, pr.ffi.new("float *", audio_metrics["smoothed_energy"]), pr.SHADER_UNIFORM_FLOAT)
        pr.set_shader_value(shader, u_time_loc, pr.ffi.new("float *", pr.get_time()), pr.SHADER_UNIFORM_FLOAT)

        if block.GAME_STATE:
            dynamic_speed = base_fall_speed + (audio_metrics["smoothed_energy"] * energy_multiplier)
            block.fall_y += pr.get_frame_time() * dynamic_speed
            if block.fall_y > block.y or pr.is_key_pressed(KEY_DOWN):
                if not block.collision_check()["down"]:
                    block.fall_y = block.y
                    block.y += 1
                else:
                    block.freeze(fx_clear)
                    pr.play_sound(fx_set)

            if pr.is_key_pressed(KEY_SPACE) and block.y > 2: # y>2 to prevent accedental drops of new blocks
                block.y = block.fall_pos()
                block.freeze(fx_clear)
                pr.play_sound(fx_set)

            if (pr.is_key_pressed(KEY_RIGHT) or pr.is_key_pressed_repeat(KEY_RIGHT)) and not block.collision_check()["right"]:
                block.x += 1
            elif (pr.is_key_pressed(KEY_LEFT) or pr.is_key_pressed_repeat(KEY_LEFT)) and not block.collision_check()["left"]:
                block.x -= 1

            if (pr.get_mouse_x(), pr.get_mouse_y()) != block.mouse_pos:
                block.mouse_pos = (pr.get_mouse_x(), pr.get_mouse_y())
                target_x = block.mouse_pos[0] // UNIT
                step_dir = 1 if target_x > block.x else -1
                while block.x != target_x:
                    next_x = block.x + step_dir
                    clear = all(0 <= next_x+dx < GRID_WIDTH and block.grid_data[block.y+dy][next_x+dx] == 0 for dx, dy in block.get_shape())
                    if not clear:
                        break
                    block.x = next_x

            if pr.is_key_pressed(KEY_RIGHT_ROTATE) and not block.collision_check_rotate()["right"]:
                block.rotation = (block.rotation + 1) % 4
            elif pr.is_key_pressed(KEY_LEFT_ROTATE) and not block.collision_check_rotate()["left"]:
                block.rotation = (block.rotation - 1) % 4
        else:
            if pr.is_key_pressed(KEY_SPACE): # restart
                block.__init__(music)
                pr.set_music_volume(music, block.music_vol)
                pr.detach_audio_stream_processor(block.music.stream, audio_process_effect_lpf)

        # animations
        if (block.x)  > block.x_ren:
            block.x_ren += abs(block.x - block.x_ren) * pr.get_frame_time() * 10
        elif (block.x) < block.x_ren:
            block.x_ren -= abs(block.x - block.x_ren) * pr.get_frame_time() * 10
        if (block.y)  > block.y_ren:
            block.y_ren += abs(block.y - block.y_ren) * pr.get_frame_time() * 10
        elif (block.y) < block.y_ren:
            block.y_ren -= abs(block.y - block.y_ren) * pr.get_frame_time() * 10

        pr.begin_texture_mode(target)
        pr.clear_background(pr.BLACK)
        for i in range(GRID_HEIGHT):
            for j in range(GRID_WIDTH):
                color_idx = block.grid_data[i][j]
                if color_idx != 0:
                    draw_cell(j, i, color_idx)

        for (dx, dy) in block.get_shape():
            draw_ghost_cell(block.x + dx, block.fall_pos() + dy, block.color_idx)

        for (dx, dy) in block.get_shape():
            draw_cell(block.x_ren + dx, block.y_ren + dy, block.color_idx)

        pr.end_texture_mode()

        pr.begin_drawing()
        pr.clear_background(pr.BLACK)

        pr.begin_shader_mode(shader)
        src_rec = pr.Rectangle(0.0, 0.0, target.texture.width, -target.texture.height)
        dest_rec = pr.Rectangle(0.0, 0.0, SCREEN_WIDTH, SCREEN_HEIGHT)
        pr.draw_texture_pro(target.texture, src_rec, dest_rec, pr.Vector2(0, 0), 0.0, pr.WHITE)
        pr.end_shader_mode()

        if not block.GAME_STATE:
            pr.draw_rectangle(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, pr.Color(0, 0, 0, 200))
            pr.draw_text("GAME OVER", 10, 10, 30, pr.RAYWHITE)
            pr.draw_text(f"SCORE: {block.score}", 10, 45, 30, pr.RAYWHITE)
        else:
            pr.draw_text(f"SCORE: {block.score}", 10, 10, 20, pr.RAYWHITE)

        pr.end_drawing()

    pr.detach_audio_stream_processor(music.stream, audio_process_energy)
    pr.unload_shader(shader)
    pr.unload_render_texture(target)
    pr.unload_music_stream(music)
    pr.unload_sound(fx_set)
    pr.unload_sound(fx_clear)
    pr.close_audio_device()
    pr.close_window()


if __name__ == "__main__":
    main()
