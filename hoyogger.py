# -*- coding: utf-8 -*-
import sys
import pygame
import math


# 円と円のあたり判定
def circle_hit_circle(x0, y0, r0, x1, y1, r1):
    dx = x0 - x1
    dy = y0 - y1
    r = r0 + r1
    return (dx * dx + dy * dy) <= (r * r)


# ステートマシン
class StateMachine:
    def __init__(self, functions, initial_state):
        self._current_state = ''
        self._next_state = initial_state
        self._state_frame_count = 0
        self._state_func_table = functions

    def update(self):
        if self._next_state:
            self._call_state_func('on_exit')
            self._current_state = self._next_state
            self._next_state = ''
            self._state_frame_count = 0
            self._call_state_func('on_enter')
        self._call_state_func('on_update')
        self._state_frame_count += 1

    def draw(self):
        self._call_state_func('on_draw')

    def _call_state_func(self, name):
        if self._current_state not in self._state_func_table:
            return
        functions = self._state_func_table[self._current_state]
        if name not in functions:
            return
        functions[name](self)

    def change_state(self, next_state):
        self._next_state = next_state

    def get_state(self):
        return self._current_state

    def get_frame_count(self):
        return self._state_frame_count


# キー入力
class KeyState:
    def __init__(self):
        self.key_new = pygame.key.get_pressed()
        self.key_old = self.key_new

    def update(self):
        self.key_old = self.key_new
        self.key_new = pygame.key.get_pressed()

    def get_key(self, name):
        return self.key_new[name]

    def get_key_down(self, name):
        return self.key_new[name] and not self.key_old[name]


# 定数
SCREEN_WIDTH = 240
SCREEN_HEIGHT = 320
WINDOW_WIDTH = SCREEN_WIDTH * 2
WINDOW_HEIGHT = SCREEN_HEIGHT * 2
OBJ_SIZE = 24
MAP_NUM_X = 9
MAP_NUM_Y = 13
MAP_LEFT = 12
MAP_TOP = 4
MAP_RIGHT = MAP_LEFT + OBJ_SIZE * MAP_NUM_X
MAP_BOTTOM = MAP_TOP + OBJ_SIZE * MAP_NUM_Y

# 初期化
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
render_buffer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()
img_title = pygame.image.load('title.png')
img_press_key = pygame.image.load('presskey.png')
img_game_over = pygame.image.load('gameover.png')
img_stage_clear = pygame.image.load('stageclear.png')
img_goal = pygame.image.load('goal.png')
img_ready = pygame.image.load('ready.png')
img_char = pygame.image.load('char.png')
img_char_flipped = pygame.transform.flip(img_char, True, False)
img_bg = pygame.image.load('bg.png')
img_frame = pygame.image.load('frame.png')
snd_walk = pygame.mixer.Sound('walk.wav')
snd_button = pygame.mixer.Sound('button.wav')
snd_dead = pygame.mixer.Sound('dead.wav')
snd_goal = pygame.mixer.Sound('goal.wav')
key_state = KeyState()


