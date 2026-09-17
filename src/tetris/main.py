from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

import pyray as pr

GAME_WIDTH = 480
GAME_HEIGHT = 960
UNIT = 48

GRID_WIDTH = GAME_WIDTH // UNIT
GRID_HEIGHT = GAME_HEIGHT // UNIT

SETTINGS_FILE = Path("settings.json")

DEFAULT_KEYBINDINGS = {
    "Move Left": getattr(pr, "KEY_A", 65),
    "Move Right": getattr(pr, "KEY_D", 68),
    "Soft Drop": getattr(pr, "KEY_S", 83),
    "Hard Drop": getattr(pr, "KEY_SPACE", 32),
    "Rotate Left": getattr(pr, "KEY_Q", 81),
    "Rotate Right": getattr(pr, "KEY_E", 69),
    "Pause Game": getattr(pr, "KEY_P", 80),
}

KEY_NAMES = {
    65: "A", 68: "D", 83: "S", 87: "W", 81: "Q", 69: "E", 80: "P", 77: "M", 79: "O",
    32: "SPACE", 256: "ESC", 262: "RIGHT", 263: "LEFT", 264: "DOWN", 265: "UP",
}

GAP = 2

COLOR_TETO_RED = pr.Color(255, 42, 75, 255)
COLOR_TETO_YELLOW = pr.Color(255, 230, 0, 255)
COLOR_TETO_DARK = pr.Color(24, 12, 16, 235)
COLOR_TETO_ACCENT = pr.Color(255, 90, 40, 255)

PALETTE = [
    pr.Color(0, 0, 0, 255),
    pr.Color(255, 60, 90, 255),
    COLOR_TETO_YELLOW,
    pr.Color(210, 40, 90, 255),
    pr.Color(255, 180, 0, 255),
    COLOR_TETO_RED,
    pr.Color(255, 120, 30, 255),
    pr.Color(190, 20, 60, 255),
]

type_arr = ["T", "O", "S", "Z", "L", "J", "I"]
shape_map = {
    "T": ((0, 0), (0, -1), (-1, 0), (1, 0)),
    "O": ((0, 0), (-1, 0), (-1, 1), (0, 1)),
    "S": ((0, 0), (1, 0), (0, 1), (-1, 1)),
    "Z": ((0, 0), (-1, 0), (0, 1), (1, 1)),
    "L": ((0, 0), (0, -1), (0, 1), (1, 1)),
    "J": ((0, 0), (0, -1), (0, 1), (-1, 1)),
    "I": ((0, 0), (0, -1), (0, 1), (0, 2)),
}

audio_state = {
    "lpf_state": [0.0, 0.0],
    "lpf_alpha": 0.06,
    "raw_energy": 0.0,
    "smoothed_energy": 0.0,
}


@pr.ffi.callback("void(void *, unsigned int)")
def combined_audio_processor(buffer: Any, frames: int) -> None:
    buffer_data = pr.ffi.cast("float *", buffer)
    sq_sum = 0.0
    total_samples = frames * 2
    l_filt = audio_state["lpf_state"][0]
    r_filt = audio_state["lpf_state"][1]
    alpha = audio_state["lpf_alpha"]

    for i in range(0, total_samples, 2):
        l_raw = float(buffer_data[i])
        r_raw = float(buffer_data[i + 1])

        l_filt += alpha * (l_raw - l_filt)
        r_filt += alpha * (r_raw - r_filt)

        buffer_data[i] = l_filt
        buffer_data[i + 1] = r_filt

        sq_sum += (l_filt * l_filt) + (r_filt * r_filt)

    audio_state["lpf_state"][0] = l_filt
    audio_state["lpf_state"][1] = r_filt
    audio_state["raw_energy"] = math.sqrt(sq_sum / total_samples)


def get_key_name(key_code: int) -> str:
    if key_code in KEY_NAMES:
        return KEY_NAMES[key_code]
    if 32 <= key_code <= 126:
        return chr(key_code).upper()
    return f"KEY_{key_code}"

def load_user_settings() -> dict[str, Any]:
    defaults = {
        "master_vol": 0.8,
        "music_vol": 0.8,
        "sfx_vol": 0.8,
        "muffle_vol": 0.20,
        "keybindings": DEFAULT_KEYBINDINGS.copy(),
    }
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                defaults["master_vol"] = data.get("master_vol", defaults["master_vol"])
                defaults["music_vol"] = data.get("music_vol", defaults["music_vol"])
                defaults["sfx_vol"] = data.get("sfx_vol", defaults["sfx_vol"])
                defaults["muffle_vol"] = data.get("muffle_vol", defaults["muffle_vol"])
                if "keybindings" in data and isinstance(data["keybindings"], dict):
                    defaults["keybindings"].update(data["keybindings"])
        except Exception:
            pass
    return defaults

