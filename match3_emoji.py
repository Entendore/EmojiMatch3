#!/usr/bin/env python3
"""
Match-3 Emoji Puzzle Game  —  Enhanced Edition
================================================
Features:
  - 6 emoji categories (Fruits, Animals, Food, Nature, Space, Sports)
  - Level system with score targets & star ratings
  - Special pieces: Striped (4-match) and Bomb (5-match)
  - Hint system (H key) highlights a valid move
  - Auto-shuffle when no moves remain
  - Smooth bounce/wobble animations
  - Combo cascade counter & score multipliers
  - Category selection screen

Controls:
  Click to select → click adjacent to swap
  H: Hint  |  R: Restart  |  ESC: Quit

Requires: pygame, NotoColorEmoji font
"""

import os
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import sys
import random
import math
import time
import copy

# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════
WINDOW_WIDTH  = 700
WINDOW_HEIGHT = 850
GRID_COLS     = 8
GRID_ROWS     = 8
CELL_SIZE     = 64
GRID_OFFSET_X = (WINDOW_WIDTH - GRID_COLS * CELL_SIZE) // 2
GRID_OFFSET_Y = 155
FPS           = 60
ANIM_SPEED    = 10

# ═══════════════════════════════════════════════════════════════════════════════
# Emoji Categories
# ═══════════════════════════════════════════════════════════════════════════════
CATEGORIES = {
    # ── Page 1 ─────────────────────────────────────────────────────────
    "Fruits": {
        "icon": "🍎",
        "emojis": ["🍎", "🍊", "🍋", "🍇", "🫐", "🥝", "🍓", "🍑", "🍒", "🥭", "🍈", "🍌", "🥑", "🍐", "🍅"],
        "color": (255, 107, 107),
        "desc": "Classic fruit match!",
    },
    "Animals": {
        "icon": "🐱",
        "emojis": ["🐶", "🐱", "🐼", "🐰", "🦊", "🐸", "🐧", "🐨", "🦁", "🐯", "🐴", "🐵", "🐮", "🐷", "🐑"],
        "color": (255, 183, 77),
        "desc": "Cute animal friends!",
    },
    "Food": {
        "icon": "🍕",
        "emojis": ["🍕", "🍔", "🌮", "🍩", "🧁", "🍪", "🧀", "🥐", "🧇", "🍿", "🥨", "🍗", "🥗", "🍣", "🥟"],
        "color": (255, 213, 79),
        "desc": "Delicious treats!",
    },
    "Nature": {
        "icon": "🌸",
        "emojis": ["🌸", "🌺", "🌻", "🌈", "⭐", "🌙", "🍂", "🍁", "🌿", "🌱", "🌾", "🌷", "🌴", "🌵", "🎋"],
        "color": (129, 199, 132),
        "desc": "Beautiful nature!",
    },
    "Space": {
        "icon": "🚀",
        "emojis": ["🚀", "🛸", "🌍", "🌙", "💫", "🪐", "☄️", "🛰️", "🌠", "🌌", "🔭", "🌑", "🌕", "🌗", "🌖"],
        "color": (149, 117, 205),
        "desc": "Explore the cosmos!",
    },
    "Sports": {
        "icon": "⚽",
        "emojis": ["⚽", "🏀", "🎾", "🏐", "🎯", "🎳", "🏓", "🏉", "🎱", "🥊", "🥅", "🎽", "🎿", "🏊", "🏋️"],
        "color": (79, 195, 247),
        "desc": "Sporty challenge!",
    },
    "Ocean": {
        "icon": "🐠",
        "emojis": ["🐠", "🐟", "🦈", "🐙", "🦑", "🦀", "🐚", "🐳", "🦭", "🐡", "🪸", "🦞", "🐢", "🐊", "🐬"],
        "color": (38, 198, 218),
        "desc": "Deep sea adventure!",
    },
    "Music": {
        "icon": "🎵",
        "emojis": ["🎵", "🎶", "🎸", "🎹", "🥁", "🎺", "🎻", "🪘", "🎷", "🪗", "🎤", "🎧", "🪕", "🪈", "🍖"],
        "color": (186, 104, 200),
        "desc": "Musical vibes!",
    },
    "Travel": {
        "icon": "✈️",
        "emojis": ["✈️", "🚗", "🚂", "🚢", "🏠", "🏯", "🗽", "🏕️", "🗺️", "⛰️", "🏖️", "🗼", "🕌", "🏝️", "🌉"],
        "color": (255, 167, 38),
        "desc": "World explorer!",
    },
    "Halloween": {
        "icon": "🎃",
        "emojis": ["🎃", "👻", "🦇", "🕷️", "💀", "👁️", "🧛", "🧟", "🕸️", "🪦", "🧪", "🧹", "🦴", "🩸", "⚰️"],
        "color": (240, 98, 146),
        "desc": "Spooky fun!",
    },
    "Hearts": {
        "icon": "❤️",
        "emojis": ["❤️", "🧡", "💛", "💚", "💙", "💜", "🤎", "🖤", "🤍", "💖", "💘", "💝", "💞", "💓", "💗"],
        "color": (236, 64, 122),
        "desc": "Spread the love!",
    },
    "Weather": {
        "icon": "☀️",
        "emojis": ["☀️", "🌤️", "⛅", "🌥️", "☁️", "🌧️", "⛈️", "❄️", "🌪️", "🌈", "🌬️", "🌊", "☔", "🌨️", "🌡️"],
        "color": (100, 181, 246),
        "desc": "Whatever the weather!",
    },
    # ── Page 2 ─────────────────────────────────────────────────────────
    "Dinosaurs": {
        "icon": "🦕",
        "emojis": ["🦕", "🦖", "🦴", "🪨", "🌋", "🌿", "🥚", "🌵", "🦣", "🦎", "🐢", "🐊", "🐲", "🐉", "🥓"],
        "color": (141, 110, 99),
        "desc": "Prehistoric puzzle!",
    },
    "Smileys": {
        "icon": "😀",
        "emojis": ["😀", "😂", "🥹", "😎", "🤩", "😜", "🤪", "😇", "🥳", "🤗", "😏", "🫠", "😴", "🤔", "🫡"],
        "color": (255, 238, 88),
        "desc": "Express yourself!",
    },
    "Gems": {
        "icon": "💎",
        "emojis": ["💎", "🔺", "🔷", "🟣", "🟡", "🟢", "🔴", "⚪", "🟠", "🟤", "💠", "🔮", "🔻", "⬛", "⬜"],
        "color": (126, 87, 194),
        "desc": "Shiny treasures!",
    },
    "Vehicles": {
        "icon": "🚗",
        "emojis": ["🚗", "🚕", "🚌", "🚎", "🏎️", "🚓", "🚑", "🚒", "🚐", "🛻", "🚜", "🛵", "🚲", "🛴", "🛺"],
        "color": (66, 165, 245),
        "desc": "Vroom vroom!",
    },
    "Garden": {
        "icon": "🌹",
        "emojis": ["🌹", "🌷", "💐", "🌻", "🌼", "🪻", "🌱", "🪴", "🌳", "🍀", "🐿️", "🦋", "🐞", "🐝", "🧆"],
        "color": (102, 187, 106),
        "desc": "Garden paradise!",
    },
    "Christmas": {
        "icon": "🎄",
        "emojis": ["🎄", "🎅", "🤶", "🎁", "🔔", "🕯️", "⭐", "❄️", "⛄", "🦌", "🧣", "🧤", "🧦", "🥮", "🍡"],
        "color": (76, 175, 80),
        "desc": "Holiday cheer!",
    },
    "Fantasy": {
        "icon": "🧙",
        "emojis": ["🧙", "🧝", "🧚", "🦄", "🐉", "👑", "⚔️", "🛡️", "🪄", "🔮", "🏰", "🗝️", "🎭", "🍵", "🫖"],
        "color": (121, 85, 72),
        "desc": "Enchanted realm!",
    },
    "Hands": {
        "icon": "👋",
        "emojis": ["👋", "🤚", "🖐️", "✋", "🖖", "👌", "🤌", "🤏", "✌️", "🤞", "🤟", "🤘", "👍", "👎", "👏"],
        "color": (255, 204, 128),
        "desc": "Hand gestures!",
    },
    "Birds": {
        "icon": "🦅",
        "emojis": ["🦅", "🦉", "🦜", "🦚", "🐤", "🐣", "🐧", "🦢", "🦩", "🕊️", "🦆", "🦃", "🐔", "🦤", "🪶"],
        "color": (255, 138, 101),
        "desc": "Fly high!",
    },
    "Insects": {
        "icon": "🐝",
        "emojis": ["🐝", "🪱", "🐛", "🦋", "🐌", "🐞", "🐜", "🪰", "🪲", "🦗", "🕷️", "🦂", "🦟", "🪳", "🦠"],
        "color": (174, 213, 129),
        "desc": "Bug world!",
    },
    "Asian": {
        "icon": "🏮",
        "emojis": ["🏮", "🧧", "🐉", "🧨", "🎋", "🎎", "🎑", "🥟", "🍜", "🍱", "🍶", "🥢", "🍻", "🥂", "🧊"],
        "color": (229, 57, 53),
        "desc": "Eastern vibes!",
    },
    "Retro": {
        "icon": "👾",
        "emojis": ["👾", "🕹️", "🃏", "🎲", "🎰", "🧸", "🎀", "🪅", "🪩", "🎯", "🏆", "🎪", "🎭", "💦", "🫧"],
        "color": (255, 112, 67),
        "desc": "Old school fun!",
    },
    # ── Page 3 ─────────────────────────────────────────────────────────
    "Science": {
        "icon": "🔬",
        "emojis": ["🔬", "🧪", "⚗️", "🧬", "🔭", "🧫", "💊", "🩺", "🧠", "🫀", "🦷", "🌡️", "🧲", "💧", "👁️"],
        "color": (0, 188, 212),
        "desc": "Lab time!",
    },
    "Tools": {
        "icon": "🔨",
        "emojis": ["🔨", "🪚", "⛏️", "🔧", "🔩", "🪛", "📐", "📏", "🧰", "👃", "👄", "👂", "📦", "📬", "📮"],
        "color": (141, 110, 99),
        "desc": "Build it!",
    },
    "Camping": {
        "icon": "⛺",
        "emojis": ["⛺", "🏕️", "🔥", "🪵", "🧭", "🎒", "🔦", "🔪", "🌲", "⛰️", "🏷️", "🧮", "📌", "📎", "🔗"],
        "color": (121, 85, 72),
        "desc": "Outdoor adventure!",
    },
    "Party": {
        "icon": "🎉",
        "emojis": ["🎉", "🎊", "🎈", "🎀", "🎁", "🎂", "🍰", "🥂", "🍾", "🪅", "🪩", "🔑", "🔒", "🔓", "🏪"],
        "color": (233, 30, 99),
        "desc": "Party time!",
    },
    "Egypt": {
        "icon": "🏛️",
        "emojis": ["🏛️", "🗿", "🐪", "🏜️", "🌙", "⭐", "🏺", "🏗️", "👣", "👆", "📰", "🏦", "🏫", "🏥", "🏨"],
        "color": (255, 193, 7),
        "desc": "Ancient wonders!",
    },
    "Office": {
        "icon": "📎",
        "emojis": ["📎", "📋", "📁", "📂", "📄", "🗂", "📃", "📨", "📧", "📩", "📥", "📦", "📍", "📌", "📝"],
        "color": (0, 150, 136),
        "desc": "Work life!",
    },
}