# プレイヤーキャラクター
class Player(StateMachine):
    def __init__(self, x, y):
        super().__init__(
            {
                'walk': {
                    'on_update': Player._walk_update,
                    'on_draw': Player._walk_draw,
                },
                'dead': {
                    'on_enter': Player._dead_enter,
                    'on_draw': Player._dead_draw,
                },
                'goal': {
                    'on_enter': Player._goal_enter,
                    'on_draw': Player._goal_draw,
                },
            },
            'walk'
        )
        self.x = MAP_LEFT + OBJ_SIZE * x
        self.y = MAP_TOP + OBJ_SIZE * y
        self.vel_x = 0
        self.vel_y = 0

    def _walk_update(self):
        # 減速
        self.vel_x *= 0.98
        self.vel_y *= 0.98

        # 矢印キーで加速
        moved = False
        if key_state.get_key_down(pygame.K_LEFT):
            self.vel_x -= 0.25
            moved = True
        elif key_state.get_key_down(pygame.K_RIGHT):
            self.vel_x += 0.25
            moved = True
        if key_state.get_key_down(pygame.K_UP):
            self.vel_y -= 0.25
            moved = True
        elif key_state.get_key_down(pygame.K_DOWN):
            self.vel_y += 0.25
            moved = True
        if moved:
            snd_walk.play()
            self.change_state('walk')

        # 最大速度を制限
        max_speed = 4.0
        magnitude_square = self.vel_x * self.vel_x + self.vel_y * self.vel_y
        if magnitude_square > max_speed * max_speed:
            magnitude = math.sqrt(magnitude_square)
            self.vel_x = self.vel_x / magnitude * max_speed
            self.vel_y = self.vel_y / magnitude * max_speed

        # 移動
        self.x += self.vel_x
        self.y += self.vel_y

        # ステージの外に出ないようにする
        self.x = min(max(self.x, MAP_LEFT), MAP_RIGHT - OBJ_SIZE)
        self.y = min(max(self.y, MAP_TOP), MAP_BOTTOM - OBJ_SIZE)

        # ゴール判定
        if self.y <= MAP_TOP:
            self.change_state('goal')

    def _walk_draw(self):
        j = [0, 1, 2, 1]
        i = j[min(int(self.get_frame_count() / 3), len(j)-1)]
        render_buffer.blit(img_char, (self.x, self.y), (i * 24, 0, 24, 24))

    def _dead_enter(self):
        snd_dead.play()

    def _dead_draw(self):
        i = int(self.get_frame_count() / 2)
        if i < 6:
            render_buffer.blit(img_char, (self.x, self.y), (i * 24, 72, 24, 24))

    def _goal_enter(self):
        snd_goal.play()

    def _goal_draw(self):
        j = [0, 1, 2, 1]
        i = j[int(self.get_frame_count() / 2) % len(j)]
        render_buffer.blit(img_char, (self.x, self.y), (i * 24, 0, 24, 24))


# 敵キャラクター（雲丹）
class EnemyUni:
    def __init__(self, x, y):
        self.x = MAP_LEFT + OBJ_SIZE * x
        self.y = MAP_TOP + OBJ_SIZE * y
        self._frame_count = 0

    def update(self):
        self._frame_count += 1

    def draw(self):
        i = int(self._frame_count / 30) % 3
        render_buffer.blit(img_char, (self.x, self.y), (72 + i * 24, 0, 24, 24))


# 敵キャラクター（翻車魚）
class EnemyManbou:
    def __init__(self, x, y, velocity):
        self.x = MAP_LEFT + OBJ_SIZE * x
        self.y = MAP_TOP + OBJ_SIZE * y
        self._velocity = velocity
        self._frame_count = 0

    def update(self):
        self._frame_count += 1
        self.x += self._velocity

        if self.x >= SCREEN_WIDTH:
            self.x = -OBJ_SIZE
        if self.x < -OBJ_SIZE:
            self.x = SCREEN_WIDTH - 1

    def draw(self):
        j = [0, 1, 2, 1]
        i = j[int(self._frame_count / 4) % len(j)]
        if self._velocity < 0:
            render_buffer.blit(img_char, (self.x, self.y), (72 + i * 24, 24, 24, 24))
        else:
            render_buffer.blit(img_char_flipped, (self.x, self.y), (i * 24, 24, 24, 24))


# 敵キャラクター（魚）
class EnemySakana:
    def __init__(self, x, y, velocity):
        self.x = MAP_LEFT + OBJ_SIZE * x
        self.y = MAP_TOP + OBJ_SIZE * y
        self._velocity = velocity
        self._frame_count = 0

    def update(self):
        self._frame_count += 1
        self.y += self._velocity

        if self.y >= SCREEN_HEIGHT:
            self.y = -OBJ_SIZE
        if self.y < -OBJ_SIZE:
            self.y = SCREEN_HEIGHT - 1

    def draw(self):
        j = [0, 1, 2, 1]
        i = j[int(self._frame_count / 2) % len(j)]
        render_buffer.blit(img_char, (self.x, self.y), (72 + i * 24, 48, 24, 24))


# 敵キャラクター（蟹）
class EnemyKani:
    def __init__(self, x, y, offset):
        self.initial_x = MAP_LEFT + OBJ_SIZE * x
        self.x = self.initial_x
        self.y = MAP_TOP + OBJ_SIZE * y
        self._frame_count = 0
        self._offset = offset

    def update(self):
        self._frame_count += 1
        frequency = self._frame_count / (8 * math.pi)
        self.x = self.initial_x + math.sin(frequency + self._offset) * OBJ_SIZE

    def draw(self):
        j = [0, 1, 2, 1]
        i = j[int(self._frame_count / 4) % len(j)]
        render_buffer.blit(img_char, (self.x, self.y), (i * 24, 24, 24, 24))


