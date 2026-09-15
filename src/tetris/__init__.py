from __future__ import annotations
import random
import pyray as pr

SCREEN_WIDTH = 450
SCREEN_HEIGHT = 900

GRID_WIDTH = 10
GRID_HEIGHT = 20

KEY_RIGHT = getattr(pr, "KEY_D", 68)
KEY_LEFT = getattr(pr, "KEY_A", 65)
KEY_DOWN = getattr(pr, "KEY_S", 83)
KEY_SPACE = getattr(pr, "KEY_SPACE", 32)
KEY_LEFT_ROTATE = getattr(pr, "KEY_Q", 81)
KEY_RIGHT_ROTATE = getattr(pr, "KEY_E", 69)

unit = SCREEN_HEIGHT // GRID_HEIGHT # 45px

color_arr = [pr.BLACK, pr.RED, pr.MAGENTA, pr.BLUE, pr.GREEN, pr.YELLOW, pr.ORANGE]
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

def rotate(x, y, angle):
    rotation = [(x,y), (-y,x), (-x,-y), (y,-x)]
    return rotation[angle % 4]

class Tetris:
    def __init__(self):
        self.GAME_STATE = True
        self.score = 0
        self.grid_data = [[ 0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.x = 4
        self.y = 1
        self.rotation = 0 # 0, 1, 2, 3
        self.color = color_arr[random.randint(1, 6)]
        self.type = type_arr[random.randint(0, 6)]

    def freeze(self):
        for (dx, dy) in self.get_shape():
            self.grid_data[self.y+dy][self.x+dx] = self.color
        for i in range(GRID_HEIGHT):
            if 0 not in self.grid_data[i]:
                del self.grid_data[i]
                self.grid_data.insert(0, [0 for _ in range(GRID_WIDTH)])
                self.score += 10

        # update new peices
        self.x = 4
        self.y = 1
        self.rotation = 0
        self.color = color_arr[random.randint(1, 6)]
        self.type = type_arr[random.randint(0, 6)]

        self.score += 4

        if self.collision_check_rotate()["neural"]:
            print("GAME OVER")
            self.GAME_STATE = False

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
        if color == 0: color = self.color
        cell = pr.Rectangle(x * unit, y * unit, unit, unit)
        pr.draw_rectangle_gradient_ex(cell, color, color, pr.DARKGRAY, color)
        self.draw_cell_boxed(x, y, pr.RAYWHITE)

    def draw_cell_boxed(self, x, y, color=0):
        if color == 0: color = self.color
        cell = pr.Rectangle(x * unit, y * unit, unit, unit)
        pr.draw_rectangle_lines_ex(cell, 1, color)


def main() -> None:
    pr.init_window(SCREEN_WIDTH, SCREEN_HEIGHT, "Tetris")
    pr.set_target_fps(60)

    block = Tetris()
    count = 0

    while not pr.window_should_close():
        if block.GAME_STATE:
            count += 1
            # drop rate 0.5s
            if count % 30 == 0 or pr.is_key_pressed(KEY_DOWN):
                if not block.collision_check()["down"]:
                    block.y += 1
                else:
                    block.freeze()

            if pr.is_key_pressed(KEY_SPACE):
                block.y = block.fall_pos()
                block.freeze()

            if pr.is_key_pressed(KEY_RIGHT) and not block.collision_check()["right"]:
                block.x += 1
            elif pr.is_key_pressed(KEY_LEFT) and not block.collision_check()["left"]:
                block.x -= 1

            if pr.is_key_pressed(KEY_RIGHT_ROTATE) and not block.collision_check_rotate()["right"]:
                block.rotation = (block.rotation + 1) % 4
            elif pr.is_key_pressed(KEY_LEFT_ROTATE) and not block.collision_check_rotate()["left"]:
                block.rotation = (block.rotation - 1) % 4
        else:
            if pr.is_key_pressed(KEY_SPACE): # restart
                block.__init__()


        pr.begin_drawing()
        pr.clear_background(pr.BLACK)

        # draw movable tetris peice
        for (dx, dy) in block.get_shape():
            block.draw_cell(block.x+dx, block.y+dy)

        # draw shadow tetris peice
        for (dx, dy) in block.get_shape():
            block.draw_cell_boxed(block.x+dx, block.fall_pos()+dy)

        # draw frozen pecies
        for i in range(GRID_HEIGHT):
            for j in range(GRID_WIDTH):
                if block.grid_data[i][j] != 0:
                    block.draw_cell(j, i, block.grid_data[i][j])

        # game over overlay
        if not block.GAME_STATE:
            pr.draw_text("GAME OVER", 10, 10, 20, pr.RAYWHITE)
            pr.draw_text(f"SCORE: {block.score}", 10, 30, 20, pr.RAYWHITE)
        else:
            pr.draw_text(f"SCORE: {block.score}", 10, 10, 20, pr.RAYWHITE)


        pr.end_drawing()

    pr.close_window()


if __name__ == "__main__":
    main()