PER_PAGE = 12  # categories per menu page

# Special piece types
SPECIAL_NONE    = "none"
SPECIAL_STRIPED = "striped"   # clears entire row or column
SPECIAL_BOMB    = "bomb"      # clears all of one emoji type

# Colors (Catppuccin Mocha palette)
BG_COLOR         = (24, 24, 37)
GRID_BG_COLOR    = (36, 36, 54)
CELL_BG          = (49, 50, 68)
CELL_HOVER       = (69, 71, 90)
SELECTED_BORDER  = (249, 226, 175)
TEXT_COLOR        = (205, 214, 244)
SUBTEXT_COLOR     = (147, 153, 178)
SCORE_COLOR      = (166, 227, 161)
COMBO_COLOR      = (249, 226, 175)
MATCH_FLASH      = (255, 255, 255)
STAR_FILLED      = (249, 226, 175)
STAR_EMPTY       = (69, 71, 90)
HINT_COLOR       = (137, 180, 250)
PROGRESS_BG      = (49, 50, 68)
PROGRESS_FG      = (166, 227, 161)
PANEL_COLOR      = (30, 30, 46)
PANEL_BORDER     = (88, 91, 112)
BUTTON_COLOR     = (69, 71, 90)
BUTTON_HOVER     = (88, 91, 112)
BUTTON_BORDER    = (137, 180, 250)

# Level config
LEVEL_TARGETS = [300, 600, 1000, 1500, 2200, 3000]
STAR_THRESHOLDS = [0.4, 0.7, 1.0]  # fraction of target for 1/2/3 stars


# ═══════════════════════════════════════════════════════════════════════════════
# Emoji Renderer
# ═══════════════════════════════════════════════════════════════════════════════
class EmojiRenderer:
    """Renders emojis to pygame surfaces with caching."""

    def __init__(self, size: int):
        self.size = size
        self.cache: dict[str, pygame.Surface] = {}
        font_paths = [
            "/usr/share/fonts/truetype/emoji/NotoColorEmoji.ttf",
            "/usr/share/fonts/noto-color-emoji/NotoColorEmoji.ttf",
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        ]
        self.font = None
        for path in font_paths:
            if os.path.exists(path):
                try:
                    self.font = pygame.font.Font(path, int(size * 0.8))
                    break
                except Exception:
                    continue
        if self.font is None:
            self.font = pygame.font.SysFont("noto color emoji", int(size * 0.8))
            if self.font is None:
                self.font = pygame.font.SysFont(None, int(size * 0.8))

    def get(self, emoji: str) -> pygame.Surface:
        if emoji not in self.cache:
            surf = self.font.render(emoji, True, (0, 0, 0))
            target = int(self.size * 0.75)
            surf = pygame.transform.smoothscale(surf, (target, target))
            self.cache[emoji] = surf
        return self.cache[emoji]