# 敵キャラクター（磯巾着）
class EnemyIsogin:
    def __init__(self, x, y, offset):
        self.initial_y = MAP_TOP + OBJ_SIZE * y
        self.x = MAP_LEFT + OBJ_SIZE * x
        self.y = self.initial_y
        self._frame_count = 0
        self._offset = offset

    def update(self):
        self._frame_count += 1
        frequency = self._frame_count / (8 * math.pi)
        self.y = self.initial_y + math.sin(frequency + self._offset) * OBJ_SIZE

    def draw(self):
        j = [0, 1, 2, 1]
        i = j[int(self._frame_count / 4) % len(j)]
        render_buffer.blit(img_char, (self.x, self.y), (i * 24, 48, 24, 24))


# ゲーム
class Game(StateMachine):
    ENEMY_DATA = [
        (None, None),
        (EnemyUni, None),
        (EnemyManbou, [1]),
        (EnemyManbou, [-1]),
        (EnemySakana, [1]),
        (EnemySakana, [-1]),
        (EnemyKani, [0]),
        (EnemyKani, [math.pi]),
        (EnemyIsogin, [0]),
        (EnemyIsogin, [math.pi]),
    ]
    STAGE_DATA = [
        # STAGE 1
        [
            0, 0, 0, 0, 0, 0, 0, 0, 0,
            1, 1, 1, 0, 0, 0, 1, 1, 1,
            2, 0, 0, 0, 0, 2, 0, 0, 0,
            2, 0, 0, 0, 0, 2, 0, 0, 0,
            0, 0, 1, 1, 1, 1, 1, 0, 0,
            0, 0, 3, 0, 0, 0, 0, 3, 0,
            0, 0, 3, 0, 0, 0, 0, 3, 0,
            1, 1, 1, 0, 0, 0, 1, 1, 1,
            2, 0, 0, 0, 0, 2, 0, 0, 0,
            2, 0, 0, 0, 0, 2, 0, 0, 0,
            0, 0, 1, 1, 1, 1, 1, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0,
        ],
        # STAGE 2
        [
            0, 0, 0, 0, 0, 0, 0, 0, 0,
            1, 1, 8, 0, 7, 0, 8, 1, 1,
            5, 2, 0, 0, 0, 2, 0, 0, 5,
            5, 0, 0, 3, 0, 0, 0, 3, 5,
            5, 1, 1, 1, 1, 1, 1, 1, 5,
            0, 2, 0, 0, 0, 2, 0, 0, 0,
            0, 0, 0, 3, 0, 0, 0, 3, 0,
            1, 1, 1, 0, 0, 0, 1, 1, 1,
            5, 2, 0, 0, 0, 2, 0, 0, 5,
            5, 0, 0, 3, 0, 0, 0, 3, 5,
            5, 1, 1, 1, 1, 1, 1, 1, 5,
            0, 1, 0, 0, 6, 0, 0, 1, 0,
            0, 0, 0, 1, 0, 1, 0, 0, 0,
        ],
    ]

    def __init__(self):
        super().__init__(
            {
                'title': {
                    'on_update': Game._title_update,
                    'on_draw': Game._title_draw
                },
                'ready': {
                    'on_enter': Game._ready_enter,
                    'on_update': Game._ready_update,
                    'on_draw': Game._ready_draw
                },
                'game': {
                    'on_enter': Game._game_enter,
                    'on_update': Game._game_update,
                    'on_draw': Game._game_draw
                },
            },
            'title'
        )
        self._stage = 0

    def _title_update(self):
        if key_state.get_key_down(pygame.K_SPACE):
            snd_button.play()
            self.change_state('ready')
            self._stage = 0

    def _title_draw(self):
        render_buffer.blit(img_bg, (0, 0))
        i = int(self.get_frame_count() / 4) % 3
        render_buffer.blit(img_char, (SCREEN_WIDTH / 2 - OBJ_SIZE / 2, SCREEN_HEIGHT / 2 - OBJ_SIZE / 2 + 8), (24 * i, 0, 24, 24))
        render_buffer.blit(img_frame, (0, 0))
        render_buffer.blit(img_title, (SCREEN_WIDTH / 2 - img_title.get_width() / 2, SCREEN_HEIGHT / 2 - img_title.get_height() / 2 - 80))
        render_buffer.blit(img_press_key, (SCREEN_WIDTH / 2 - img_press_key.get_width() / 2, SCREEN_HEIGHT / 2 - img_press_key.get_height() / 2 + 80))

    def _draw_game_objects(self):
        render_buffer.blit(img_bg, (0, 0))
        for e in self._enemies:
            e.draw()
        self._player.draw()
        render_buffer.blit(img_frame, (0, 0))

    def _ready_enter(self):
        # ゲームの準備
        self._player = Player(4, 12)
        self._enemies = []
        for y in range(0, MAP_NUM_Y):
            for x in range(0, MAP_NUM_X):
                i = Game.STAGE_DATA[self._stage][y * MAP_NUM_X + x]
                enemy_class, init_arguments = Game.ENEMY_DATA[i]
                if enemy_class:
                    if init_arguments:
                        self._enemies.append(enemy_class(x, y, *init_arguments))
                    else:
                        self._enemies.append(enemy_class(x, y))

    def _ready_update(self):
        if self.get_frame_count() >= 60:
            self.change_state('game')

    def _ready_draw(self):
        self._draw_game_objects()

        # READY表示
        x = SCREEN_WIDTH / 2 - img_ready.get_width() / 2
        y = SCREEN_HEIGHT / 2 - img_ready.get_height() / 2
        render_buffer.blit(img_ready, (x, y))

    def _game_enter(self):
        #pygame.mixer.music.load('bgmGame.wav')
        #pygame.mixer.music.set_volume(0.25)
        #pygame.mixer.music.play(-1)
        pass

    def _game_update(self):
        # 衝突判定
        if self._player.get_state() == 'walk':
            for e in self._enemies:
                if circle_hit_circle(self._player.x, self._player.y, OBJ_SIZE / 2 - 4, e.x, e.y, OBJ_SIZE / 2 - 4):
                    self._player.change_state('dead')

        self._player.update()
        for e in self._enemies:
            e.update()

        # プレイヤー死亡後180フレームでタイトル画面に
        if self._player.get_state() == 'dead' and self._player.get_frame_count() > 180:
            self.change_state('title')

        # プレイヤーゴール後180フレームで次のステージに
        if self._player.get_state() == 'goal' and self._player.get_frame_count() > 180:
            self._stage = (self._stage + 1) % len(Game.STAGE_DATA)
            self.change_state('ready')

        if self._player.get_state() != 'walk':
            pygame.mixer.music.stop()

    def _game_draw(self):
        self._draw_game_objects()
        pygame.draw.line(render_buffer, (255, 0, 0), (MAP_LEFT, MAP_TOP + OBJ_SIZE), (MAP_RIGHT-1, MAP_TOP + OBJ_SIZE))

        # ゴール表示
        if self._player.get_state() == 'walk' and self.get_frame_count() % 60 >= 30 and self._player.y > MAP_TOP + OBJ_SIZE * 2:
            x = SCREEN_WIDTH / 2 - img_goal.get_width() / 2
            y = MAP_TOP + OBJ_SIZE - img_goal.get_height() - 4
            render_buffer.blit(img_goal, (x, y))

        # ゲーム―バー表示
        if self._player.get_state() == 'dead':
            x = SCREEN_WIDTH / 2 - img_game_over.get_width() / 2
            y = SCREEN_HEIGHT / 2 - img_game_over.get_height() / 2
            render_buffer.blit(img_game_over, (x, y))

        # ステージクリア表示
        if self._player.get_state() == 'goal':
            x = SCREEN_WIDTH / 2 - img_stage_clear.get_width() / 2
            y = SCREEN_HEIGHT / 2 - img_stage_clear.get_height() / 2
            render_buffer.blit(img_stage_clear, (x, y))


# メインループ
game = Game()
quit_game = False
while not quit_game:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            quit_game = True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            quit_game = True

    # 更新
    key_state.update()
    game.update()

    # 描画
    render_buffer.fill((0, 0, 0))  # 画面クリア
    game.draw()
    screen.blit(pygame.transform.scale(render_buffer, (WINDOW_WIDTH, WINDOW_HEIGHT)), (0, 0))  # 拡大コピー

    pygame.display.flip()   # バッファフリップ
    clock.tick(60)          # フレームレートを60fpsに保つ

# 終了
pygame.quit()
sys.exit(0)