def draw_cell(x: float, y: float, color_idx: int, audio_energy: float = 0.0):
    if color_idx <= 0 or color_idx >= len(PALETTE):
        return
    base_color = PALETTE[color_idx]
    px = int(x * UNIT + GAP)
    py = int(y * UNIT + GAP)
    size = UNIT - GAP * 2
    energy_boost = int(audio_energy * 40)
    highlight = pr.Color(
        min(base_color.r + 50 + energy_boost, 255),
        min(base_color.g + 50 + energy_boost, 255),
        min(base_color.b + 50 + energy_boost, 255),
        255,
    )
    dark = pr.Color(
        max(base_color.r // 2, 0),
        max(base_color.g // 2, 0),
        max(base_color.b // 2, 0),
        255,
    )
    pr.draw_rectangle(px + 3, py + 3, size, size, pr.Color(0, 0, 0, 110))
    pr.draw_rectangle(px, py, size, size, base_color)
    pr.draw_rectangle(px + 2, py + 2, size - 4, 3, highlight)
    pr.draw_rectangle(px + 2, py + 2, 3, size - 4, highlight)
    pr.draw_rectangle(px + 2, py + size - 5, size - 4, 3, dark)
    pr.draw_rectangle(px + size - 5, py + 2, 3, size - 4, dark)
    pr.draw_rectangle_lines_ex(
        pr.Rectangle(px, py, size, size), 1, pr.Color(20, 5, 10, 220)
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
    ghost_border = pr.Color(base_color.r, base_color.g, base_color.b, 160)
    pr.draw_rectangle_lines_ex(
        pr.Rectangle(px, py, size, size), 2, ghost_border
    )


def rotate(x: int, y: int, angle: int):
    rotation = [(x, y), (-y, x), (-x, -y), (y, -x)]
    return rotation[angle % 4]


class Tetris:

    def __init__(self, music, fx_set, fx_clear):
        self.game_state = "MENU"
        self.previous_state = "MENU"
        self.score = 0
        self.grid_data = [
            [0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)
        ]
        self.x = 4
        self.y = 1
        self.rotation = 0
        self.type = type_arr[random.randint(0, 6)]
        self.color_idx = (
            2 if self.type == "O" else random.choice([1, 3, 4, 5, 6, 7])
        )

        self.fall_y = float(self.y)
        self.x_ren = float(self.x)
        self.y_ren = float(self.y)

        self.music = music
        self.fx_set = fx_set
        self.fx_clear = fx_clear

        saved = load_user_settings()
        self.vol_master = saved["master_vol"]
        self.vol_music = saved["music_vol"]
        self.vol_sfx = saved["sfx_vol"]
        self.vol_muffle = saved["muffle_vol"]
        self.keybindings = saved["keybindings"]

        self.settings_selected = 0
        self.keybind_selected = 0
        self.in_keybind_menu = False
        self.rebinding = False

        self.mouse_pos = (0, 0)
        self.impact_trigger = False
        self.clear_trigger = False
        self.clear_row_uv = 0.5

    def save_settings(self):
        data = {
            "master_vol": self.vol_master,
            "music_vol": self.vol_music,
            "sfx_vol": self.vol_sfx,
            "muffle_vol": self.vol_muffle,
            "keybindings": self.keybindings,
        }
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def update_volumes(self):
        pr.set_music_volume(self.music, self.vol_master * self.vol_music)
        pr.set_sound_volume(self.fx_set, self.vol_master * self.vol_sfx)
        pr.set_sound_volume(self.fx_clear, self.vol_master * self.vol_sfx)

    def play_sfx(self, sound):
        pr.set_sound_volume(sound, self.vol_master * self.vol_sfx)
        pr.play_sound(sound)

    def reset_grid(self):
        self.score = 0
        self.grid_data = [
            [0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)
        ]
        self.x = 4
        self.y = 1
        self.rotation = 0
        self.type = type_arr[random.randint(0, 6)]
        self.color_idx = (
            2 if self.type == "O" else random.choice([1, 3, 4, 5, 6, 7])
        )
        self.fall_y = float(self.y)
        self.x_ren = float(self.x)
        self.y_ren = float(self.y)

    def freeze(self):
        for dx, dy in self.get_shape():
            gx, gy = self.x + dx, self.y + dy
            if 0 <= gx < GRID_WIDTH and 0 <= gy < GRID_HEIGHT:
                self.grid_data[gy][gx] = self.color_idx

        self.impact_trigger = True

        cleared_rows = []
        for i in range(GRID_HEIGHT):
            if 0 not in self.grid_data[i]:
                cleared_rows.append(i)

        for i in cleared_rows:
            del self.grid_data[i]
            self.grid_data.insert(0, [0 for _ in range(GRID_WIDTH)])
            self.score += 10

        if cleared_rows:
            self.play_sfx(self.fx_clear)
            self.clear_trigger = True
            avg_y = sum(cleared_rows) / len(cleared_rows)
            self.clear_row_uv = (avg_y + 0.5) / GRID_HEIGHT

        self.x = 4
        self.y = 1
        self.rotation = 0
        self.type = type_arr[random.randint(0, 6)]
        self.color_idx = (
            2 if self.type == "O" else random.choice([1, 3, 4, 5, 6, 7])
        )

        self.fall_y = float(self.y)
        self.score += 4

        if self.collision_check_rotate()["neural"]:
            self.game_state = "GAMEOVER"
            self.update_volumes()

    def get_shape(self):
        if self.type == "O":
            return shape_map["O"]
        return [rotate(x, y, self.rotation) for x, y in shape_map[self.type]]

    def fall_pos(self):
        max_y = self.y + 1
        while True:
            checks_clear = all(
                0 <= max_y + dy < GRID_HEIGHT
                and 0 <= self.x + dx < GRID_WIDTH
                and self.grid_data[max_y + dy][self.x + dx] == 0
                for (dx, dy) in self.get_shape()
            )
            if checks_clear:
                max_y += 1
            else:
                break
        return max_y - 1

    def collision_check(self):
        collision = {"left": True, "right": True, "down": True, "up": True}
        direction = {
            "left": (-1, 0),
            "right": (1, 0),
            "down": (0, 1),
            "up": (0, -1),
        }
        for key, (j, i) in direction.items():
            checks_clear = all(
                0 <= self.x + dx + j < GRID_WIDTH
                and 0 <= self.y + dy + i < GRID_HEIGHT
                and self.grid_data[self.y + dy + i][self.x + dx + j] == 0
                for (dx, dy) in self.get_shape()
            )
            if checks_clear:
                collision[key] = False
        return collision

    def collision_check_rotate(self):
        collision = {"left": True, "right": True, "neural": True}
        rotation_dir = {"left": 1, "right": -1, "neural": 0}
        for key, d in rotation_dir.items():
            checks_clear = all(
                0 <= self.x + x < GRID_WIDTH
                and 0 <= self.y + y < GRID_HEIGHT
                and self.grid_data[self.y + y][self.x + x] == 0
                for (x, y) in [
                    rotate(dx, dy, self.rotation + d)
                    for (dx, dy) in shape_map[self.type]
                ]
            )
            if checks_clear:
                collision[key] = False
        return collision


def draw_panel(x: int, y: int, width: int, height: int, title: str = ""):
    pr.draw_rectangle(x, y, width, height, COLOR_TETO_DARK)
    pr.draw_rectangle_lines_ex(
        pr.Rectangle(x, y, width, height), 2, COLOR_TETO_RED
    )
    if title:
        tw = pr.measure_text(title, 24)
        pr.draw_rectangle(
            x + (width - tw) // 2 - 12, y - 14, tw + 24, 28, COLOR_TETO_DARK
        )
        pr.draw_rectangle_lines_ex(
            pr.Rectangle(x + (width - tw) // 2 - 12, y - 14, tw + 24, 28),
            1,
            COLOR_TETO_YELLOW,
        )
        pr.draw_text(
            title, x + (width - tw) // 2, y - 10, 24, COLOR_TETO_YELLOW
        )


def draw_slider(
    x: int, y: int, width: int, label: str, val: float, selected: bool
):
    color_hdr = COLOR_TETO_YELLOW if selected else pr.LIGHTGRAY
    pr.draw_text(label, x, y, 18, color_hdr)

    val_str = f"{int(val * 100)}%"
    pr.draw_text(val_str, x + width - 45, y, 18, color_hdr)

    bar_y = y + 26
    bar_h = 10
    pr.draw_rectangle(x, bar_y, width, bar_h, pr.Color(40, 20, 28, 255))
    pr.draw_rectangle(
        x,
        bar_y,
        int(width * val),
        bar_h,
        COLOR_TETO_RED if selected else pr.Color(180, 40, 60, 200),
    )
    pr.draw_rectangle_lines_ex(
        pr.Rectangle(x, bar_y, width, bar_h), 1, pr.GRAY
    )

    handle_x = x + int(width * val) - 4
    pr.draw_rectangle(handle_x, bar_y - 3, 8, bar_h + 6, COLOR_TETO_YELLOW)


def main() -> None:
    pr.set_config_flags(pr.FLAG_WINDOW_RESIZABLE)
    pr.init_window(GAME_WIDTH, GAME_HEIGHT, "TETORIS")
    pr.set_exit_key(0)
    pr.init_audio_device()
    pr.set_target_fps(120)

    resources = Path(__file__).resolve().parent / "../../resources"
    shader_path = resources / "shaders/reactive.fs"
    shader = pr.load_shader("", str(shader_path))

    music_dir = resources / "music"
    musics_paths = (
        sorted([p for p in music_dir.iterdir() if p.suffix == ".mp3"])
        if music_dir.exists()
        else []
    )
    current_song_idx = (
        random.randrange(len(musics_paths)) if musics_paths else 0
    )

    music = (
        pr.load_music_stream(str(musics_paths[current_song_idx]))
        if musics_paths
        else None
    )
    fx_set = pr.load_sound(str(resources / "fx/shoot.ogg"))
    fx_clear = pr.load_sound(str(resources / "fx/power-up.ogg"))

    u_energy_loc = pr.get_shader_location(shader, "u_energy")
    u_time_loc = pr.get_shader_location(shader, "u_time")
    u_impactPulse_loc = pr.get_shader_location(shader, "u_impactPulse")
    u_clearPulse_loc = pr.get_shader_location(shader, "u_clearPulse")
    u_clearRowY_loc = pr.get_shader_location(shader, "u_clearRowY")

    grid_target = pr.load_render_texture(GAME_WIDTH, GAME_HEIGHT)
    ui_target = pr.load_render_texture(GAME_WIDTH, GAME_HEIGHT)

    if music:
        pr.play_music_stream(music)
        pr.attach_audio_stream_processor(
            music.stream, combined_audio_processor
        )

    block = Tetris(music, fx_set, fx_clear)
    block.update_volumes()

    beat_avg_energy = 0.04
    beat_cooldown = 0.0
    beat_pulse = 0.0
    impact_pulse = 0.0
    clear_pulse = 0.0

    marquee_offset = 0.0
    marquee_speed = 40.0

    def change_track(new_idx: int):
        nonlocal current_song_idx, music
        if not musics_paths:
            return
        if music:
            pr.detach_audio_stream_processor(
                music.stream, combined_audio_processor
            )
            pr.unload_music_stream(music)

        current_song_idx = new_idx % len(musics_paths)
        music = pr.load_music_stream(str(musics_paths[current_song_idx]))
        block.music = music
        pr.play_music_stream(music)
        block.update_volumes()
        pr.attach_audio_stream_processor(
            music.stream, combined_audio_processor
        )

    def start_gameplay():
        block.reset_grid()
        block.game_state = "PLAYING"
        block.update_volumes()
        if music:
            pr.resume_music_stream(music)
            pr.seek_music_stream(music, 0.0)

    while not pr.window_should_close():
        dt = pr.get_frame_time()
        if music:
            pr.update_music_stream(music)

        screen_w = pr.get_screen_width()
        screen_h = pr.get_screen_height()
        scale = min(screen_w / GAME_WIDTH, screen_h / GAME_HEIGHT)

        render_w = GAME_WIDTH * scale
        render_h = GAME_HEIGHT * scale
        offset_x = (screen_w - render_w) / 2.0
        offset_y = (screen_h - render_h) / 2.0

        if block.game_state == "PLAYING":
            audio_state["lpf_alpha"] = 1.0 - (block.vol_muffle * 0.94)
        else:
            audio_state["lpf_alpha"] = 0.06

        bass_energy = audio_state["raw_energy"]
        audio_state["smoothed_energy"] += (
            bass_energy - audio_state["smoothed_energy"]
        ) * (dt * 12.0)
        beat_avg_energy += (bass_energy - beat_avg_energy) * (dt * 1.5)

        beat_cooldown -= dt

        if (
            bass_energy > (beat_avg_energy * 1.35 + 0.012)
            and beat_cooldown <= 0.0
        ):
            beat_pulse = 1.0
            beat_cooldown = 0.18
        else:
            beat_pulse = max(0.0, beat_pulse - dt * 4.5)

        impact_pulse = max(0.0, impact_pulse - dt * 3.5)
        clear_pulse = max(0.0, clear_pulse - dt * 3.0)

        if block.impact_trigger:
            impact_pulse = 1.0
            block.impact_trigger = False

        if block.clear_trigger:
            clear_pulse = 1.0
            block.clear_trigger = False

        pr.set_shader_value(
            shader,
            u_energy_loc,
            pr.ffi.new("float *", beat_pulse),
            pr.SHADER_UNIFORM_FLOAT,
        )
        pr.set_shader_value(
            shader,
            u_time_loc,
            pr.ffi.new("float *", pr.get_time()),
            pr.SHADER_UNIFORM_FLOAT,
        )
        pr.set_shader_value(
            shader,
            u_impactPulse_loc,
            pr.ffi.new("float *", impact_pulse),
            pr.SHADER_UNIFORM_FLOAT,
        )
        pr.set_shader_value(
            shader,
            u_clearPulse_loc,
            pr.ffi.new("float *", clear_pulse),
            pr.SHADER_UNIFORM_FLOAT,
        )
        pr.set_shader_value(
            shader,
            u_clearRowY_loc,
            pr.ffi.new("float *", block.clear_row_uv),
            pr.SHADER_UNIFORM_FLOAT,
        )

        kb = block.keybindings
        k_left = kb["Move Left"]
        k_right = kb["Move Right"]
        k_down = kb["Soft Drop"]
        k_drop = kb["Hard Drop"]
        k_rot_l = kb["Rotate Left"]
        k_rot_r = kb["Rotate Right"]
        k_pause = kb["Pause Game"]

        if pr.is_key_pressed(k_pause) and not block.rebinding:
            if block.game_state == "PLAYING":
                block.game_state = "PAUSED"
                if music:
                    pr.pause_music_stream(music)
            elif block.game_state == "PAUSED":
                block.game_state = "PLAYING"
                if music:
                    pr.resume_music_stream(music)

        elif pr.is_key_pressed(getattr(pr, "KEY_ESCAPE", 256)):
            if block.rebinding:
                block.rebinding = False
            elif block.in_keybind_menu:
                block.in_keybind_menu = False
            elif block.game_state == "SETTINGS":
                block.game_state = block.previous_state
            elif block.game_state == "PLAYING":
                block.game_state = "PAUSED"
                if music:
                    pr.pause_music_stream(music)
            elif block.game_state == "PAUSED":
                block.game_state = "PLAYING"
                if music:
                    pr.resume_music_stream(music)

        if block.game_state == "MENU":
            if pr.is_key_pressed(k_right) or pr.is_key_pressed(262):
                change_track(current_song_idx + 1)
            elif pr.is_key_pressed(k_left) or pr.is_key_pressed(263):
                change_track(current_song_idx - 1)

            if pr.is_key_pressed(k_drop):
                start_gameplay()
            elif pr.is_key_pressed(getattr(pr, "KEY_O", 79)):
                block.previous_state = "MENU"
                block.game_state = "SETTINGS"
                block.in_keybind_menu = False

        elif block.game_state == "SETTINGS":
            keys_list = list(block.keybindings.keys())
            total_kb_items = len(keys_list) + 1

            if block.rebinding:
                key_pressed = pr.get_key_pressed()
                if key_pressed > 0:
                    if key_pressed != getattr(pr, "KEY_ESCAPE", 256):
                        target_key = keys_list[block.keybind_selected]
                        block.keybindings[target_key] = key_pressed
                    block.rebinding = False
                    block.save_settings()

            elif block.in_keybind_menu:
                if pr.is_key_pressed(264) or pr.is_key_pressed(83):
                    block.keybind_selected = (
                        block.keybind_selected + 1
                    ) % total_kb_items
                elif pr.is_key_pressed(265) or pr.is_key_pressed(87):
                    block.keybind_selected = (
                        block.keybind_selected - 1
                    ) % total_kb_items

                if pr.is_key_pressed(32) or pr.is_key_pressed(257):
                    if block.keybind_selected == len(keys_list):
                        block.keybindings = DEFAULT_KEYBINDINGS.copy()
                        block.save_settings()
                    else:
                        block.rebinding = True

            else:
                if pr.is_key_pressed(264) or pr.is_key_pressed(83):
                    block.settings_selected = (block.settings_selected + 1) % 5
                elif pr.is_key_pressed(265) or pr.is_key_pressed(87):
                    block.settings_selected = (block.settings_selected - 1) % 5

                if block.settings_selected == 4:
                    if pr.is_key_pressed(32) or pr.is_key_pressed(257):
                        block.in_keybind_menu = True
                        block.keybind_selected = 0
                else:
                    delta_val = 0.0
                    if pr.is_key_pressed(262) or pr.is_key_pressed(68):
                        delta_val = 0.05
                    elif pr.is_key_pressed(263) or pr.is_key_pressed(65):
                        delta_val = -0.05

                    if delta_val != 0.0:
                        if block.settings_selected == 0:
                            block.vol_master = max(
                                0.0, min(1.0, block.vol_master + delta_val)
                            )
                        elif block.settings_selected == 1:
                            block.vol_music = max(
                                0.0, min(1.0, block.vol_music + delta_val)
                            )
                        elif block.settings_selected == 2:
                            block.vol_sfx = max(
                                0.0, min(1.0, block.vol_sfx + delta_val)
                            )
                        elif block.settings_selected == 3:
                            block.vol_muffle = max(
                                0.0, min(1.0, block.vol_muffle + delta_val)
                            )
                        block.update_volumes()
                        block.save_settings()

        elif block.game_state == "PAUSED":
            if pr.is_key_pressed(k_drop):
                block.game_state = "PLAYING"
                if music:
                    pr.resume_music_stream(music)
            elif pr.is_key_pressed(getattr(pr, "KEY_O", 79)):
                block.previous_state = "PAUSED"
                block.game_state = "SETTINGS"
                block.in_keybind_menu = False
            elif pr.is_key_pressed(getattr(pr, "KEY_M", 77)):
                block.game_state = "MENU"
                if music:
                    pr.resume_music_stream(music)

        elif block.game_state == "PLAYING":
            block.fall_y += dt
            if beat_pulse > 0.8 and beat_cooldown >= 0.15:
                block.fall_y += 0.8
            if block.fall_y > block.y or pr.is_key_pressed(k_down):
                if not block.collision_check()["down"]:
                    block.fall_y = float(block.y)
                    block.y += 1
                else:
                    block.freeze()
                    block.play_sfx(fx_set)

            if pr.is_key_pressed(k_drop) and block.y > 1:
                block.y = block.fall_pos()
                block.freeze()
                block.play_sfx(fx_set)

            if (
                pr.is_key_pressed(k_right)
                or pr.is_key_pressed_repeat(k_right)
            ) and not block.collision_check()["right"]:
                block.x += 1
            elif (
                pr.is_key_pressed(k_left) or pr.is_key_pressed_repeat(k_left)
            ) and not block.collision_check()["left"]:
                block.x -= 1

            raw_mx = pr.get_mouse_x()
            raw_my = pr.get_mouse_y()
            local_mx = int((raw_mx - offset_x) / scale)
            local_my = int((raw_my - offset_y) / scale)

            if (local_mx, local_my) != block.mouse_pos:
                block.mouse_pos = (local_mx, local_my)
                target_x = max(
                    0, min(GRID_WIDTH - 1, block.mouse_pos[0] // UNIT)
                )
                step_dir = 1 if target_x > block.x else -1
                while block.x != target_x:
                    next_x = block.x + step_dir
                    clear = all(
                        0 <= next_x + dx < GRID_WIDTH
                        and 0 <= block.y + dy < GRID_HEIGHT
                        and block.grid_data[block.y + dy][next_x + dx] == 0
                        for dx, dy in block.get_shape()
                    )
                    if not clear:
                        break
                    block.x = next_x

            if (
                pr.is_key_pressed(k_rot_l)
                and not block.collision_check_rotate()["left"]
            ):
                block.rotation = (block.rotation + 1) % 4
            elif (
                pr.is_key_pressed(k_rot_r)
                and not block.collision_check_rotate()["right"]
            ):
                block.rotation = (block.rotation - 1) % 4

        elif block.game_state == "GAMEOVER":
            if pr.is_key_pressed(k_drop):
                start_gameplay()
            elif pr.is_key_pressed(getattr(pr, "KEY_M", 77)):
                block.game_state = "MENU"
                if music:
                    pr.resume_music_stream(music)

        if block.x > block.x_ren:
            block.x_ren += abs(block.x - block.x_ren) * pr.get_frame_time() * 10
        elif block.x < block.x_ren:
            block.x_ren -= abs(block.x - block.x_ren) * pr.get_frame_time() * 10
        if block.y > block.y_ren:
            block.y_ren += abs(block.y - block.y_ren) * pr.get_frame_time() * 10
        elif block.y < block.y_ren:
            block.y_ren -= abs(block.y - block.y_ren) * pr.get_frame_time() * 10

        pr.begin_texture_mode(grid_target)
        pr.clear_background(pr.BLACK)
        for i in range(GRID_HEIGHT):
            for j in range(GRID_WIDTH):
                color_idx = block.grid_data[i][j]
                if color_idx != 0:
                    draw_cell(j, i, color_idx)

        if block.game_state in ["PLAYING", "PAUSED"]:
            for dx, dy in block.get_shape():
                draw_ghost_cell(
                    block.x + dx, block.fall_pos() + dy, block.color_idx
                )

            for dx, dy in block.get_shape():
                draw_cell(
                    block.x_ren + dx, block.y_ren + dy, block.color_idx
                )

        pr.end_texture_mode()

        pr.begin_texture_mode(ui_target)
        pr.clear_background(pr.Color(0, 0, 0, 0))

        if block.game_state == "MENU":
            pr.draw_rectangle(
                0, 0, GAME_WIDTH, GAME_HEIGHT, pr.Color(12, 6, 8, 200)
            )
            draw_panel(40, 220, 400, 520, "TETORIS")

            song_name = (
                musics_paths[current_song_idx].stem
                if musics_paths
                else "No Tracks Found"
            )
            raw_label = f"< {song_name} >"
            font_size = 18
            text_w = pr.measure_text(raw_label, font_size)

            panel_x, panel_w = 40, 400
            max_visible_w = panel_w - 60
            clip_x = panel_x + 30
            clip_y = 285

            if text_w > max_visible_w:
                marquee_offset += dt * marquee_speed
                loop_w = text_w + 50
                if marquee_offset >= loop_w:
                    marquee_offset -= loop_w

                pr.begin_scissor_mode(clip_x, clip_y, max_visible_w, 30)
                draw_x = clip_x - int(marquee_offset)
                pr.draw_text(
                    raw_label,
                    draw_x,
                    clip_y + 3,
                    font_size,
                    COLOR_TETO_YELLOW,
                )
                pr.draw_text(
                    raw_label,
                    draw_x + int(loop_w),
                    clip_y + 3,
                    font_size,
                    COLOR_TETO_YELLOW,
                )
                pr.end_scissor_mode()
            else:
                draw_x = panel_x + (panel_w - text_w) // 2
                pr.draw_text(
                    raw_label,
                    draw_x,
                    clip_y + 3,
                    font_size,
                    COLOR_TETO_YELLOW,
                )

            sub = "PRESS SPACE TO PLAY"
            sub_w = pr.measure_text(sub, 20)
            pr.draw_text(
                sub, (GAME_WIDTH - sub_w) // 2, 350, 20, pr.RAYWHITE
            )

            opt = "PRESS O FOR SETTINGS"
            opt_w = pr.measure_text(opt, 14)
            pr.draw_text(
                opt, (GAME_WIDTH - opt_w) // 2, 390, 14, COLOR_TETO_RED
            )

            controls = [
                f"{get_key_name(k_left)} / {get_key_name(k_right)} : Select Track / Move",
                f"{get_key_name(k_rot_l)} / {get_key_name(k_rot_r)} : Rotate Piece",
                f"{get_key_name(k_down)} : Soft Drop",
                f"{get_key_name(k_drop)} : Hard Drop",
                f"{get_key_name(k_pause)} / ESC : Pause Game",
            ]
            for idx, text in enumerate(controls):
                cw = pr.measure_text(text, 15)
                pr.draw_text(
                    text,
                    (GAME_WIDTH - cw) // 2,
                    460 + (idx * 30),
                    15,
                    pr.LIGHTGRAY,
                )

        elif block.game_state == "PAUSED":
            pr.draw_rectangle(
                0, 0, GAME_WIDTH, GAME_HEIGHT, pr.Color(12, 6, 8, 200)
            )
            draw_panel(60, 280, 360, 360, "PAUSED")

            sub = "PRESS SPACE TO RESUME"
            sub_w = pr.measure_text(sub, 18)
            pr.draw_text(
                sub, (GAME_WIDTH - sub_w) // 2, 360, 18, pr.RAYWHITE
            )

            opt = "PRESS O FOR AUDIO SETTINGS"
            opt_w = pr.measure_text(opt, 15)
            pr.draw_text(
                opt, (GAME_WIDTH - opt_w) // 2, 430, 15, COLOR_TETO_RED
            )

            menu_txt = "PRESS M FOR MAIN MENU"
            menu_w = pr.measure_text(menu_txt, 15)
            pr.draw_text(
                menu_txt, (GAME_WIDTH - menu_w) // 2, 480, 15, pr.GRAY
            )

        elif block.game_state == "SETTINGS":
            pr.draw_rectangle(
                0, 0, GAME_WIDTH, GAME_HEIGHT, pr.Color(12, 6, 8, 220)
            )

            if block.in_keybind_menu:
                draw_panel(40, 140, 400, 680, "KEYBINDINGS")

                keys_list = list(block.keybindings.keys())
                for idx, action in enumerate(keys_list):
                    selected = block.keybind_selected == idx
                    c_hdr = COLOR_TETO_YELLOW if selected else pr.LIGHTGRAY
                    y_offset = 200 + (idx * 48)

                    pr.draw_text(action, 80, y_offset, 18, c_hdr)

                    if selected and block.rebinding:
                        val_str = "< PRESS KEY >"
                        val_col = COLOR_TETO_RED
                    else:
                        val_str = f"[ {get_key_name(block.keybindings[action])} ]"
                        val_col = COLOR_TETO_YELLOW if selected else pr.GRAY

                    pr.draw_text(val_str, 290, y_offset, 18, val_col)

                rst_selected = block.keybind_selected == len(keys_list)
                rst_col = COLOR_TETO_RED if rst_selected else pr.LIGHTGRAY
                pr.draw_text(
                    "RESET TO DEFAULTS",
                    (GAME_WIDTH - pr.measure_text("RESET TO DEFAULTS", 18)) // 2,
                    200 + (len(keys_list) * 48) + 15,
                    18,
                    rst_col,
                )

                hint = "SPACE/ENTER: Rebind  |  ESC: Back"
                hint_w = pr.measure_text(hint, 14)
                pr.draw_text(
                    hint, (GAME_WIDTH - hint_w) // 2, 760, 14, pr.RAYWHITE
                )

            else:
                draw_panel(50, 160, 380, 580, "SETTINGS")

                draw_slider(
                    90, 220, 300, "Master Volume", block.vol_master, block.settings_selected == 0
                )
                draw_slider(
                    90, 300, 300, "Music Volume", block.vol_music, block.settings_selected == 1
                )
                draw_slider(
                    90, 380, 300, "SFX Volume", block.vol_sfx, block.settings_selected == 2
                )
                draw_slider(
                    90, 460, 300, "Gameplay Muffle", block.vol_muffle, block.settings_selected == 3
                )

                kb_hdr = (
                    COLOR_TETO_YELLOW
                    if block.settings_selected == 4
                    else pr.LIGHTGRAY
                )
                kb_txt = "CONFIGURE KEYBINDINGS >"
                kb_w = pr.measure_text(kb_txt, 18)
                pr.draw_text(
                    kb_txt, (GAME_WIDTH - kb_w) // 2, 560, 18, kb_hdr
                )

                hint = "W/S: Select  |  A/D: Adjust"
                hint_w = pr.measure_text(hint, 15)
                pr.draw_text(
                    hint, (GAME_WIDTH - hint_w) // 2, 640, 15, pr.RAYWHITE
                )

                back = "PRESS ESC TO RETURN"
                back_w = pr.measure_text(back, 14)
                pr.draw_text(
                    back, (GAME_WIDTH - back_w) // 2, 680, 14, COLOR_TETO_YELLOW
                )

        elif block.game_state == "GAMEOVER":
            pr.draw_rectangle(
                0, 0, GAME_WIDTH, GAME_HEIGHT, pr.Color(12, 6, 8, 220)
            )
            draw_panel(50, 280, 380, 360, "GAME OVER")

            score_txt = f"FINAL SCORE: {block.score}"
            sw = pr.measure_text(score_txt, 22)
            pr.draw_text(
                score_txt, (GAME_WIDTH - sw) // 2, 360, 22, COLOR_TETO_YELLOW
            )

            sub = "PRESS SPACE TO RESTART"
            sub_w = pr.measure_text(sub, 18)
            pr.draw_text(
                sub, (GAME_WIDTH - sub_w) // 2, 450, 18, pr.RAYWHITE
            )

            menu_txt = "PRESS M FOR MAIN MENU"
            menu_w = pr.measure_text(menu_txt, 16)
            pr.draw_text(
                menu_txt, (GAME_WIDTH - menu_w) // 2, 510, 16, pr.GRAY
            )

        else:
            pr.draw_text(f"SCORE: {block.score}", 16, 16, 20, pr.RAYWHITE)
            pr.draw_text("P / ESC: Pause", GAME_WIDTH - 140, 16, 16, pr.GRAY)

        pr.end_texture_mode()

        pr.begin_drawing()
        pr.clear_background(pr.Color(10, 5, 8, 255))

        src_rec = pr.Rectangle(
            0.0, 0.0, grid_target.texture.width, -grid_target.texture.height
        )
        dest_rec = pr.Rectangle(offset_x, offset_y, render_w, render_h)

        pr.begin_shader_mode(shader)
        pr.draw_texture_pro(
            grid_target.texture,
            src_rec,
            dest_rec,
            pr.Vector2(0, 0),
            0.0,
            pr.WHITE,
        )
        pr.end_shader_mode()

        pr.draw_texture_pro(
            ui_target.texture, src_rec, dest_rec, pr.Vector2(0, 0), 0.0, pr.WHITE
        )

        pr.draw_rectangle_lines_ex(
            pr.Rectangle(offset_x, offset_y, render_w, render_h),
            4,
            COLOR_TETO_DARK,
        )

        pr.end_drawing()

    if music:
        pr.detach_audio_stream_processor(
            music.stream, combined_audio_processor
        )
        pr.unload_music_stream(music)

    pr.unload_shader(shader)
    pr.unload_render_texture(grid_target)
    pr.unload_render_texture(ui_target)
    pr.unload_sound(fx_set)
    pr.unload_sound(fx_clear)
    pr.close_audio_device()
    pr.close_window()


if __name__ == "__main__":
    main()