# ═══════════════════════════════════════════════════════════════════════════════
# Piece
# ═══════════════════════════════════════════════════════════════════════════════
class Piece:
    """A single grid piece with animation and special type."""

    def __init__(self, emoji: str, row: int, col: int, special: str = SPECIAL_NONE):
        self.emoji = emoji
        self.row = row
        self.col = col
        self.special = special
        self.x = float(GRID_OFFSET_X + col * CELL_SIZE)
        self.y = float(GRID_OFFSET_Y + row * CELL_SIZE)
        self.target_x = self.x
        self.target_y = self.y
        self.matched = False
        self.scale = 1.0
        self.wobble = 0.0      # wobble angle for hint animation
        self.bounce = 0.0       # bounce offset for landing

    @property
    def is_animating(self) -> bool:
        return abs(self.x - self.target_x) > 0.5 or abs(self.y - self.target_y) > 0.5

    def snap_to_target(self):
        self.x, self.y = self.target_x, self.target_y

    def update_target(self):
        self.target_x = float(GRID_OFFSET_X + self.col * CELL_SIZE)
        self.target_y = float(GRID_OFFSET_Y + self.row * CELL_SIZE)

    def animate(self, speed: float = ANIM_SPEED):
        for attr, target in [("x", "target_x"), ("y", "target_y")]:
            val = getattr(self, attr)
            tgt = getattr(self, target)
            if abs(val - tgt) > 0.5:
                setattr(self, attr, val + math.copysign(speed, tgt - val))
            else:
                setattr(self, attr, tgt)

        # Bounce decay
        if abs(self.bounce) > 0.3:
            self.bounce *= -0.55
        else:
            self.bounce = 0.0

        # Wobble decay
        if abs(self.wobble) > 0.01:
            self.wobble *= 0.92
        else:
            self.wobble = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Button helper
# ═══════════════════════════════════════════════════════════════════════════════
class Button:
    def __init__(self, x, y, w, h, text, font, color=BUTTON_COLOR,
                 hover_color=BUTTON_HOVER, border=BUTTON_BORDER, text_color=TEXT_COLOR):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.border = border
        self.text_color = text_color
        self.hovered = False

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surface):
        c = self.hover_color if self.hovered else self.color
        pygame.draw.rect(surface, c, self.rect, border_radius=10)
        pygame.draw.rect(surface, self.border, self.rect, 2, border_radius=10)
        ts = self.font.render(self.text, True, self.text_color)
        surface.blit(ts, (self.rect.centerx - ts.get_width() // 2,
                          self.rect.centery - ts.get_height() // 2))

    def clicked(self, pos) -> bool:
        return self.rect.collidepoint(pos)


# ═══════════════════════════════════════════════════════════════════════════════
# Main Game
# ═══════════════════════════════════════════════════════════════════════════════
class Match3Game:
    # States
    MENU      = "menu"
    IDLE      = "idle"
    SELECTED  = "selected"
    SWAPPING  = "swapping"
    REMOVING  = "removing"
    FALLING   = "falling"
    GAME_OVER = "game_over"
    LEVEL_WIN = "level_win"
    SHUFFLING = "shuffling"

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Match-3 Emoji Puzzle — Enhanced Edition")
        self.clock = pygame.time.Clock()

        # Fonts
        self.title_font  = pygame.font.SysFont("dejavu sans", 38, bold=True)
        self.big_font    = pygame.font.SysFont("dejavu sans", 32, bold=True)
        self.score_font  = pygame.font.SysFont("dejavu sans", 26, bold=True)
        self.info_font   = pygame.font.SysFont("dejavu sans", 18)
        self.small_font  = pygame.font.SysFont("dejavu sans", 14)
        self.tiny_font   = pygame.font.SysFont("dejavu sans", 12)

        self.emoji_renderer = EmojiRenderer(CELL_SIZE)
        self.emoji_renderer_small = EmojiRenderer(36)
        self.emoji_renderer_large = EmojiRenderer(80)

        # Persistent game state
        self.state = self.MENU
        self.category_name: str = ""
        self.current_emojis: list[str] = []
        self.level = 1
        self.score = 0
        self.total_score = 0
        self.combo = 0
        self.max_combo = 0
        self.moves = 0
        self.max_moves = 30
        self.best_match = 0
        self.selected: tuple[int, int] | None = None
        self.swap_pair: tuple[tuple, tuple] | None = None
        self.swap_back = False
        self.grid: list[list[Piece | None]] = []
        self.particles: list[dict] = []
        self.popups: list[dict] = []
        self.match_flash_timer = 0
        self.hint_pos: tuple[int, int] | None = None
        self.hint_timer = 0
        self.shuffle_timer = 0
        self.level_stars: dict[int, int] = {}   # level → stars earned
        self.screen_shake = 0.0

        # Menu buttons
        self._build_menu_buttons()

    # ── Menu ──────────────────────────────────────────────────────────────
    def _build_menu_buttons(self):
        self.cat_names = list(CATEGORIES.keys())
        self.menu_page = 0
        self.total_pages = math.ceil(len(self.cat_names) / PER_PAGE)
        self._rebuild_page_buttons()

    def _rebuild_page_buttons(self):
        self.cat_buttons: list[tuple[str, Button]] = []
        page_names = self.cat_names[self.menu_page * PER_PAGE:
                                      (self.menu_page + 1) * PER_PAGE]
        cols = 4
        bw, bh = 155, 130
        gap_x, gap_y = 12, 10
        total_w = cols * bw + (cols - 1) * gap_x
        start_x = (WINDOW_WIDTH - total_w) // 2
        start_y = 140
        for i, name in enumerate(page_names):
            r, c = divmod(i, cols)
            x = start_x + c * (bw + gap_x)
            y = start_y + r * (bh + gap_y)
            cat = CATEGORIES[name]
            btn = Button(x, y, bw, bh, "", self.info_font,
                         color=(cat["color"][0] // 5 + 20,
                                cat["color"][1] // 5 + 20,
                                cat["color"][2] // 5 + 20),
                         border=cat["color"])
            self.cat_buttons.append((name, btn))
        # Page nav buttons
        nav_y = start_y + (math.ceil(len(page_names) / cols)) * (bh + gap_y) + 5
        self.page_left_btn = Button(WINDOW_WIDTH // 2 - 170, nav_y, 100, 36,
                                    "< Prev", self.info_font)
        self.page_right_btn = Button(WINDOW_WIDTH // 2 + 70, nav_y, 100, 36,
                                     "Next >", self.info_font)
        self.page_nav_y = nav_y

    def _change_page(self, delta: int):
        new_page = self.menu_page + delta
        if 0 <= new_page < self.total_pages:
            self.menu_page = new_page
            self._rebuild_page_buttons()

    def _draw_menu(self):
        self.screen.fill(BG_COLOR)
        # Title
        t = self.title_font.render("Match-3 Emoji Puzzle", True, TEXT_COLOR)
        self.screen.blit(t, (WINDOW_WIDTH // 2 - t.get_width() // 2, 25))
        sub = self.info_font.render("Choose a category to play!", True, SUBTEXT_COLOR)
        self.screen.blit(sub, (WINDOW_WIDTH // 2 - sub.get_width() // 2, 75))

        # Total score
        if self.total_score > 0:
            ts = self.info_font.render(f"Total Score: {self.total_score}", True, SCORE_COLOR)
            self.screen.blit(ts, (WINDOW_WIDTH // 2 - ts.get_width() // 2, 110))

        mouse_pos = pygame.mouse.get_pos()
        for name, btn in self.cat_buttons:
            btn.update(mouse_pos)
            btn.draw(self.screen)
            cat = CATEGORIES[name]
            # Category icon
            icon_surf = self.emoji_renderer_large.get(cat["icon"])
            self.screen.blit(icon_surf, (btn.rect.centerx - icon_surf.get_width() // 2,
                                          btn.rect.y + 8))
            # Category name
            ns = self.score_font.render(name, True, TEXT_COLOR)
            self.screen.blit(ns, (btn.rect.centerx - ns.get_width() // 2, btn.rect.y + 52))
            # Emojis preview (3 rows of 5)
            emojis = cat["emojis"]
            for row_i in range(3):
                chunk = emojis[row_i * 5:(row_i + 1) * 5]
                line = " ".join(chunk)
                ps = self.tiny_font.render(line, True, SUBTEXT_COLOR)
                self.screen.blit(ps, (btn.rect.centerx - ps.get_width() // 2,
                                       btn.rect.y + 78 + row_i * 15))

        # Page navigation
        if self.total_pages > 1:
            self.page_left_btn.update(mouse_pos)
            self.page_right_btn.update(mouse_pos)
            if self.menu_page > 0:
                self.page_left_btn.draw(self.screen)
            if self.menu_page < self.total_pages - 1:
                self.page_right_btn.draw(self.screen)
            page_text = f"Page {self.menu_page + 1} / {self.total_pages}"
            pt = self.info_font.render(page_text, True, SUBTEXT_COLOR)
            self.screen.blit(pt, (WINDOW_WIDTH // 2 - pt.get_width() // 2, self.page_nav_y + 8))

        # Star summary
        if self.level_stars:
            sy = self.page_nav_y + 50
            ss = self.info_font.render("Stars Earned:", True, SUBTEXT_COLOR)
            self.screen.blit(ss, (WINDOW_WIDTH // 2 - ss.get_width() // 2, sy))
            display = []
            for lvl in sorted(self.level_stars.keys()):
                stars_str = "★" * self.level_stars[lvl] + "☆" * (3 - self.level_stars[lvl])
                display.append(f"Lv{lvl}: {stars_str}")
            line = "   ".join(display[:4])
            if len(display) > 4:
                line += "\n" + "   ".join(display[4:])
            for i, l in enumerate(line.split("\n")):
                ds = self.small_font.render(l, True, STAR_FILLED)
                self.screen.blit(ds, (WINDOW_WIDTH // 2 - ds.get_width() // 2, sy + 25 + i * 20))

        # Footer
        hint = self.small_font.render("Click a category to start  |  ESC: Quit", True, SUBTEXT_COLOR)
        self.screen.blit(hint, (WINDOW_WIDTH // 2 - hint.get_width() // 2, WINDOW_HEIGHT - 30))

    # ── Level Setup ───────────────────────────────────────────────────────
    def _start_category(self, cat_name: str):
        self.category_name = cat_name
        self.current_emojis = CATEGORIES[cat_name]["emojis"]
        self.level = 1
        self.total_score = 0
        self.level_stars = {}
        self._start_level()

    def _start_level(self):
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.moves = 0
        self.best_match = 0
        self.selected = None
        self.swap_pair = None
        self.particles.clear()
        self.popups.clear()
        self.hint_pos = None
        self.hint_timer = 0
        self.swap_back = False
        self.screen_shake = 0

        # Progressive difficulty
        self.max_moves = max(15, 35 - (self.level - 1) * 3)
        self._init_grid()
        self.state = self.IDLE

    @property
    def level_target(self) -> int:
        idx = min(self.level - 1, len(LEVEL_TARGETS) - 1)
        return LEVEL_TARGETS[idx]

    @property
    def moves_left(self) -> int:
        return self.max_moves - self.moves

    # ── Grid Init ─────────────────────────────────────────────────────────
    def _init_grid(self):
        self.grid = []
        for r in range(GRID_ROWS):
            row: list[Piece | None] = [None] * GRID_COLS
            self.grid.append(row)
            for c in range(GRID_COLS):
                emoji = self._random_emoji_no_match(r, c)
                self.grid[r][c] = Piece(emoji, r, c)
        self._snap_all()
        # Ensure at least one valid move
        if not self._find_any_move():
            self._init_grid()

    def _random_emoji_no_match(self, row: int, col: int) -> str:
        forbidden: set[str] = set()
        if col >= 2:
            p1, p2 = self.grid[row][col - 1], self.grid[row][col - 2]
            if p1 and p2 and p1.emoji == p2.emoji:
                forbidden.add(p1.emoji)
        if row >= 2:
            p1, p2 = self.grid[row - 1][col], self.grid[row - 2][col]
            if p1 and p2 and p1.emoji == p2.emoji:
                forbidden.add(p1.emoji)
        choices = [e for e in self.current_emojis if e not in forbidden]
        return random.choice(choices or self.current_emojis)

    def _snap_all(self):
        for row in self.grid:
            for p in row:
                if p:
                    p.snap_to_target()

    # ── Match Detection ──────────────────────────────────────────────────
    def _find_matches(self) -> set[tuple[int, int]]:
        matched: set[tuple[int, int]] = set()
        # Horizontal runs
        for r in range(GRID_ROWS):
            c = 0
            while c < GRID_COLS:
                emoji = self.grid[r][c].emoji if self.grid[r][c] else None
                if emoji is None:
                    c += 1
                    continue
                run = [(r, c)]
                nc = c + 1
                while nc < GRID_COLS and self.grid[r][nc] and self.grid[r][nc].emoji == emoji:
                    run.append((r, nc))
                    nc += 1
                if len(run) >= 3:
                    matched.update(run)
                c = nc
        # Vertical runs
        for c in range(GRID_COLS):
            r = 0
            while r < GRID_ROWS:
                emoji = self.grid[r][c].emoji if self.grid[r][c] else None
                if emoji is None:
                    r += 1
                    continue
                run = [(r, c)]
                nr = r + 1
                while nr < GRID_ROWS and self.grid[nr][c] and self.grid[nr][c].emoji == emoji:
                    run.append((nr, c))
                    nr += 1
                if len(run) >= 3:
                    matched.update(run)
                r = nr
        return matched

    def _classify_matches(self, matches: set[tuple[int, int]]):
        """Classify matches into horizontal and vertical runs; return specials to create."""
        specials: list[tuple[int, int, str]] = []  # (row, col, special_type)
        used: set[tuple[int, int]] = set()

        # Horizontal runs
        rows_grouped: dict[int, list[tuple[int, int]]] = {}
        for r, c in matches:
            rows_grouped.setdefault(r, []).append((r, c))
        for r, cells in rows_grouped.items():
            cells.sort(key=lambda x: x[1])
            i = 0
            while i < len(cells):
                run = [cells[i]]
                j = i + 1
                while j < len(cells) and cells[j][1] == cells[j - 1][1] + 1:
                    run.append(cells[j])
                    j += 1
                if len(run) >= 5:
                    # Bomb: place at center
                    mid = run[len(run) // 2]
                    if mid not in used:
                        specials.append((*mid, SPECIAL_BOMB))
                        used.add(mid)
                elif len(run) == 4:
                    # Striped horizontal: place at one end
                    pos = run[1]  # second piece
                    if pos not in used:
                        specials.append((*pos, SPECIAL_STRIPED))
                        used.add(pos)
                i = j

        # Vertical runs
        cols_grouped: dict[int, list[tuple[int, int]]] = {}
        for r, c in matches:
            cols_grouped.setdefault(c, []).append((r, c))
        for c, cells in cols_grouped.items():
            cells.sort(key=lambda x: x[0])
            i = 0
            while i < len(cells):
                run = [cells[i]]
                j = i + 1
                while j < len(cells) and cells[j][0] == cells[j - 1][0] + 1:
                    run.append(cells[j])
                    j += 1
                if len(run) >= 5 and run[len(run) // 2] not in used:
                    mid = run[len(run) // 2]
                    specials.append((*mid, SPECIAL_BOMB))
                    used.add(mid)
                elif len(run) == 4:
                    pos = run[1]
                    if pos not in used:
                        specials.append((*pos, SPECIAL_STRIPED))
                        used.add(pos)
                i = j

        return specials

    # ── Move Detection (for hints & shuffle check) ───────────────────────
    def _find_any_move(self) -> tuple[int, int, int, int] | None:
        """Return (r1,c1,r2,c2) for a valid swap, or None."""
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                # Try swap right
                if c < GRID_COLS - 1:
                    self._swap_grid_data(r, c, r, c + 1)
                    if self._find_matches():
                        self._swap_grid_data(r, c, r, c + 1)
                        return (r, c, r, c + 1)
                    self._swap_grid_data(r, c, r, c + 1)
                # Try swap down
                if r < GRID_ROWS - 1:
                    self._swap_grid_data(r, c, r + 1, c)
                    if self._find_matches():
                        self._swap_grid_data(r, c, r + 1, c)
                        return (r, c, r + 1, c)
                    self._swap_grid_data(r, c, r + 1, c)
        return None

    def _swap_grid_data(self, r1, c1, r2, c2):
        self.grid[r1][c1], self.grid[r2][c2] = self.grid[r2][c2], self.grid[r1][c1]
        if self.grid[r1][c1]:
            self.grid[r1][c1].row, self.grid[r1][c1].col = r1, c1
        if self.grid[r2][c2]:
            self.grid[r2][c2].row, self.grid[r2][c2].col = r2, c2

    # ── Swap Logic ───────────────────────────────────────────────────────
    def _swap_pieces(self, pos1: tuple, pos2: tuple):
        self._swap_grid_data(*pos1, *pos2)
        for pos in (pos1, pos2):
            p = self.grid[pos[0]][pos[1]]
            if p:
                p.update_target()

    def _is_adjacent(self, a: tuple, b: tuple) -> bool:
        return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1

    # ── Special Piece Activation ─────────────────────────────────────────
    def _activate_special(self, piece: Piece) -> set[tuple[int, int]]:
        """Return set of cells to clear when a special piece is activated."""
        cleared: set[tuple[int, int]] = set()
        r, c = piece.row, piece.col

        if piece.special == SPECIAL_STRIPED:
            # Clear entire row and column
            for cc in range(GRID_COLS):
                if self.grid[r][cc]:
                    cleared.add((r, cc))
            for rr in range(GRID_ROWS):
                if self.grid[rr][c]:
                    cleared.add((rr, c))
            self.screen_shake = 6.0

        elif piece.special == SPECIAL_BOMB:
            # Clear all pieces of the same emoji type
            target_emoji = piece.emoji
            for rr in range(GRID_ROWS):
                for cc in range(GRID_COLS):
                    p = self.grid[rr][cc]
                    if p and p.emoji == target_emoji:
                        cleared.add((rr, cc))
            self.screen_shake = 10.0

        return cleared

    # ── Gravity & Fill ───────────────────────────────────────────────────
    def _apply_gravity(self):
        moved = False
        for c in range(GRID_COLS):
            write_row = GRID_ROWS - 1
            for r in range(GRID_ROWS - 1, -1, -1):
                if self.grid[r][c] is not None:
                    if r != write_row:
                        self.grid[write_row][c] = self.grid[r][c]
                        self.grid[r][c] = None
                        self.grid[write_row][c].row = write_row
                        self.grid[write_row][c].update_target()
                        self.grid[write_row][c].bounce = -8.0  # bounce on land
                        moved = True
                    write_row -= 1
            for r in range(write_row, -1, -1):
                emoji = random.choice(self.current_emojis)
                piece = Piece(emoji, r, c)
                piece.y = float(GRID_OFFSET_Y - (write_row - r + 1) * CELL_SIZE)
                self.grid[r][c] = piece
                piece.update_target()
                piece.bounce = -6.0
                moved = True
        return moved

    def _shuffle_grid(self):
        """Shuffle the grid preserving positions but randomizing emojis."""
        emojis = [p.emoji for row in self.grid for p in row if p]
        random.shuffle(emojis)
        idx = 0
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c]:
                    self.grid[r][c].emoji = emojis[idx]
                    self.grid[r][c].special = SPECIAL_NONE
                    idx += 1
        # Remove any pre-existing matches by re-shuffling if needed
        if self._find_matches():
            self._shuffle_grid()
            return
        if not self._find_any_move():
            self._shuffle_grid()

    # ── Particles & Effects ──────────────────────────────────────────────
    def _spawn_particles(self, row, col, emoji, count=8):
        cx = GRID_OFFSET_X + col * CELL_SIZE + CELL_SIZE // 2
        cy = GRID_OFFSET_Y + row * CELL_SIZE + CELL_SIZE // 2
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2.0, 6.0)
            self.particles.append({
                "x": float(cx), "y": float(cy),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed - 2.5,
                "life": random.uniform(0.6, 1.4),
                "emoji": emoji,
                "size": random.randint(8, 18),
            })

    def _spawn_ring_particles(self, row, col, emoji, count=16):
        cx = GRID_OFFSET_X + col * CELL_SIZE + CELL_SIZE // 2
        cy = GRID_OFFSET_Y + row * CELL_SIZE + CELL_SIZE // 2
        for i in range(count):
            angle = (2 * math.pi * i) / count
            speed = 4.0
            self.particles.append({
                "x": float(cx), "y": float(cy),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": 0.8,
                "emoji": emoji,
                "size": 14,
            })

    def _add_popup(self, text, x, y, color=None):
        self.popups.append({
            "text": text, "x": x, "y": y,
            "life": 1.8, "vy": -1.2,
            "color": color or SCORE_COLOR,
        })

    # ── Input ────────────────────────────────────────────────────────────
    def _handle_click(self, pos):
        if self.state == self.MENU:
            # Check page nav
            if self.total_pages > 1:
                if self.menu_page > 0 and self.page_left_btn.clicked(pos):
                    self._change_page(-1)
                    return
                if self.menu_page < self.total_pages - 1 and self.page_right_btn.clicked(pos):
                    self._change_page(1)
                    return
            for name, btn in self.cat_buttons:
                if btn.clicked(pos):
                    self._start_category(name)
                    return
            return

        if self.state in (self.GAME_OVER, self.LEVEL_WIN):
            # Click anywhere to continue
            if self.state == self.LEVEL_WIN:
                self.level += 1
                self.total_score += self.score
                self._start_level()
            else:
                self.state = self.MENU
            return

        if self.state not in (self.IDLE, self.SELECTED):
            return

        mx, my = pos
        col = (mx - GRID_OFFSET_X) // CELL_SIZE
        row = (my - GRID_OFFSET_Y) // CELL_SIZE

        if not (0 <= row < GRID_ROWS and 0 <= col < GRID_COLS):
            self.selected = None
            self.state = self.IDLE
            self.hint_pos = None
            return

        if self.state == self.IDLE:
            self.selected = (row, col)
            self.state = self.SELECTED
            self.hint_pos = None
        elif self.state == self.SELECTED:
            if (row, col) == self.selected:
                self.selected = None
                self.state = self.IDLE
            elif self._is_adjacent(self.selected, (row, col)):
                self.swap_pair = (self.selected, (row, col))
                self.swap_back = False
                self._swap_pieces(self.selected, (row, col))
                self.state = self.SWAPPING
                self.selected = None
                self.hint_pos = None
            else:
                self.selected = (row, col)

    # ── Update ───────────────────────────────────────────────────────────
    def update(self, dt: float):
        if self.state == self.MENU:
            return

        # Animate pieces
        any_animating = False
        for row in self.grid:
            for p in row:
                if p and p.is_animating:
                    p.animate(ANIM_SPEED)
                    any_animating = True
                elif p and (abs(p.bounce) > 0.3 or abs(p.wobble) > 0.01):
                    any_animating = True

        # Screen shake decay
        if self.screen_shake > 0:
            self.screen_shake *= 0.85
            if self.screen_shake < 0.3:
                self.screen_shake = 0

        # Particles
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.15
            p["life"] -= dt
        self.particles = [p for p in self.particles if p["life"] > 0]

        # Popups
        for p in self.popups:
            p["y"] += p["vy"]
            p["life"] -= dt
        self.popups = [p for p in self.popups if p["life"] > 0]

        # Hint timer
        if self.hint_timer > 0:
            self.hint_timer -= dt
            if self.hint_timer <= 0:
                self.hint_pos = None

        # Shuffle timer
        if self.shuffle_timer > 0:
            self.shuffle_timer -= dt
            if self.shuffle_timer <= 0:
                self._shuffle_grid()
                self._snap_all()
                self.state = self.IDLE

        # State machine
        if self.state == self.SWAPPING and not any_animating:
            matches = self._find_matches()
            if matches or self.swap_back:
                if matches:
                    self.swap_back = False
                    self.combo = 0
                    self.moves += 1
                    self._start_remove(matches)
                else:
                    self.swap_back = True
                    self._swap_pieces(*self.swap_pair)
                    self.state = self.SWAPPING
            else:
                self.state = self.IDLE
                self._check_no_moves()

        elif self.state == self.REMOVING:
            self.match_flash_timer -= dt
            if self.match_flash_timer <= 0:
                # Process removal and specials
                extra_to_clear: set[tuple[int, int]] = set()
                for r in range(GRID_ROWS):
                    for c in range(GRID_COLS):
                        p = self.grid[r][c]
                        if p and p.matched and p.special != SPECIAL_NONE:
                            extra = self._activate_special(p)
                            extra_to_clear |= extra
                # Mark extras
                for r, c in extra_to_clear:
                    p = self.grid[r][c]
                    if p and not p.matched:
                        p.matched = True
                        self._spawn_particles(r, c, p.emoji, 4)

                # Remove all matched
                for r in range(GRID_ROWS):
                    for c in range(GRID_COLS):
                        p = self.grid[r][c]
                        if p and p.matched:
                            self.grid[r][c] = None

                self._apply_gravity()
                self.state = self.FALLING

        elif self.state == self.FALLING and not any_animating:
            matches = self._find_matches()
            if matches:
                self._start_remove(matches)
            else:
                if self.combo > self.max_combo:
                    self.max_combo = self.combo
                self.combo = 0
                self.state = self.IDLE
                # Check win/lose
                if self.score >= self.level_target:
                    self.state = self.LEVEL_WIN
                elif self.moves >= self.max_moves:
                    self.state = self.GAME_OVER
                else:
                    self._check_no_moves()

    def _check_no_moves(self):
        if self.state != self.IDLE:
            return
        if not self._find_any_move():
            self.shuffle_timer = 0.8
            self._add_popup("No moves! Shuffling...",
                            WINDOW_WIDTH // 2, GRID_OFFSET_Y - 25, COMBO_COLOR)

    def _start_remove(self, matches: set[tuple[int, int]]):
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        if len(matches) > self.best_match:
            self.best_match = len(matches)

        points = len(matches) * 10 * self.combo
        self.score += points

        # Classify and create specials
        specials = self._classify_matches(matches)

        avg_x = sum(GRID_OFFSET_X + c * CELL_SIZE + CELL_SIZE // 2 for _, c in matches) / len(matches)
        avg_y = sum(GRID_OFFSET_Y + r * CELL_SIZE + CELL_SIZE // 2 for r, _ in matches) / len(matches)

        if self.combo > 1:
            self._add_popup(f"+{points}  x{self.combo} COMBO!", avg_x, avg_y, COMBO_COLOR)
        elif len(matches) >= 5:
            self._add_popup(f"+{points}  AMAZING!", avg_x, avg_y, (243, 139, 168))
        elif len(matches) == 4:
            self._add_popup(f"+{points}  GREAT!", avg_x, avg_y, HINT_COLOR)
        else:
            self._add_popup(f"+{points}", avg_x, avg_y)

        for r, c in matches:
            p = self.grid[r][c]
            if p:
                p.matched = True
                if p.special != SPECIAL_NONE:
                    self._spawn_ring_particles(r, c, p.emoji, 20)
                else:
                    self._spawn_particles(r, c, p.emoji, 6)

        # Create special pieces (replace matched ones that aren't already special)
        for sr, sc, stype in specials:
            p = self.grid[sr][sc]
            if p and p.matched:
                emoji = p.emoji
                self.grid[sr][sc] = Piece(emoji, sr, sc, special=stype)
                self.grid[sr][sc].snap_to_target()
                if stype == SPECIAL_BOMB:
                    self._add_popup("BOMB!", GRID_OFFSET_X + sc * CELL_SIZE + CELL_SIZE // 2,
                                    GRID_OFFSET_Y + sr * CELL_SIZE, (243, 139, 168))
                else:
                    self._add_popup("STRIPED!", GRID_OFFSET_X + sc * CELL_SIZE + CELL_SIZE // 2,
                                    GRID_OFFSET_Y + sr * CELL_SIZE, HINT_COLOR)

        self.match_flash_timer = 0.2
        self.state = self.REMOVING

    # ── Hint ─────────────────────────────────────────────────────────────
    def _show_hint(self):
        if self.state not in (self.IDLE, self.SELECTED):
            return
        move = self._find_any_move()
        if move:
            r1, c1, r2, c2 = move
            self.hint_pos = (r1, c1)
            self.hint_timer = 2.0
            if self.grid[r1][c1]:
                self.grid[r1][c1].wobble = 0.5
            if self.grid[r2][c2]:
                self.grid[r2][c2].wobble = 0.5

    # ── Star Rating ──────────────────────────────────────────────────────
    def _get_stars(self) -> int:
        ratio = self.score / max(1, self.level_target)
        stars = 0
        for thresh in STAR_THRESHOLDS:
            if ratio >= thresh:
                stars += 1
        return stars

    # ── Draw ─────────────────────────────────────────────────────────────
    def draw(self):
        if self.state == self.MENU:
            self._draw_menu()
            pygame.display.flip()
            return

        # Screen shake offset
        shake_x = random.randint(int(-self.screen_shake), int(self.screen_shake)) if self.screen_shake > 0 else 0
        shake_y = random.randint(int(-self.screen_shake), int(self.screen_shake)) if self.screen_shake > 0 else 0

        self.screen.fill(BG_COLOR)
        # Create offset surface for shake
        canvas = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)

        self._draw_header(canvas)
        self._draw_progress_bar(canvas)

        # Grid background
        gr = pygame.Rect(GRID_OFFSET_X - 6, GRID_OFFSET_Y - 6,
                         GRID_COLS * CELL_SIZE + 12, GRID_ROWS * CELL_SIZE + 12)
        cat_color = CATEGORIES.get(self.category_name, {}).get("color", PANEL_BORDER)
        pygame.draw.rect(canvas, GRID_BG_COLOR, gr, border_radius=12)
        pygame.draw.rect(canvas, (*cat_color, 80), gr, 2, border_radius=12)

        mouse_pos = pygame.mouse.get_pos()
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                self._draw_cell(canvas, r, c, mouse_pos)

        # Selection
        if self.selected and self.state == self.SELECTED:
            sr, sc = self.selected
            sel_rect = pygame.Rect(GRID_OFFSET_X + sc * CELL_SIZE - 3,
                                   GRID_OFFSET_Y + sr * CELL_SIZE - 3,
                                   CELL_SIZE + 6, CELL_SIZE + 6)
            pulse = int(128 + 127 * math.sin(time.time() * 6))
            bc = (pulse, 255, min(255, pulse + 50))
            pygame.draw.rect(canvas, bc, sel_rect, 3, border_radius=8)

        # Hint highlight
        if self.hint_pos and self.hint_timer > 0:
            hr, hc = self.hint_pos
            hint_alpha = int(128 + 127 * math.sin(time.time() * 8))
            hint_rect = pygame.Rect(GRID_OFFSET_X + hc * CELL_SIZE - 2,
                                    GRID_OFFSET_Y + hr * CELL_SIZE - 2,
                                    CELL_SIZE + 4, CELL_SIZE + 4)
            hint_surf = pygame.Surface((CELL_SIZE + 4, CELL_SIZE + 4), pygame.SRCALPHA)
            pygame.draw.rect(hint_surf, (*HINT_COLOR, hint_alpha), hint_surf.get_rect(), 3, border_radius=8)
            canvas.blit(hint_surf, hint_rect.topleft)

        # Particles
        for p in self.particles:
            alpha = max(0, min(255, int(255 * (p["life"] / 1.0))))
            surf = self.emoji_renderer.get(p["emoji"])
            sz = p["size"]
            scaled = pygame.transform.smoothscale(surf, (sz, sz))
            scaled.set_alpha(alpha)
            canvas.blit(scaled, (int(p["x"] - sz // 2), int(p["y"] - sz // 2)))

        # Popups
        for p in self.popups:
            alpha = max(0, min(255, int(255 * (p["life"] / 1.8))))
            ts = self.score_font.render(p["text"], True, p.get("color", SCORE_COLOR))
            ts.set_alpha(alpha)
            canvas.blit(ts, (int(p["x"] - ts.get_width() // 2), int(p["y"])))

        # Overlays
        if self.state == self.GAME_OVER:
            self._draw_game_over(canvas)
        elif self.state == self.LEVEL_WIN:
            self._draw_level_win(canvas)

        # Footer
        hint = self.small_font.render("H: Hint  |  R: Restart  |  ESC: Menu", True, SUBTEXT_COLOR)
        canvas.blit(hint, (WINDOW_WIDTH // 2 - hint.get_width() // 2, WINDOW_HEIGHT - 30))

        # Shuffle indicator
        if self.shuffle_timer > 0:
            shuf = self.big_font.render("Shuffling...", True, COMBO_COLOR)
            shuf.set_alpha(int(255 * min(1, self.shuffle_timer / 0.4)))
            canvas.blit(shuf, (WINDOW_WIDTH // 2 - shuf.get_width() // 2, GRID_OFFSET_Y + GRID_ROWS * CELL_SIZE // 2 - 20))

        self.screen.blit(canvas, (shake_x, shake_y))
        pygame.display.flip()

    def _draw_header(self, surface):
        cat = CATEGORIES.get(self.category_name, {})
        # Category icon + name
        icon = cat.get("icon", "")
        icon_surf = self.emoji_renderer_small.get(icon)
        surface.blit(icon_surf, (15, 8))

        title = self.big_font.render(f"{self.category_name}  Lv.{self.level}", True, TEXT_COLOR)
        surface.blit(title, (50, 5))

        # Score
        st = self.score_font.render(f"Score: {self.score}", True, SCORE_COLOR)
        surface.blit(st, (15, 55))

        # Target
        target_color = (243, 139, 168) if self.score < self.level_target else SCORE_COLOR
        tt = self.info_font.render(f"Target: {self.level_target}", True, target_color)
        surface.blit(tt, (15, 88))

        # Moves
        ml = self.moves_left
        mc = (243, 139, 168) if ml <= 5 else ((COMBO_COLOR if ml <= 10 else TEXT_COLOR))
        mt = self.score_font.render(f"Moves: {ml}", True, mc)
        surface.blit(mt, (WINDOW_WIDTH - mt.get_width() - 15, 55))

        # Combo
        if self.combo > 1:
            ct = self.info_font.render(f"Combo x{self.combo}!", True, COMBO_COLOR)
            surface.blit(ct, (WINDOW_WIDTH - ct.get_width() - 15, 88))

        # Stars preview
        stars = self._get_stars()
        star_str = "★" * stars + "☆" * (3 - stars)
        st_surf = self.info_font.render(star_str, True, STAR_FILLED)
        surface.blit(st_surf, (WINDOW_WIDTH - st_surf.get_width() - 15, 115))

    def _draw_progress_bar(self, surface):
        bar_x = 15
        bar_y = 140
        bar_w = WINDOW_WIDTH - 30
        bar_h = 10
        pygame.draw.rect(surface, PROGRESS_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=5)
        fill_w = int(bar_w * min(1.0, self.score / max(1, self.level_target)))
        if fill_w > 0:
            cat_color = CATEGORIES.get(self.category_name, {}).get("color", PROGRESS_FG)
            pygame.draw.rect(surface, cat_color, (bar_x, bar_y, fill_w, bar_h), border_radius=5)
        # Target marker
        if self.score < self.level_target:
            tx = bar_x + bar_w - 1
            pygame.draw.line(surface, TEXT_COLOR, (tx, bar_y - 2), (tx, bar_y + bar_h + 2), 2)

    def _draw_cell(self, surface, row, col, mouse_pos):
        x = GRID_OFFSET_X + col * CELL_SIZE
        y = GRID_OFFSET_Y + row * CELL_SIZE
        rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)

        is_hover = rect.collidepoint(mouse_pos) and self.state in (self.IDLE, self.SELECTED)
        bg = CELL_HOVER if is_hover else CELL_BG
        pygame.draw.rect(surface, bg, rect, border_radius=6)

        piece = self.grid[row][col]
        if piece is None:
            return

        # Matched flash
        if piece.matched and self.state == self.REMOVING:
            fa = int(200 * max(0, self.match_flash_timer / 0.2))
            fs = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            fs.fill((*MATCH_FLASH, fa))
            surface.blit(fs, (x, y))

        # Emoji
        emoji_surf = self.emoji_renderer.get(piece.emoji)
        w = emoji_surf.get_width()
        h = emoji_surf.get_height()

        # Apply wobble
        wobble_offset_x = 0
        if abs(piece.wobble) > 0.01:
            wobble_offset_x = math.sin(time.time() * 15) * piece.wobble * 10

        # Apply bounce
        bounce_offset_y = piece.bounce

        # Apply scale for matched shrink
        shrink = 1.0
        if piece.matched and self.state == self.REMOVING:
            shrink = max(0.1, self.match_flash_timer / 0.2)

        dw = int(w * shrink)
        dh = int(h * shrink)
        if dw > 0 and dh > 0:
            draw_surf = emoji_surf
            if shrink != 1.0:
                draw_surf = pygame.transform.smoothscale(emoji_surf, (dw, dh))
            dx = int(piece.x + (CELL_SIZE - dw) // 2 + wobble_offset_x)
            dy = int(piece.y + (CELL_SIZE - dh) // 2 + bounce_offset_y)
            surface.blit(draw_surf, (dx, dy))

        # Special piece indicators
        if piece.special == SPECIAL_STRIPED and not piece.matched:
            # Draw subtle striped lines
            indicator = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            for i in range(0, CELL_SIZE, 8):
                pygame.draw.line(indicator, (255, 255, 255, 50), (i, 0), (i, CELL_SIZE), 1)
            surface.blit(indicator, (x, y))
            # Small arrows
            arrow_color = (255, 255, 255, 120)
            arrow_surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            cx, cy = CELL_SIZE // 2, CELL_SIZE // 2
            # Horizontal arrow
            pygame.draw.line(arrow_surf, arrow_color, (8, cy), (CELL_SIZE - 8, cy), 2)
            pygame.draw.polygon(arrow_surf, arrow_color, [
                (CELL_SIZE - 8, cy), (CELL_SIZE - 14, cy - 5), (CELL_SIZE - 14, cy + 5)])
            pygame.draw.polygon(arrow_surf, arrow_color, [
                (8, cy), (14, cy - 5), (14, cy + 5)])
            # Vertical arrow
            pygame.draw.line(arrow_surf, arrow_color, (cx, 8), (cx, CELL_SIZE - 8), 2)
            pygame.draw.polygon(arrow_surf, arrow_color, [
                (cx, 8), (cx - 5, 14), (cx + 5, 14)])
            pygame.draw.polygon(arrow_surf, arrow_color, [
                (cx, CELL_SIZE - 8), (cx - 5, CELL_SIZE - 14), (cx + 5, CELL_SIZE - 14)])
            surface.blit(arrow_surf, (x, y))

        elif piece.special == SPECIAL_BOMB and not piece.matched:
            # Pulsing glow
            pulse = int(60 + 40 * math.sin(time.time() * 4))
            glow = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            pygame.draw.circle(glow, (243, 139, 168, pulse),
                               (CELL_SIZE // 2, CELL_SIZE // 2), CELL_SIZE // 2)
            surface.blit(glow, (x, y))
            # "B" label
            b_surf = self.small_font.render("B", True, (255, 255, 255))
            b_surf.set_alpha(180)
            surface.blit(b_surf, (x + CELL_SIZE - 14, y + 2))

    def _draw_game_over(self, surface):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))

        pw, ph = 380, 300
        px = WINDOW_WIDTH // 2 - pw // 2
        py = WINDOW_HEIGHT // 2 - ph // 2
        panel = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(surface, PANEL_COLOR, panel, border_radius=16)
        pygame.draw.rect(surface, (243, 139, 168), panel, 3, border_radius=16)

        go = self.title_font.render("Game Over!", True, (243, 139, 168))
        surface.blit(go, (WINDOW_WIDTH // 2 - go.get_width() // 2, py + 20))

        lines = [
            (f"Final Score: {self.score}", SCORE_COLOR),
            (f"Level Reached: {self.level}", TEXT_COLOR),
            (f"Best Combo: x{self.max_combo}", COMBO_COLOR),
            (f"Largest Match: {self.best_match} pieces", HINT_COLOR),
        ]
        for i, (text, color) in enumerate(lines):
            ts = self.info_font.render(text, True, color)
            surface.blit(ts, (WINDOW_WIDTH // 2 - ts.get_width() // 2, py + 70 + i * 30))

        hint = self.info_font.render("Click to return to menu", True, SUBTEXT_COLOR)
        surface.blit(hint, (WINDOW_WIDTH // 2 - hint.get_width() // 2, py + 255))

    def _draw_level_win(self, surface):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))

        pw, ph = 400, 340
        px = WINDOW_WIDTH // 2 - pw // 2
        py = WINDOW_HEIGHT // 2 - ph // 2
        panel = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(surface, PANEL_COLOR, panel, border_radius=16)
        pygame.draw.rect(surface, SCORE_COLOR, panel, 3, border_radius=16)

        wt = self.title_font.render("Level Complete!", True, SCORE_COLOR)
        surface.blit(wt, (WINDOW_WIDTH // 2 - wt.get_width() // 2, py + 15))

        # Stars
        stars = self._get_stars()
        self.level_stars[self.level] = max(self.level_stars.get(self.level, 0), stars)
        star_str = "★" * stars + "☆" * (3 - stars)
        star_color = STAR_FILLED if stars > 0 else STAR_EMPTY
        ss = self.big_font.render(star_str, True, star_color)
        surface.blit(ss, (WINDOW_WIDTH // 2 - ss.get_width() // 2, py + 65))

        lines = [
            (f"Score: {self.score} / {self.level_target}", SCORE_COLOR),
            (f"Moves Used: {self.moves}", TEXT_COLOR),
            (f"Best Combo: x{self.max_combo}", COMBO_COLOR),
            (f"Largest Match: {self.best_match} pieces", HINT_COLOR),
        ]
        for i, (text, color) in enumerate(lines):
            ts = self.info_font.render(text, True, color)
            surface.blit(ts, (WINDOW_WIDTH // 2 - ts.get_width() // 2, py + 115 + i * 30))

        # Category icon
        cat_icon = CATEGORIES.get(self.category_name, {}).get("icon", "")
        icon_s = self.emoji_renderer_large.get(cat_icon)
        surface.blit(icon_s, (WINDOW_WIDTH // 2 - icon_s.get_width() // 2, py + 230))

        hint = self.info_font.render("Click for next level!", True, SUBTEXT_COLOR)
        surface.blit(hint, (WINDOW_WIDTH // 2 - hint.get_width() // 2, py + 305))

    # ── Restart ──────────────────────────────────────────────────────────
    def restart(self):
        if self.state == self.MENU:
            return
        self._start_level()

    # ── Main Loop ────────────────────────────────────────────────────────
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state != self.MENU:
                            self.state = self.MENU
                        else:
                            running = False
                    elif event.key == pygame.K_r:
                        self.restart()
                    elif event.key == pygame.K_h:
                        self._show_hint()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    game = Match3Game()
    game.run()