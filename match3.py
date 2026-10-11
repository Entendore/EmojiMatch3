"""
Match-3 Deluxe: Synthwave Edition
Features: Mini-DAW procedural audio, complex waveforms, lush SFX, 8-bar music loop.

Install:  pip install pygame-ce numpy
Run:      python match3.py
"""
import pygame
import numpy as np
import random
import math
import json
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

# ───────── Reproducibility ─────────
SEED = 1337
random.seed(SEED)
np.random.seed(SEED)

# ───────── Config ─────────
SCREEN_W, SCREEN_H = 450, 800
GRID_N      = 8
CELL        = 48
GRID_PX     = GRID_N * CELL
GRID_X      = (SCREEN_W - GRID_PX) // 2
GRID_Y      = 220
GAME_TIME   = 60.0
MOVES_MODE  = 30
FPS         = 60
HINT_DELAY  = 5.0

BG_TOP    = (18, 16, 38)
BG_BOTTOM = (42, 30, 72)
PANEL     = (30, 26, 60)
PANEL_HI  = (52, 44, 96)
GRID_BG   = (20, 18, 42)
GRID_CELL = (34, 30, 62)
TEXT      = (245, 245, 255)
TEXT_DIM  = (170, 170, 195)
ACCENT    = (255, 215, 110)
DANGER    = (255,  90, 110)
GOOD      = (110, 230, 140)
WOOD      = (120, 80, 45)
WOOD_DARK = (80, 50, 25)
ICE_COL   = (150, 220, 255)
STONE_COL = (120, 120, 130)

GEM_TYPES = 8
GEM_COLORS = [
    (245,  90, 110), (255, 155,  60), (255, 220,  90),
    ( 95, 220, 130), ( 90, 185, 245), (205, 125, 245),
    (255, 105, 180), (  0, 200, 200),
]
GEM_HIGHLIGHT = [
    (255, 165, 180), (255, 195, 130), (255, 240, 150),
    (165, 240, 180), (160, 215, 255), (225, 175, 255),
    (255, 180, 210), (120, 230, 230),
]

SPECIAL_NONE   = 0
SPECIAL_H_LINE = 1
SPECIAL_V_LINE = 2
SPECIAL_BOMB   = 3
SPECIAL_COLOR  = 4

BLOCKER_NONE  = 0
BLOCKER_ICE   = 1
BLOCKER_CRATE = 2
BLOCKER_STONE = 3
BLOCKER_HP    = {BLOCKER_ICE: 1, BLOCKER_CRATE: 2, BLOCKER_STONE: 3}

HIGHSCORE_FILE = Path.home() / ".match3_synthwave_highscore.json"

# ───────── Easing ─────────
def ease_out_cubic(t):    return 1 - (1 - t) ** 3
def ease_in_cubic(t):     return t ** 3
def ease_out_back(t):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1)**3 + c1 * (t - 1)**2
def lerp(a, b, t): return a + (b - a) * t
def clamp(v, lo, hi): return max(lo, min(hi, v))

class GameState(Enum):
    MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()

# ───────── Audio (Mini-DAW) ─────────
class Audio:
    def __init__(self):
        self.enabled = True
        self.muted = False
        self.music_playing = False
        try:
            pygame.mixer.pre_init(44100, -16, 2, 256)
            pygame.mixer.init()
        except pygame.error:
            self.enabled = False
            return
        self.sr = 44100
        self.sounds = {}
        self.music_channel = pygame.mixer.Channel(7)
        self._build()
        self._build_music()

    def _make(self, samples):
        if not self.enabled: return None
        s = np.clip(samples, -1, 1)
        s = (s * 32767).astype(np.int16)
        stereo = np.column_stack([s, s])
        return pygame.sndarray.make_sound(stereo)

    def _pitch_shift(self, samples, factor):
        if not self.enabled: return None
        indices = np.arange(0, len(samples), factor)
        shifted = np.interp(indices, np.arange(len(samples)), samples)
        return self._make(shifted)

    # --- Waveform Generators ---
    def _wave_sine(self, f, t, phase=0):
        return np.sin(2 * np.pi * f * t + phase)

    def _wave_saw(self, f, t):
        # Careful with phase wrapping for sawtooth
        return 2 * (t * f - np.floor(0.5 + t * f))

    def _wave_square(self, f, t):
        return np.sign(np.sin(2 * np.pi * f * t))

    def _wave_triangle(self, f, t):
        return 2 * np.abs(2 * (t * f - np.floor(t * f + 0.5))) - 1

    def _wave_noise(self, t):
        return np.random.uniform(-1, 1, len(t))

    def _env_adsr(self, t, attack, decay, sustain, release, dur):
        env = np.zeros_like(t)
        a_len = int(attack * len(t))
        d_len = int(decay * len(t))
        s_len = int((dur - attack - decay - release) * len(t))
        r_len = len(t) - a_len - d_len - s_len
        
        if a_len > 0: env[:a_len] = np.linspace(0, 1, a_len)
        if d_len > 0: env[a_len:a_len+d_len] = np.linspace(1, sustain, d_len)
        if s_len > 0: env[a_len+d_len:a_len+d_len+s_len] = sustain
        if r_len > 0: env[a_len+d_len+s_len:] = np.linspace(sustain, 0, r_len)
        return env

    def _env_exp(self, t, decay):
        return np.exp(-t * decay)

    # --- SFX Synthesis ---
    def _build(self):
        sr = self.sr
        
        # Swap: Quick upward sine sweep
        t = np.arange(int(sr * 0.08)) / sr
        freq = 400 + 1200 * t
        self.sounds['swap'] = self._make(0.3 * self._env_exp(t, 20) * self._wave_sine(freq, t))
        
        # Fail: Detuned sawtooth slide down
        t = np.arange(int(sr * 0.18)) / sr
        freq = 200 - 80 * t
        wave = 0.4 * self._wave_saw(freq, t) + 0.2 * self._wave_saw(freq*1.01, t)
        self.sounds['fail'] = self._make(wave * self._env_exp(t, 10))
        
        # Game Over: Sad triangle descent
        t = np.arange(int(sr * 0.8)) / sr
        freq = 300 - 200 * t
        self.sounds['over'] = self._make(0.5 * self._env_exp(t, 3) * self._wave_triangle(freq, t))
        
        # Click: Very short high sine
        t = np.arange(int(sr * 0.04)) / sr
        self.sounds['click'] = self._make(0.3 * self._env_exp(t, 60) * self._wave_sine(1200, t))
        
        # Hammer: Metallic clang (multiple high sines + noise)
        t = np.arange(int(sr * 0.15)) / sr
        env = self._env_exp(t, 15)
        wave = 0.3 * self._wave_sine(800, t) + 0.2 * self._wave_sine(1200, t) + 0.2 * self._wave_sine(1600, t) + 0.4 * self._wave_noise(t)
        self.sounds['hammer'] = self._make(wave * env)
        
        # Ice: Glass shatter (high noise + high sine sweep)
        t = np.arange(int(sr * 0.15)) / sr
        env = self._env_exp(t, 20)
        freq = 3000 + 2000 * np.exp(-t * 30)
        wave = 0.3 * self._wave_sine(freq, t) + 0.6 * self._wave_noise(t)
        self.sounds['ice'] = self._make(wave * env)
        
        # Stone: Low thud + gravel noise
        t = np.arange(int(sr * 0.2)) / sr
        env = self._env_exp(t, 12)
        freq = 80 + 40 * np.exp(-t * 30)
        wave = 0.5 * self._wave_sine(freq, t) + 0.5 * self._wave_noise(t)
        self.sounds['stone'] = self._make(wave * env)
        
        # Crate: Wood knock (mid square + noise)
        t = np.arange(int(sr * 0.15)) / sr
        env = self._env_exp(t, 18)
        freq = 250 - 100 * t
        wave = 0.3 * self._wave_square(freq, t) + 0.4 * self._wave_noise(t)
        self.sounds['crate'] = self._make(wave * env)
        
        # Match: Bright bell (Additive synthesis)
        t = np.arange(int(sr * 0.3)) / sr
        env = self._env_exp(t, 6)
        freq = 440 + 600 * t
        wave = 0.4 * self._wave_sine(freq, t) + 0.2 * self._wave_sine(freq*2, t) + 0.1 * self._wave_sine(freq*3, t)
        self.base_match = wave * env
        
        # Special: Deep impact + sparkles
        t = np.arange(int(sr * 0.4)) / sr
        env = self._env_exp(t, 5)
        freq = 150 + 800 * np.exp(-t * 8)
        wave = 0.4 * self._wave_sine(freq, t) + 0.3 * self._wave_noise(t) + 0.2 * self._wave_triangle(880, t)
        self.sounds['special'] = self._make(wave * env)
        
        # Shuffle: Fast ascending arpeggio
        t = np.arange(int(sr * 0.4)) / sr
        env = self._env_exp(t, 4)
        freq = 300 + 800 * t
        wave = 0.3 * self._wave_square(freq, t) + 0.2 * self._wave_sine(freq*2, t)
        self.sounds['shuffle'] = self._make(wave * env)
        
        # Level Up: Major chord (C-E-G-C) using triangles
        t = np.arange(int(sr * 0.6)) / sr
        env = self._env_adsr(t, 0.01, 0.1, 0.8, 0.2, 0.6)
        wave = 0.2 * self._wave_triangle(261.63, t) + 0.2 * self._wave_triangle(329.63, t) + 0.2 * self._wave_triangle(392.00, t) + 0.2 * self._wave_triangle(523.25, t)
        self.sounds['levelup'] = self._make(wave * env)
        
        # Frenzy: Rising pitch sweep with vibrato
        t = np.arange(int(sr * 0.6)) / sr
        env = self._env_exp(t, 3)
        freq = 200 + 1000 * t
        vibrato = 1 + 0.03 * self._wave_sine(10, t)
        wave = 0.4 * self._wave_saw(freq * vibrato, t)
        self.sounds['frenzy'] = self._make(wave * env)
        
        # Tick: Short electronic beep
        t = np.arange(int(sr * 0.05)) / sr
        env = self._env_exp(t, 40)
        wave = 0.3 * self._wave_square(880, t)
        self.sounds['tick'] = self._make(wave * env)

    # --- Music Synthesis (8-bar Synthwave Loop) ---
    def _build_music(self):
        sr = self.sr
        bpm = 100
        beat_len = 60.0 / bpm
        total_beats = 32  # 8 bars
        dur = total_beats * beat_len
        t_full = np.arange(int(sr * dur)) / sr
        
        # Tracks
        track_drums = np.zeros_like(t_full)
        track_bass = np.zeros_like(t_full)
        track_pad = np.zeros_like(t_full)
        track_arp = np.zeros_like(t_full)
        
        # Chord Progression: Am - F - C - G (2 bars each)
        chords = [
            [220.00, 261.63, 329.63], # Am
            [174.61, 220.00, 261.63], # F
            [130.81, 164.81, 196.00], # C
            [196.00, 246.94, 293.66]  # G
        ]
        bass_notes = [55.00, 43.65, 32.70, 49.00] # A1, F1, C1, G1
        
        def add_note(track, start_sec, note_dur, freq, wave_type, vol, env_decay=None, env_adsr=None):
            start_idx = int(start_sec * sr)
            end_idx = int((start_sec + note_dur) * sr)
            if end_idx > len(track): end_idx = len(track)
            if start_idx >= len(track): return
            
            seg_len = end_idx - start_idx
            if seg_len <= 0: return
            t = np.arange(seg_len) / sr
            
            if env_decay:
                env = self._env_exp(t, env_decay)
            elif env_adsr:
                a, d, s, r = env_adsr
                env = self._env_adsr(t, a, d, s, r, note_dur)
            else:
                env = np.ones_like(t)
                
            if wave_type == 'sine': wave = self._wave_sine(freq, t)
            elif wave_type == 'saw': wave = self._wave_saw(freq, t)
            elif wave_type == 'square': wave = self._wave_square(freq, t)
            elif wave_type == 'triangle': wave = self._wave_triangle(freq, t)
            elif wave_type == 'noise': wave = self._wave_noise(t)
            else: wave = self._wave_sine(freq, t)
            
            track[start_idx:end_idx] += wave * env * vol

        # 1. Drums
        for bar in range(8):
            bar_start = bar * 4 * beat_len
            chord_idx = bar // 2
            
            # Kick (1 and 3)
            add_note(track_drums, bar_start, 0.2, 60, 'sine', 0.8, env_decay=15)
            add_note(track_drums, bar_start + 2*beat_len, 0.2, 60, 'sine', 0.8, env_decay=15)
            
            # Snare (2 and 4)
            add_note(track_drums, bar_start + 1*beat_len, 0.15, 200, 'sine', 0.3, env_decay=10)
            add_note(track_drums, bar_start + 1*beat_len, 0.15, 0, 'noise', 0.5, env_decay=15)
            add_note(track_drums, bar_start + 3*beat_len, 0.15, 200, 'sine', 0.3, env_decay=10)
            add_note(track_drums, bar_start + 3*beat_len, 0.15, 0, 'noise', 0.5, env_decay=15)
            
            # Hi-hat (8th notes)
            for i in range(8):
                add_note(track_drums, bar_start + i*beat_len/2, 0.05, 0, 'noise', 0.2, env_decay=40)

        # 2. Bass (Root note, syncopated)
        for bar in range(8):
            bar_start = bar * 4 * beat_len
            chord_idx = bar // 2
            root = bass_notes[chord_idx]
            
            add_note(track_bass, bar_start, beat_len*0.9, root, 'saw', 0.4, env_decay=4)
            add_note(track_bass, bar_start + 1.5*beat_len, beat_len*0.9, root, 'saw', 0.4, env_decay=4)
            add_note(track_bass, bar_start + 2*beat_len, beat_len*0.9, root*1.5, 'saw', 0.4, env_decay=4)
            add_note(track_bass, bar_start + 3.5*beat_len, beat_len*0.9, root, 'saw', 0.4, env_decay=4)

        # 3. Pad (Lush triangle chords)
        for bar in range(8):
            bar_start = bar * 4 * beat_len
            chord_idx = bar // 2
            chord = chords[chord_idx]
            
            for note in chord:
                # Slight detune for chorus effect
                add_note(track_pad, bar_start, 4*beat_len, note, 'triangle', 0.15, env_adsr=(0.2, 0.2, 0.8, 0.5))
                add_note(track_pad, bar_start, 4*beat_len, note*1.003, 'triangle', 0.1, env_adsr=(0.2, 0.2, 0.8, 0.5))

        # 4. Arpeggio (Square wave with vibrato)
        for bar in range(8):
            bar_start = bar * 4 * beat_len
            chord_idx = bar // 2
            chord = chords[chord_idx]
            
            # Play 16th notes
            for i in range(16):
                note = chord[i % 3] * 2 # Up one octave
                t_start = bar_start + i * (beat_len / 4)
                # Fake vibrato by rapidly shifting pitch? No, stick to simple square for performance.
                add_note(track_arp, t_start, beat_len/4 * 0.9, note, 'square', 0.15, env_decay=15)

        # Mix and master
        mix = track_drums + track_bass + track_pad + track_arp
        mix = np.clip(mix, -1, 1)
        self.music = self._make(mix)

    def play_music(self):
        if not self.enabled or self.muted or self.music is None: return
        if not self.music_playing:
            self.music_channel.play(self.music, loops=-1)
            self.music_playing = True

    def stop_music(self):
        if not self.enabled: return
        self.music_channel.stop()
        self.music_playing = False

    def play(self, name, vol=1.0):
        if not self.enabled or self.muted: return
        s = self.sounds.get(name)
        if s:
            s.set_volume(vol)
            s.play()

    def play_match(self, level):
        if not self.enabled or self.muted: return
        factor = max(0.6, 1.0 - level * 0.12)
        sound = self._pitch_shift(self.base_match, factor)
        if sound:
            sound.set_volume(0.9)
            sound.play()

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.stop_music()
        else:
            self.play_music()

# ───────── VFX & Particles ─────────
@dataclass
class Particle:
    x: float; y: float
    vx: float; vy: float
    life: float; max_life: float
    color: tuple
    size: float
    gravity: float = 320.0
    sparkle: bool = False
    sprite: pygame.Surface = None

@dataclass
class LineEffect:
    x1: float; y1: float; x2: float; y2: float
    color: tuple
    life: float = 0.35; max_life: float = 0.35
    width: int = 6

@dataclass
class ShockwaveEffect:
    x: float; y: float
    max_radius: float
    color: tuple
    life: float = 0.4; max_life: float = 0.4

class VFXPool:
    def __init__(self):
        self.parts = []
        self.lines = []
        self.waves = []
        self.layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)

    def burst(self, x, y, color, count=10, speed=(80, 220), sparkle=False, sprite=None):
        if len(self.parts) > 400: self.parts = self.parts[-200:]
        for _ in range(count):
            ang = random.random() * math.tau
            spd = random.uniform(*speed)
            life = random.uniform(0.32, 0.6)
            self.parts.append(Particle(
                x=x, y=y, vx=math.cos(ang) * spd, vy=math.sin(ang) * spd - 40,
                life=life, max_life=life, color=color,
                size=random.uniform(3.0, 6.0), sparkle=sparkle and random.random() < 0.3,
                sprite=sprite))

    def sparkle_burst(self, x, y, color, count=6, sprite=None):
        for _ in range(count):
            ang = random.random() * math.tau
            spd = random.uniform(30, 100)
            life = random.uniform(0.4, 0.7)
            self.parts.append(Particle(
                x=x, y=y, vx=math.cos(ang) * spd, vy=math.sin(ang) * spd - 20,
                life=life, max_life=life, color=(255, 255, 255),
                size=random.uniform(2.0, 4.0), sparkle=True, gravity=80.0, sprite=sprite))

    def beam(self, x1, y1, x2, y2, color, width=6):
        self.lines.append(LineEffect(x1, y1, x2, y2, color, width=width))

    def shockwave(self, x, y, radius, color):
        self.waves.append(ShockwaveEffect(x, y, radius, color))

    def update(self, dt):
        for p in self.parts:
            p.life -= dt
            p.vy += p.gravity * dt
            p.x += p.vx * dt; p.y += p.vy * dt
            p.vx *= 0.97
        self.parts = [p for p in self.parts if p.life > 0]
        
        for l in self.lines: l.life -= dt
        self.lines = [l for l in self.lines if l.life > 0]
        
        for w in self.waves: w.life -= dt
        self.waves = [w for w in self.waves if w.life > 0]

    def draw(self, surf):
        self.layer.fill((0, 0, 0, 0))
        for p in self.parts:
            a = clamp(p.life / p.max_life, 0, 1)
            if p.sprite:
                temp = p.sprite.copy()
                temp.fill((255, 255, 255, int(255 * a)), special_flags=pygame.BLEND_RGBA_MULT)
                surf.blit(temp, (p.x - temp.get_width()//2, p.y - temp.get_height()//2))
            else:
                r = max(1, int(p.size * (0.4 + 0.6 * a)))
                c = (int(p.color[0] * a), int(p.color[1] * a), int(p.color[2] * a))
                pygame.draw.circle(self.layer, c, (int(p.x), int(p.y)), r)
                if p.sparkle:
                    pygame.draw.circle(self.layer, c, (int(p.x), int(p.y)), r*2, 1)
        
        for l in self.lines:
            a = clamp(l.life / l.max_life, 0, 1)
            c = (int(l.color[0] * a), int(l.color[1] * a), int(l.color[2] * a))
            pygame.draw.line(self.layer, c, (l.x1, l.y1), (l.x2, l.y2), l.width)
            for w in range(1, 4):
                ca = (int(l.color[0] * a * 0.3), int(l.color[1] * a * 0.3), int(l.color[2] * a * 0.3))
                pygame.draw.line(self.layer, ca, (l.x1, l.y1), (l.x2, l.y2), l.width + w*2)
                
        for w in self.waves:
            a = clamp(w.life / w.max_life, 0, 1)
            t = 1.0 - a
            r = int(w.max_radius * t)
            c = (int(w.color[0] * a), int(w.color[1] * a), int(w.color[2] * a))
            if r > 0:
                pygame.draw.circle(self.layer, c, (int(w.x), int(w.y)), r, 4)
                pygame.draw.circle(self.layer, c, (int(w.x), int(w.y)), int(r*0.8), 2)
                
        surf.blit(self.layer, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

@dataclass
class ScorePopup:
    x: float; y: float
    text: str
    color: tuple = (255, 255, 255)
    life: float = 0.9; max_life: float = 0.9
    vy: float = -70; scale: float = 1.0
    alive: bool = True

    def update(self, dt):
        self.life -= dt
        self.y += self.vy * dt
        self.vy *= 0.95
        if self.life <= 0: self.alive = False

@dataclass
class Toast:
    text: str
    life: float = 2.0; max_life: float = 2.0
    alive: bool = True

    def update(self, dt):
        self.life -= dt
        if self.life <= 0: self.alive = False

# ───────── Blocker ─────────
class Blocker:
    def __init__(self, b_type):
        self.type = b_type
        self.hp = BLOCKER_HP[b_type]
        self.shake_t = 0
        
    def update(self, dt):
        if self.shake_t > 0:
            self.shake_t -= dt

# ───────── Gem ─────────
class Gem:
    __slots__ = ('gx', 'gy', 'vx', 'vy', 'type', 'special', 'state', 'anim_t',
                 'anim_dur', 'start_vx', 'start_vy', 'target_vx', 'target_vy',
                 'scale', 'alpha', 'trail')

    def __init__(self, gx, gy, type_, special=SPECIAL_NONE):
        self.gx = gx; self.gy = gy
        self.vx = GRID_X + gx * CELL + CELL / 2
        self.vy = GRID_Y + gy * CELL + CELL / 2
        self.type = type_
        self.special = special
        self.state = 'idle'
        self.anim_t = 0.0; self.anim_dur = 0.25
        self.start_vx = self.vx; self.start_vy = self.vy
        self.target_vx = self.vx; self.target_vy = self.vy
        self.scale = 1.0; self.alpha = 1.0
        self.trail = []

    def set_target(self, gx, gy, dur, state, start_vx=None, start_vy=None):
        self.gx = gx; self.gy = gy
        self.start_vx = self.vx if start_vx is None else start_vx
        self.start_vy = self.vy if start_vy is None else start_vy
        self.target_vx = GRID_X + gx * CELL + CELL / 2
        self.target_vy = GRID_Y + gy * CELL + CELL / 2
        self.anim_t = 0.0; self.anim_dur = dur; self.state = state

    def update(self, dt):
        if self.state == 'idle': return
        if self.state in ('swap', 'fall') and len(self.trail) < 4:
            self.trail.append((self.vx, self.vy, 0.0))
        self.trail = [(x, y, age + dt) for x, y, age in self.trail if age + dt < 0.15]

        self.anim_t += dt
        t = clamp(self.anim_t / self.anim_dur, 0, 1)
        if self.state == 'swap':
            te = ease_out_back(t)
            self.vx = lerp(self.start_vx, self.target_vx, te)
            self.vy = lerp(self.start_vy, self.target_vy, te)
            if t >= 1:
                self.state = 'idle'
                self.vx, self.vy = self.target_vx, self.target_vy
                self.trail.clear()
        elif self.state == 'fall':
            te = ease_out_cubic(t)
            self.vx = lerp(self.start_vx, self.target_vx, te)
            self.vy = lerp(self.start_vy, self.target_vy, te)
            if t > 0.85:
                bt = (t - 0.85) / 0.15
                self.scale = 1.0 + 0.15 * math.sin(bt * math.pi)
            else:
                self.scale = 1.0
            if t >= 1:
                self.state = 'idle'
                self.vx, self.vy = self.target_vx, self.target_vy
                self.scale = 1.0
        elif self.state == 'clear':
            if t < 0.25:
                self.scale = 1.0 + 0.6 * ease_out_cubic(t / 0.25)
                self.alpha = 1.0
            else:
                tt = (t - 0.25) / 0.75
                self.scale = 1.6 - 1.6 * ease_in_cubic(tt)
                self.alpha = 1.0 - tt
            if t >= 1:
                self.state = 'dead'
                self.scale = 0; self.alpha = 0

# ───────── Emoji Renderer ─────────
class GemRenderer:
    def __init__(self):
        emoji_fonts = "Segoe UI Emoji,Apple Color Emoji,Noto Color Emoji,DejaVu Sans,Arial"
        self.font = pygame.font.SysFont(emoji_fonts, 38)
        self.overlay_font = pygame.font.SysFont(emoji_fonts, 28)
        self.blocker_font = pygame.font.SysFont(emoji_fonts, 42)
        self.debris_font = pygame.font.SysFont(emoji_fonts, 20)
        self.ui_font = pygame.font.SysFont(emoji_fonts, 24)
        
        self.themes = {
            "Fruits":    ["🍎", "🍊", "🍋", "🍏", "🫐", "🍇", "🍉", "🍓"],
            "Animals":   ["🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼"],
            "Faces":     ["😀", "😎", "😭", "😡", "😱", "😴", "🤔", "🥳"],
            "Space":     ["⭐", "🚀", "🌙", "🌍", "☄️", "👽", "🛸", "🌟"],
            "Food":      ["🍕", "🍔", "🍟", "🌭", "🍩", "🍪", "🌮", "🍣"],
            "Nature":    ["🌸", "🌺", "🌻", "🌷", "🌹", "🍀", "🌳", "🍁"],
            "Sports":    ["⚽", "🏀", "🏈", "⚾", "🎾", "🏐", "🏓", "🏸"],
            "Halloween": ["🎃", "👻", "🧟", "🦇", "🕷️", "🧛", "🪦", "🧹"],
            "Undersea":  ["🐠", "🐟", "🐙", "🦈", "🦀", "🐬", "🐳", "🦑"],
            "Hearts":    ["❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍"],
            "Music":     ["🎸", "🎹", "🎺", "🎻", "🥁", "🎤", "🎷", "🪕"],
            "Weather":   ["☀️", "⛅", "🌧️", "⛈️", "❄️", "🌪️", "🌈", "🌫️"],
            "Vehicles":  ["🚗", "🚕", "🚙", "🚌", "🏎️", "🚓", "🚑", "🚒"],
            "Drinks":    ["☕", "🍵", "🧃", "🥤", "🍺", "🍷", "🍸", "🥂"],
            "Sweets":    ["🍬", "🍭", "🍫", "🍮", "🍯", "🧁", "🍰", "🥧"],
            "Tech":      ["💻", "🖥️", "🖨️", "⌨️", "🖱️", "📱", "🕹️", "💽"],
            "Party":     ["🎉", "🎊", "🎈", "🎁", "🎀", "🪅", "🪩", "🥂"],
            "Camping":   ["⛺", "🔥", "🏕️", "🧭", "🪓", "🥾", "🏔️", "🧊"],
            "Veggies":   ["🥕", "🥬", "🥒", "🌶️", "🧅", "🧄", "🍅", "🌽"],
            "Symbols":   ["🔮", "📿", "🧿", "💠", "🌐", "♻️", "✡️", "☮️"],
            "Clothing":  ["🎩", "🧢", "👕", "👖", "👔", "👗", "👟", "🧥"],
            "Money":     ["💵", "💶", "💷", "💴", "💰", "💳", "💎", "🪙"],
            "Tools":     ["🔧", "🔨", "⛏️", "⚙️", "🪛", "🔩", "🪚", "🧰"],
            "Zodiac":    ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏"],
            "Office":    ["📎", "🖊️", "📏", "📌", "✂️", "📁", "🖇️", "🗒️"],
            "Buildings": ["🏠", "🏢", "🏬", "🏥", "🏦", "⛪", "🏫", "🏨"],
            "Science":   ["🔬", "🔭", "🧬", "⚗️", "🧪", "📡", "📈", "🧮"],
            "Chess":     ["♚", "♛", "♜", "♝", "♞", "♟", "♔", "♕"],
            "Insects":   ["🐝", "🦋", "🐛", "🐜", "🪲", "🐞", "🦗", "🪰"],
            "Fantasy":   ["🔮", "🪄", "🧙", "🦄", "🐉", "🧞", "🧚", "🧝"],
        }
        
        self.theme_names = list(self.themes.keys())
        self.active_theme = "Fruits"
        
        self.theme_surfaces = {}
        for theme, emojis in self.themes.items():
            self.theme_surfaces[theme] = [
                self.font.render(e, True, (255,255,255)).convert_alpha() for e in emojis
            ]
            
        self.overlays = {
            SPECIAL_H_LINE: self.overlay_font.render("↔️", True, (255,255,255)).convert_alpha(),
            SPECIAL_V_LINE: self.overlay_font.render("↕️", True, (255,255,255)).convert_alpha(),
            SPECIAL_BOMB: self.overlay_font.render("💣", True, (255,255,255)).convert_alpha(),
            SPECIAL_COLOR: self.overlay_font.render("🌈", True, (255,255,255)).convert_alpha(),
        }
        
        self.blockers = {
            BLOCKER_ICE: self.blocker_font.render("🧊", True, (255,255,255)).convert_alpha(),
            BLOCKER_CRATE: self.blocker_font.render("📦", True, (255,255,255)).convert_alpha(),
            BLOCKER_STONE: self.blocker_font.render("🪨", True, (255,255,255)).convert_alpha(),
        }
        
        self.debris = {
            BLOCKER_ICE: self.debris_font.render("🧊", True, (255,255,255)).convert_alpha(),
            BLOCKER_CRATE: self.debris_font.render("🪵", True, (255,255,255)).convert_alpha(),
            BLOCKER_STONE: self.debris_font.render("🪨", True, (255,255,255)).convert_alpha(),
            'sparkle': self.debris_font.render("✨", True, (255,255,255)).convert_alpha(),
        }
        
        self.icons = {
            'hammer': self.ui_font.render("🔨", True, (255,255,255)).convert_alpha(),
            'pause': self.ui_font.render("⏸️", True, (255,255,255)).convert_alpha(),
            'left': self.ui_font.render("⬅️", True, (255,255,255)).convert_alpha(),
            'right': self.ui_font.render("➡️", True, (255,255,255)).convert_alpha(),
            'shuffle': self.ui_font.render("🔀", True, (255,255,255)).convert_alpha(),
        }

    @property
    def match_debris(self):
        return self.theme_surfaces[self.active_theme]

    def draw_gem(self, dest, gem, selected=False, time=0.0, hint_t=0.0, frenzy_t=0.0):
        if gem.state == 'dead': return
        
        bob_y = 0
        if gem.state == 'idle':
            bob_y = math.sin(time * 2 + gem.gx * 0.5 + gem.gy * 0.5) * 1.5
            
        for i, (tx, ty, age) in enumerate(gem.trail):
            a = (1.0 - age / 0.15) * 0.3
            if a > 0:
                ghost = self.match_debris[gem.type].copy()
                ghost.fill((255, 255, 255, int(255 * a)), special_flags=pygame.BLEND_RGBA_MULT)
                dest.blit(ghost, (tx - ghost.get_width() / 2, ty - ghost.get_height() / 2))
                
        scale = gem.scale
        if selected and gem.state == 'idle':
            scale *= 1.1 + 0.05 * math.sin(time * 6)
            
        s = self.match_debris[gem.type]
        if scale != 1.0 or gem.alpha != 1.0:
            sz = max(1, int(CELL * scale))
            scaled = pygame.transform.smoothscale(s, (sz, sz))
            if gem.alpha < 1.0:
                scaled.fill((255, 255, 255, int(255 * gem.alpha)), special_flags=pygame.BLEND_RGBA_MULT)
            dest.blit(scaled, (gem.vx - scaled.get_width() / 2, gem.vy + bob_y - scaled.get_height() / 2))
        else:
            dest.blit(s, (gem.vx - s.get_width() / 2, gem.vy + bob_y - s.get_height() / 2))
            
        if gem.special != SPECIAL_NONE:
            sp = self.overlays[gem.special]
            if scale != 1.0:
                sz = max(1, int(CELL * scale))
                sp_scaled = pygame.transform.smoothscale(sp, (sz, sz))
                dest.blit(sp_scaled, (gem.vx - sp_scaled.get_width() / 2, gem.vy + bob_y - sp_scaled.get_height() / 2))
            else:
                dest.blit(sp, (gem.vx - sp.get_width() / 2, gem.vy + bob_y - sp.get_height() / 2))
                
        if selected:
            pulse = 0.5 + 0.5 * math.sin(time * 8)
            ring_r = int(CELL * 0.52 + pulse * 3)
            ring_s = pygame.Surface((ring_r * 2 + 6, ring_r * 2 + 6), pygame.SRCALPHA)
            color = GEM_HIGHLIGHT[gem.type]
            for w in range(3, 0, -1):
                pygame.draw.circle(ring_s, (*color, int(180 * pulse + 50)), (ring_r + 3, ring_r + 3), ring_r, w)
            dest.blit(ring_s, (gem.vx - ring_r - 3, gem.vy + bob_y - ring_r - 3))
            
        if hint_t > 0:
            pulse = 0.5 + 0.5 * math.sin(time * 6)
            r = int(CELL * 0.48 + pulse * 4)
            ring_s = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(ring_s, (255, 255, 255, int(120 * hint_t * pulse)), (r + 4, r + 4), r, 3)
            dest.blit(ring_s, (gem.vx - r - 4, gem.vy + bob_y - r - 4))
            
        if frenzy_t > 0:
            pulse = 0.5 + 0.5 * math.sin(time * 10)
            r = int(CELL * 0.5 + pulse * 2)
            c = GEM_COLORS[int(time * 10) % GEM_TYPES]
            ring_s = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring_s, (*c, int(100 * pulse)), (r + 2, r + 2), r, 2)
            dest.blit(ring_s, (gem.vx - r - 2, gem.vy + bob_y - r - 2))

# ───────── Board ─────────
class Board:
    def __init__(self, audio, reduced_motion=False, mode="Timed"):
        self.audio = audio
        self.reduced_motion = reduced_motion
        self.mode = mode  # "Timed" or "Moves"
        self.gems = [[None] * GRID_N for _ in range(GRID_N)]
        self.blockers = [[None] * GRID_N for _ in range(GRID_N)]
        self.state = 'idle'
        self.selected = None
        self.drag_start = None
        self.drag_gem_start = None
        self.drag_moved = False
        self.swap_pair = None
        self.cascade_level = 0
        self.score = 0
        self.level = 1
        self.target_score = 1000
        self.time_left = GAME_TIME if mode == "Timed" else 0
        self.moves_left = MOVES_MODE if mode == "Moves" else 0
        self.combo_display_t = 0
        self.last_combo = 0
        self.max_combo = 0
        self.matches_made = 0
        self.shake_amp = 0; self.shake_t = 0; self.shake_dur = 0.28
        self.hit_stop_t = 0
        self.flash_t = 0; self.flash_color = (255, 255, 255)
        self.popups = []
        self.vfx = VFXPool()
        self.toasts = []
        self.hint_t = 0; self.hint_move = None
        self.idle_t = 0; self.tick_t = 0; self.level_up_t = 0
        self.hammers_left = 3
        self.shuffles_left = 3
        self.hammer_mode = False
        self.frenzy_t = 0
        self.frenzy_mult = 1
        self._init_grid()
        self._find_hint()

    def _init_grid(self):
        for y in range(GRID_N):
            for x in range(GRID_N):
                while True:
                    t = random.randint(0, GEM_TYPES - 1)
                    if x >= 2 and self.gems[y][x-1] and self.gems[y][x-2] and self.gems[y][x-1].type == t and self.gems[y][x-2].type == t: continue
                    if y >= 2 and self.gems[y-1][x] and self.gems[y-2][x] and self.gems[y-1][x].type == t and self.gems[y-2][x].type == t: continue
                    break
                self.gems[y][x] = Gem(x, y, t)
        for _ in range(4):
            cx, cy = random.randint(1, GRID_N-2), random.randint(1, GRID_N-2)
            if not self.blockers[cy][cx]:
                b_type = random.choice([BLOCKER_ICE, BLOCKER_CRATE, BLOCKER_STONE])
                self.blockers[cy][cx] = Blocker(b_type)

    def _find_matches(self):
        groups = []
        for y in range(GRID_N):
            x = 0
            while x < GRID_N:
                if self.blockers[y][x] is not None: x += 1; continue
                g = self.gems[y][x]
                if g is None or g.state in ('clear', 'dead'): x += 1; continue
                t = g.type; run_start = x
                while x < GRID_N and self.blockers[y][x] is None and self.gems[y][x] and self.gems[y][x].type == t and self.gems[y][x].state not in ('clear', 'dead'): x += 1
                run_len = x - run_start
                if run_len >= 3:
                    cells = set((run_start + i, y) for i in range(run_len))
                    groups.append({'cells': cells, 'type': t, 'len': run_len, 'dir': 'h'})
        for x in range(GRID_N):
            y = 0
            while y < GRID_N:
                if self.blockers[y][x] is not None: y += 1; continue
                g = self.gems[y][x]
                if g is None or g.state in ('clear', 'dead'): y += 1; continue
                t = g.type; run_start = y
                while y < GRID_N and self.blockers[y][x] is None and self.gems[y][x] and self.gems[y][x].type == t and self.gems[y][x].state not in ('clear', 'dead'): y += 1
                run_len = y - run_start
                if run_len >= 3:
                    cells = set((x, run_start + i) for i in range(run_len))
                    groups.append({'cells': cells, 'type': t, 'len': run_len, 'dir': 'v'})
        merged = []; used = set()
        for i, g1 in enumerate(groups):
            if i in used: continue
            combined_cells = set(g1['cells']); combined_len = g1['len']; combined_type = g1['type']; dirs = {g1['dir']}
            for j in range(i+1, len(groups)):
                if j in used: continue
                g2 = groups[j]
                if g2['type'] != combined_type: continue
                if combined_cells & g2['cells']:
                    combined_cells |= g2['cells']; combined_len += g2['len']; dirs.add(g2['dir']); used.add(j)
            used.add(i)
            merged.append({'cells': combined_cells, 'type': combined_type, 'len': len(combined_cells), 'is_l': len(dirs) > 1, 'dirs': dirs})
        return merged

    def _find_hint(self):
        self.hint_move = None
        for y in range(GRID_N):
            for x in range(GRID_N):
                if self.blockers[y][x] is not None: continue
                for dx, dy in [(1, 0), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if nx >= GRID_N or ny >= GRID_N or self.blockers[ny][nx] is not None: continue
                    self.gems[y][x], self.gems[ny][nx] = self.gems[ny][nx], self.gems[y][x]
                    matches = self._find_matches()
                    self.gems[y][x], self.gems[ny][nx] = self.gems[ny][nx], self.gems[y][x]
                    if matches:
                        self.hint_move = ((x, y), (nx, ny)); return

    def _has_moves(self):
        for y in range(GRID_N):
            for x in range(GRID_N):
                if self.blockers[y][x] is not None: continue
                for dx, dy in [(1, 0), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if nx >= GRID_N or ny >= GRID_N or self.blockers[ny][nx] is not None: continue
                    self.gems[y][x], self.gems[ny][nx] = self.gems[ny][nx], self.gems[y][x]
                    matches = self._find_matches()
                    self.gems[y][x], self.gems[ny][nx] = self.gems[ny][nx], self.gems[y][x]
                    if matches: return True
        return False

    def _shuffle(self):
        types = []; specials = []
        for y in range(GRID_N):
            for x in range(GRID_N):
                if self.gems[y][x]:
                    types.append(self.gems[y][x].type); specials.append(self.gems[y][x].special)
        for _ in range(100):
            random.shuffle(types); random.shuffle(specials); idx = 0
            for y in range(GRID_N):
                for x in range(GRID_N):
                    if self.blockers[y][x] is None:
                        self.gems[y][x] = Gem(x, y, types[idx], specials[idx]); idx += 1
            if self._has_moves() and not self._find_matches(): break
        for y in range(GRID_N):
            for x in range(GRID_N):
                g = self.gems[y][x]
                if g:
                    g.vy = GRID_Y - (GRID_N - y) * CELL - random.uniform(20, 80)
                    g.set_target(x, y, 0.5 + y * 0.04, 'fall', start_vy=g.vy)
        self.audio.play('shuffle')
        self.toasts.append(Toast("Shuffled!"))

    def use_hammer(self):
        if self.hammers_left > 0 and self.state == 'idle':
            self.hammer_mode = not self.hammer_mode
            self.selected = None
            self.audio.play('click')

    def use_shuffle(self):
        if self.shuffles_left > 0 and self.state == 'idle':
            self.shuffles_left -= 1
            self._shuffle()
            self.audio.play('click')

    def try_swap(self, x1, y1, x2, y2):
        if self.state != 'idle': return False
        if abs(x1 - x2) + abs(y1 - y2) != 1: return False
        if self.blockers[y1][x1] is not None or self.blockers[y2][x2] is not None: return False
        g1 = self.gems[y1][x1]; g2 = self.gems[y2][x2]
        if not g1 or not g2: return False

        if g1.special != SPECIAL_NONE and g2.special != SPECIAL_NONE:
            self._do_swap(x1, y1, x2, y2)
            self.state = 'swapping'
            self.swap_pair = (x1, y1, x2, y2, 'mixed', None)
            self.audio.play('swap'); self.idle_t = 0
            return True

        if g1.special == SPECIAL_COLOR or g2.special == SPECIAL_COLOR:
            bomb, other = (g1, g2) if g1.special == SPECIAL_COLOR else (g2, g1)
            target_type = other.type
            self._do_swap(x1, y1, x2, y2)
            self.state = 'swapping'
            self.swap_pair = (x1, y1, x2, y2, 'color', target_type)
            self.audio.play('swap'); self.idle_t = 0
            return True

        self._do_swap(x1, y1, x2, y2)
        self.state = 'swapping'
        self.swap_pair = (x1, y1, x2, y2, False, None)
        self.audio.play('swap'); self.idle_t = 0
        return True

    def _do_swap(self, x1, y1, x2, y2):
        g1 = self.gems[y1][x1]; g2 = self.gems[y2][x2]
        g1.set_target(x2, y2, 0.22, 'swap'); g2.set_target(x1, y1, 0.22, 'swap')
        self.gems[y1][x1] = g2; self.gems[y2][x2] = g1

    def _do_swap_back(self, x1, y1, x2, y2):
        g1 = self.gems[y1][x1]; g2 = self.gems[y2][x2]
        g1.set_target(x2, y2, 0.18, 'swap'); g2.set_target(x1, y1, 0.18, 'swap')
        self.gems[y1][x1] = g2; self.gems[y2][x2] = g1

    def _process_mixed_specials(self, x1, y1, x2, y2):
        g1 = self.gems[y2][x2] 
        g2 = self.gems[y1][x1] 
        s1, s2 = g1.special, g2.special
        cells = set()
        
        px1, py1 = GRID_X + x1*CELL + CELL/2, GRID_Y + y1*CELL + CELL/2
        px2, py2 = GRID_X + x2*CELL + CELL/2, GRID_Y + y2*CELL + CELL/2
        self.vfx.beam(px1, py1, px2, py2, (255, 255, 255), width=10)
        
        if s1 == SPECIAL_COLOR and s2 == SPECIAL_COLOR:
            for y in range(GRID_N):
                for x in range(GRID_N):
                    if self.gems[y][x] and self.gems[y][x].state == 'idle':
                        cells.add((x, y))
            self.toasts.append(Toast("BOARD CLEAR!"))
            self.vfx.shockwave(SCREEN_W/2, GRID_Y+GRID_PX/2, CELL*10, (255, 255, 255))
        elif {s1, s2} == {SPECIAL_H_LINE, SPECIAL_V_LINE}:
            cells.update((i, y1) for i in range(GRID_N))
            cells.update((i, y2) for i in range(GRID_N))
            cells.update((x1, i) for i in range(GRID_N))
            cells.update((x2, i) for i in range(GRID_N))
            self.toasts.append(Toast("Cross Clear!"))
        elif {s1, s2} == {SPECIAL_BOMB, SPECIAL_H_LINE} or {s1, s2} == {SPECIAL_BOMB, SPECIAL_V_LINE}:
            for y in range(max(0, y1-1), min(GRID_N, y1+2)):
                cells.update((i, y) for i in range(GRID_N))
            for x in range(max(0, x1-1), min(GRID_N, x1+2)):
                cells.update((x, i) for i in range(GRID_N))
            self.toasts.append(Toast("Mega Blast!"))
        elif s1 == SPECIAL_BOMB and s2 == SPECIAL_BOMB:
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    nx, ny = x1+dx, y1+dy
                    if 0<=nx<GRID_N and 0<=ny<GRID_N: cells.add((nx, ny))
            self.vfx.shockwave(px1, py1, CELL*4, (255, 200, 100))
            self.toasts.append(Toast("5x5 Annihilator!"))
        elif SPECIAL_COLOR in (s1, s2):
            other_s = s1 if s2 == SPECIAL_COLOR else s2
            other_g = g1 if s2 == SPECIAL_COLOR else g2
            t_type = other_g.type
            for y in range(GRID_N):
                for x in range(GRID_N):
                    gg = self.gems[y][x]
                    if gg and gg.type == t_type and gg.state == 'idle':
                        gg.special = other_s
                        cells.add((x, y))
            self.toasts.append(Toast("Color Special!"))
            
        cells.add((x1, y1)); cells.add((x2, y2))
        
        extra = set()
        for (cx, cy) in cells:
            g = self.gems[cy][cx]
            if g and g.special != SPECIAL_NONE and g.state != 'clear':
                extra |= self._detonate_special(cx, cy, g.special, g.type)
        cells |= extra
        
        for (cx, cy) in list(cells):
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = cx+dx, cy+dy
                if 0<=nx<GRID_N and 0<=ny<GRID_N and self.blockers[ny][nx] is not None:
                    self._damage_blocker(nx, ny)
                    
        for (cx, cy) in cells:
            g = self.gems[cy][cx]
            if g and g.state != 'clear':
                g.state = 'clear'; g.anim_t = 0; g.anim_dur = 0.4
                px = GRID_X + cx * CELL + CELL/2; py = GRID_Y + cy * CELL + CELL/2
                sprite = self.renderer.match_debris[g.type]
                self.vfx.burst(px, py, GEM_COLORS[g.type], count=6, sparkle=True, sprite=sprite)
                self.vfx.burst(px, py, GEM_COLORS[g.type], count=8)
                
        self.cascade_level = 0
        self.score += len(cells) * 100 * self.frenzy_mult
        self.state = 'clearing'
        self.audio.play('special')
        if not self.reduced_motion:
            self.shake_amp = 10; self.shake_t = 0; self.flash_t = 0.3
            self.hit_stop_t = 0.1

    def _check_frenzy(self):
        if self.cascade_level >= 3 and self.frenzy_t <= 0:
            self.frenzy_t = 5.0
            self.toasts.append(Toast("FRENZY! x2 SCORE"))
            self.audio.play('frenzy')
            self.flash_t = 0.4
            self.flash_color = (255, 100, 255)
            
        if self.frenzy_t > 0:
            self.frenzy_mult = 2
        else:
            self.frenzy_mult = 1

    def _clear_matches(self, matches):
        self._check_frenzy()
        
        cells_to_clear = set()
        special_creations = []
        for m in matches:
            cells = m['cells']; mlen = m['len']; is_l = m['is_l']; gtype = m['type']
            special = SPECIAL_NONE
            if is_l and mlen >= 5: special = SPECIAL_BOMB
            elif mlen >= 5: special = SPECIAL_COLOR
            elif mlen == 4:
                if 'h' in m['dirs'] and 'v' not in m['dirs']: special = SPECIAL_H_LINE
                elif 'v' in m['dirs'] and 'h' not in m['dirs']: special = SPECIAL_V_LINE
                else: special = SPECIAL_H_LINE
            if special != SPECIAL_NONE:
                cx = sum(c[0] for c in cells) // len(cells); cy = sum(c[1] for c in cells) // len(cells)
                if (cx, cy) not in cells: cx, cy = random.choice(list(cells))
                special_creations.append((cx, cy, gtype, special))
            cells_to_clear |= cells

        creation_cells = set((c[0], c[1]) for c in special_creations)
        pure_clear = cells_to_clear - creation_cells

        extra_clear = set()
        for (x, y) in list(pure_clear):
            g = self.gems[y][x]
            if g and g.special != SPECIAL_NONE:
                extra_clear |= self._detonate_special(x, y, g.special, g.type)
        pure_clear |= extra_clear

        for (x, y) in pure_clear:
            g = self.gems[y][x]
            if g and g.state != 'clear':
                g.set_target(x, y, 0.4, 'clear'); g.state = 'clear'; g.anim_t = 0; g.anim_dur = 0.4
                px = GRID_X + x * CELL + CELL/2; py = GRID_Y + y * CELL + CELL/2
                sprite = self.renderer.match_debris[g.type]
                self.vfx.burst(px, py, GEM_COLORS[g.type], count=4, sparkle=True, sprite=sprite)
                self.vfx.burst(px, py, GEM_COLORS[g.type], count=8)
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nx, ny = x+dx, y+dy
                    if 0<=nx<GRID_N and 0<=ny<GRID_N and self.blockers[ny][nx] is not None:
                        self._damage_blocker(nx, ny)

        for (cx, cy, gtype, special) in special_creations:
            old = self.gems[cy][cx]
            if old: old.state = 'dead'; old.alpha = 0
            new_g = Gem(cx, cy, gtype, special)
            new_g.scale = 0.1; new_g.state = 'fall'; new_g.anim_t = 0; new_g.anim_dur = 0.3
            new_g.start_vx = new_g.vx; new_g.start_vy = new_g.vy
            new_g.target_vx = new_g.vx; new_g.target_vy = new_g.vy
            self.gems[cy][cx] = new_g
            px = GRID_X + cx * CELL + CELL/2; py = GRID_Y + cy * CELL + CELL/2
            self.vfx.sparkle_burst(px, py, GEM_HIGHLIGHT[gtype], count=10, sprite=self.renderer.debris['sparkle'])
            self.audio.play('special')

        base_per_gem = 30; combo_mult = 1 + self.cascade_level * 0.5
        match_count = len(pure_clear)
        total = int(match_count * base_per_gem * combo_mult * self.frenzy_mult)
        total += len(special_creations) * 150 * self.frenzy_mult
        for m in matches:
            if m['len'] >= 5: total += 300 * self.frenzy_mult
            elif m['len'] == 4: total += 100 * self.frenzy_mult

        self.score += total; self.matches_made += len(matches)
        self.last_combo = self.cascade_level + 1
        self.max_combo = max(self.max_combo, self.last_combo)

        if matches:
            avg_x = sum(GRID_X + c[0] * CELL + CELL/2 for m in matches for c in m['cells']) / sum(len(m['cells']) for m in matches)
            avg_y = sum(GRID_Y + c[1] * CELL + CELL/2 for m in matches for c in m['cells']) / sum(len(m['cells']) for m in matches)
            self.popups.append(ScorePopup(x=avg_x, y=avg_y, text=f"+{total}", color=ACCENT if self.last_combo > 1 else TEXT, scale=1.0 + self.cascade_level * 0.15))
            if self.last_combo > 1:
                self.popups.append(ScorePopup(x=avg_x, y=avg_y - 30, text=f"COMBO x{self.last_combo}", color=DANGER, scale=1.2, life=1.0, max_life=1.0, vy=-50))

        if not self.reduced_motion:
            if self.cascade_level >= 1 or match_count >= 5:
                self.shake_amp = min(10, 3 + match_count * 0.5 + self.cascade_level * 2); self.shake_t = 0; self.shake_dur = 0.28
            if match_count >= 5 or self.cascade_level >= 2 or special_creations:
                self.flash_t = 0.2; self.flash_color = (255, 255, 255)
            if match_count >= 4 or self.cascade_level >= 1 or special_creations:
                self.hit_stop_t = 0.04 + min(0.08, self.cascade_level * 0.02)

        self.audio.play_match(self.cascade_level)

    def _damage_blocker(self, x, y):
        b = self.blockers[y][x]
        if b is not None:
            b.hp -= 1
            b.shake_t = 0.2
            px = GRID_X + x * CELL + CELL/2; py = GRID_Y + y * CELL + CELL/2
            sprite = self.renderer.debris[b.type]
            if b.type == BLOCKER_ICE:
                self.vfx.burst(px, py, ICE_COL, count=6, sprite=sprite)
                self.audio.play('ice')
            elif b.type == BLOCKER_CRATE:
                self.vfx.burst(px, py, WOOD, count=6, sprite=sprite)
                self.audio.play('crate')
            elif b.type == BLOCKER_STONE:
                self.vfx.burst(px, py, STONE_COL, count=8, sprite=sprite)
                self.audio.play('stone')
            
            if b.hp <= 0:
                self.blockers[y][x] = None
                if b.type == BLOCKER_ICE:
                    self.vfx.burst(px, py, (200, 240, 255), count=12, sparkle=True, sprite=sprite)
                elif b.type == BLOCKER_CRATE:
                    self.vfx.burst(px, py, WOOD_DARK, count=12, speed=(80, 200), sprite=sprite)
                elif b.type == BLOCKER_STONE:
                    self.vfx.burst(px, py, (80, 80, 90), count=14, speed=(100, 250), sprite=sprite)
                self.score += 100 * self.frenzy_mult
                self.popups.append(ScorePopup(x=px, y=py, text="+100", color=ACCENT, scale=0.8))

    def _detonate_special(self, x, y, special, gem_type):
        cells = set()
        if special == SPECIAL_H_LINE:
            for i in range(GRID_N): cells.add((i, y))
            px1, py1 = GRID_X + CELL/2, GRID_Y + y*CELL + CELL/2
            px2, py2 = GRID_X + GRID_PX - CELL/2, GRID_Y + y*CELL + CELL/2
            self.vfx.beam(px1, py1, px2, py2, GEM_HIGHLIGHT[gem_type], width=8)
        elif special == SPECIAL_V_LINE:
            for i in range(GRID_N): cells.add((x, i))
            px1, py1 = GRID_X + x*CELL + CELL/2, GRID_Y + CELL/2
            px2, py2 = GRID_X + x*CELL + CELL/2, GRID_Y + GRID_PX - CELL/2
            self.vfx.beam(px1, py1, px2, py2, GEM_HIGHLIGHT[gem_type], width=8)
        elif special == SPECIAL_BOMB:
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < GRID_N and 0 <= ny < GRID_N: cells.add((nx, ny))
            px, py = GRID_X + x*CELL + CELL/2, GRID_Y + y*CELL + CELL/2
            self.vfx.shockwave(px, py, CELL*3, GEM_COLORS[gem_type])
        elif special == SPECIAL_COLOR:
            for yy in range(GRID_N):
                for xx in range(GRID_N):
                    g = self.gems[yy][xx]
                    if g and g.type == gem_type: cells.add((xx, yy))
        extra = set()
        for (cx, cy) in cells:
            g = self.gems[cy][cx]
            if g and g.special != SPECIAL_NONE and g.state != 'clear':
                extra |= self._detonate_special(cx, cy, g.special, g.type)
        return cells | extra

    def _apply_gravity(self):
        moved = False
        for x in range(GRID_N):
            write_y = GRID_N - 1
            for y in range(GRID_N - 1, -1, -1):
                if self.blockers[y][x] is not None:
                    write_y = y - 1
                    continue
                g = self.gems[y][x]
                if g and g.state != 'dead' and g.state != 'clear':
                    if write_y != y:
                        fall_dist = write_y - y
                        g.set_target(x, write_y, 0.25 + fall_dist * 0.04, 'fall')
                        self.gems[write_y][x] = g; self.gems[y][x] = None; moved = True
                    write_y -= 1
                elif g and g.state == 'dead':
                    self.gems[y][x] = None
            spawn_y = -1
            for y in range(write_y, -1, -1):
                if self.blockers[y][x] is not None: break
                t = random.randint(0, GEM_TYPES - 1)
                g = Gem(x, y, t)
                start_vy = GRID_Y + spawn_y * CELL + CELL / 2
                g.vy = start_vy
                g.set_target(x, y, 0.35 + (write_y - y) * 0.04, 'fall', start_vy=start_vy)
                self.gems[y][x] = g; spawn_y -= 1; moved = True
        return moved

    def _all_idle(self):
        for y in range(GRID_N):
            for x in range(GRID_N):
                g = self.gems[y][x]
                if g and g.state != 'idle': return False
        return True

    def update(self, dt, game_active=True):
        if self.hit_stop_t > 0:
            self.hit_stop_t -= dt
            if self.hit_stop_t > 0: return

        for y in range(GRID_N):
            for x in range(GRID_N):
                g = self.gems[y][x]
                if g: g.update(dt)
                b = self.blockers[y][x]
                if b: b.update(dt)

        self.vfx.update(dt)
        for p in self.popups: p.update(dt)
        self.popups = [p for p in self.popups if p.alive]
        for t in self.toasts: t.update(dt)
        self.toasts = [t for t in self.toasts if t.alive]

        if self.shake_t < self.shake_dur: self.shake_t += dt
        if self.flash_t > 0: self.flash_t -= dt
        if self.combo_display_t > 0: self.combo_display_t -= dt
        if self.level_up_t > 0: self.level_up_t -= dt
        if self.frenzy_t > 0:
            self.frenzy_t -= dt
            if self.frenzy_t <= 0: self.frenzy_t = 0

        if game_active and self.state == 'idle':
            if self.mode == "Timed":
                self.time_left -= dt
                if self.time_left <= 10 and self.time_left > 0:
                    self.tick_t += dt
                    if self.tick_t >= 1.0: self.tick_t = 0; self.audio.play('tick')
                if self.time_left <= 0: self.time_left = 0

        if game_active and self.state == 'idle':
            self.idle_t += dt
            if self.idle_t > HINT_DELAY and self.hint_move:
                self.hint_t = min(1.0, self.hint_t + dt * 2)
            else:
                self.hint_t = max(0, self.hint_t - dt * 2)
        else:
            self.idle_t = 0; self.hint_t = max(0, self.hint_t - dt * 2)

        if self.state == 'swapping':
            if self._all_idle():
                x1, y1, x2, y2, special_swap, cb_target = self.swap_pair
                if special_swap == 'mixed':
                    self._process_mixed_specials(x1, y1, x2, y2)
                elif special_swap == 'color':
                    g1 = self.gems[y1][x1]; g2 = self.gems[y2][x2]
                    bomb = g1 if g1.special == SPECIAL_COLOR else g2
                    cells = self._detonate_special(bomb.gx, bomb.gy, SPECIAL_COLOR, cb_target)
                    for (cx, cy) in cells:
                        gg = self.gems[cy][cx]
                        if gg and gg.state != 'clear':
                            gg.state = 'clear'; gg.anim_t = 0; gg.anim_dur = 0.4
                            px = GRID_X + cx * CELL + CELL/2; py = GRID_Y + cy * CELL + CELL/2
                            self.vfx.burst(px, py, GEM_COLORS[gg.type], count=8)
                            self.vfx.burst(px, py, GEM_COLORS[gg.type], count=4, sparkle=True, sprite=self.renderer.match_debris[gg.type])
                            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                                nx, ny = cx+dx, cy+dy
                                if 0<=nx<GRID_N and 0<=ny<GRID_N and self.blockers[ny][nx] is not None:
                                    self._damage_blocker(nx, ny)
                    self.cascade_level = 0; self.state = 'clearing'; self.audio.play('special')
                    if not self.reduced_motion:
                        self.shake_amp = 8; self.shake_t = 0; self.flash_t = 0.2; self.hit_stop_t = 0.08
                else:
                    matches = self._find_matches()
                    if matches:
                        self.cascade_level = 0; self._clear_matches(matches); self.state = 'clearing'
                        if self.mode == "Moves": self.moves_left -= 1
                    else:
                        self._do_swap_back(x1, y1, x2, y2); self.audio.play('fail'); self.state = 'swap_back'

        elif self.state == 'swap_back':
            if self._all_idle():
                self.state = 'idle'; self._find_hint()

        elif self.state == 'clearing':
            any_clearing = any(self.gems[y][x] and self.gems[y][x].state == 'clear' for y in range(GRID_N) for x in range(GRID_N))
            if not any_clearing:
                for y in range(GRID_N):
                    for x in range(GRID_N):
                        if self.gems[y][x] and self.gems[y][x].state == 'dead': self.gems[y][x] = None
                self._apply_gravity(); self.state = 'falling'

        elif self.state == 'falling':
            if self._all_idle():
                matches = self._find_matches()
                if matches:
                    self.cascade_level += 1; self.combo_display_t = 1.5
                    self._clear_matches(matches); self.state = 'clearing'
                else:
                    self.cascade_level = 0; self.state = 'idle'
                    if self.score >= self.target_score: self._level_up()
                    if not self._has_moves(): self._shuffle()
                    self._find_hint()

    def _level_up(self):
        self.level += 1
        self.target_score = int(self.target_score * 1.6)
        if self.mode == "Timed":
            self.time_left = min(self.time_left + 15, 99)
        else:
            self.moves_left += 5
        self.level_up_t = 2.0; self.audio.play('levelup')
        self.toasts.append(Toast(f"Level {self.level}!"))
        empty = [(x, y) for y in range(GRID_N) for x in range(GRID_N) if self.blockers[y][x] is None]
        if empty:
            cx, cy = random.choice(empty)
            b_type = random.choice([BLOCKER_ICE, BLOCKER_CRATE, BLOCKER_STONE])
            self.blockers[cy][cx] = Blocker(b_type)
        if not self.reduced_motion:
            self.flash_t = 0.3; self.flash_color = GOOD
            self.vfx.sparkle_burst(SCREEN_W / 2, SCREEN_H / 2, (255, 255, 255), count=30, sprite=self.renderer.debris['sparkle'])

    def handle_click(self, mx, my):
        if self.state != 'idle': return
        gx = (mx - GRID_X) // CELL; gy = (my - GRID_Y) // CELL
        if not (0 <= gx < GRID_N and 0 <= gy < GRID_N):
            self.selected = None; return
        
        if self.hammer_mode:
            if self.blockers[gy][gx] is not None:
                for _ in range(BLOCKER_HP[self.blockers[gy][gx].type]):
                    self._damage_blocker(gx, gy)
            elif self.gems[gy][gx]:
                g = self.gems[gy][gx]
                if g.special != SPECIAL_NONE:
                    cells = self._detonate_special(gx, gy, g.special, g.type)
                    for (cx, cy) in cells:
                        gg = self.gems[cy][cx]
                        if gg and gg.state != 'clear':
                            gg.state = 'clear'; gg.anim_t = 0; gg.anim_dur = 0.4
                            px = GRID_X + cx * CELL + CELL/2; py = GRID_Y + cy * CELL + CELL/2
                            self.vfx.burst(px, py, GEM_COLORS[gg.type], count=8)
                            self.vfx.burst(px, py, GEM_COLORS[gg.type], count=4, sparkle=True, sprite=self.renderer.match_debris[gg.type])
                    self.state = 'clearing'
                else:
                    g.state = 'clear'; g.anim_t = 0; g.anim_dur = 0.3
                    px = GRID_X + gx * CELL + CELL/2; py = GRID_Y + gy * CELL + CELL/2
                    self.vfx.burst(px, py, GEM_COLORS[g.type], count=8)
                    self.vfx.burst(px, py, GEM_COLORS[g.type], count=4, sparkle=True, sprite=self.renderer.match_debris[g.type])
                    self.state = 'falling'
            self.hammers_left -= 1; self.hammer_mode = False
            self.audio.play('hammer')
            if not self.reduced_motion: self.shake_amp = 4; self.shake_t = 0
            return

        if self.blockers[gy][gx] is not None: return
        
        if self.selected:
            sx, sy = self.selected
            if (gx, gy) == (sx, sy): self.selected = None; return
            if abs(gx - sx) + abs(gy - sy) == 1:
                self.try_swap(sx, sy, gx, gy); self.selected = None
            else:
                self.selected = (gx, gy)
        else:
            self.selected = (gx, gy)
        self.idle_t = 0

    def handle_drag_start(self, mx, my):
        if self.state != 'idle' or self.hammer_mode: return
        gx = (mx - GRID_X) // CELL; gy = (my - GRID_Y) // CELL
        if 0 <= gx < GRID_N and 0 <= gy < GRID_N and self.blockers[gy][gx] is None:
            self.drag_start = (mx, my); self.drag_gem_start = (gx, gy); self.drag_moved = False; self.idle_t = 0

    def handle_drag_move(self, mx, my):
        if not self.drag_start or self.state != 'idle': return
        dx = mx - self.drag_start[0]; dy = my - self.drag_start[1]
        if abs(dx) > 17 or abs(dy) > 17:
            gx, gy = self.drag_gem_start
            if abs(dx) > abs(dy): nx, ny = gx + (1 if dx > 0 else -1), gy
            else: nx, ny = gx, gy + (1 if dy > 0 else -1)
            if 0 <= nx < GRID_N and 0 <= ny < GRID_N and self.blockers[ny][nx] is None:
                self.try_swap(gx, gy, nx, ny)
            self.drag_start = None; self.drag_gem_start = None; self.selected = None; self.drag_moved = True

    def handle_drag_end(self, mx, my):
        if self.drag_start and not self.drag_moved: self.handle_click(mx, my)
        self.drag_start = None; self.drag_gem_start = None

    def draw(self, surf, time, font_sm, font_md, font_lg):
        sx, sy = 0, 0
        if self.shake_t < self.shake_dur and not self.reduced_motion:
            amp = self.shake_amp * math.exp(-self.shake_t / (self.shake_dur * 0.4))
            amp = min(amp, 10); sx = random.uniform(-amp, amp); sy = random.uniform(-amp, amp)

        grid_rect = pygame.Rect(GRID_X - 6 + sx, GRID_Y - 6 + sy, GRID_PX + 12, GRID_PX + 12)
        pygame.draw.rect(surf, PANEL, grid_rect, border_radius=14)
        pygame.draw.rect(surf, PANEL_HI, grid_rect, width=2, border_radius=14)

        for y in range(GRID_N):
            for x in range(GRID_N):
                r = pygame.Rect(GRID_X + x * CELL + 2 + sx, GRID_Y + y * CELL + 2 + sy, CELL - 4, CELL - 4)
                pygame.draw.rect(surf, GRID_CELL, r, border_radius=8)

        if self.hint_move and self.hint_t > 0:
            (hx1, hy1), (hx2, hy2) = self.hint_move
            for hx, hy in [(hx1, hy1), (hx2, hy2)]:
                r = pygame.Rect(GRID_X + hx * CELL + sx, GRID_Y + hy * CELL + sy, CELL, CELL)
                glow = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
                pulse = 0.5 + 0.5 * math.sin(time * 6)
                a = int(60 * self.hint_t * pulse)
                pygame.draw.rect(glow, (255, 255, 255, a), (0, 0, CELL, CELL), border_radius=8)
                surf.blit(glow, r.topleft)

        renderer = self.renderer
        for y in range(GRID_N):
            for x in range(GRID_N):
                b = self.blockers[y][x]
                if b is not None:
                    bx, by = GRID_X + x * CELL + sx, GRID_Y + y * CELL + sy
                    if b.shake_t > 0:
                        bx += random.uniform(-3, 3); by += random.uniform(-3, 3)
                    self._draw_blocker(surf, b, bx, by, renderer)
                    
        for y in range(GRID_N):
            for x in range(GRID_N):
                g = self.gems[y][x]
                if g:
                    selected = self.selected == (x, y)
                    hint_t = 0
                    if self.hint_move and self.hint_t > 0:
                        if (x, y) in [self.hint_move[0], self.hint_move[1]]: hint_t = self.hint_t
                    renderer.draw_gem(surf, g, selected, time, hint_t, self.frenzy_t)

        self.vfx.draw(surf)

        for p in self.popups:
            a = clamp(p.life / p.max_life, 0, 1)
            scale = p.scale * (1.0 + (1 - a) * 0.3)
            txt = font_lg.render(p.text, True, p.color) if p.scale > 1.1 else font_md.render(p.text, True, p.color)
            if scale != 1.0:
                txt = pygame.transform.smoothscale(txt, (int(txt.get_width() * scale), int(txt.get_height() * scale)))
            txt.set_alpha(int(255 * a))
            surf.blit(txt, (p.x - txt.get_width() / 2, p.y - txt.get_height() / 2))

        if self.flash_t > 0:
            a = int(120 * (self.flash_t / 0.3))
            flash = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            flash.fill((*self.flash_color, a))
            surf.blit(flash, (0, 0))

        for i, t in enumerate(self.toasts):
            a = clamp(t.life / t.max_life, 0, 1)
            fade = min(1.0, a * 2) if a > 0.5 else a * 2
            txt = font_lg.render(t.text, True, ACCENT)
            txt.set_alpha(int(255 * fade))
            bg = pygame.Surface((txt.get_width() + 40, txt.get_height() + 16), pygame.SRCALPHA)
            bg.fill((30, 26, 60, int(220 * fade)))
            pygame.draw.rect(bg, (*ACCENT, int(180 * fade)), bg.get_rect(), 2, border_radius=10)
            x = SCREEN_W / 2 - bg.get_width() / 2; y = GRID_Y - 70 - i * 50
            surf.blit(bg, (x, y)); surf.blit(txt, (x + 20, y + 8))

        if self.level_up_t > 0:
            a = clamp(self.level_up_t / 2.0, 0, 1)
            fade = 1.0 if a > 0.3 else a / 0.3
            txt = font_lg.render(f"LEVEL {self.level}!", True, GOOD)
            txt.set_alpha(int(255 * fade))
            scale = 1.0 + (1 - a) * 0.5
            txt = pygame.transform.smoothscale(txt, (int(txt.get_width() * scale), int(txt.get_height() * scale)))
            surf.blit(txt, (SCREEN_W / 2 - txt.get_width() / 2, SCREEN_H / 2 - txt.get_height() / 2))
            
        if self.frenzy_t > 0:
            pulse = 0.5 + 0.5 * math.sin(time * 10)
            a = int(150 * (self.frenzy_t / 5.0) * pulse)
            border_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            pygame.draw.rect(border_surf, (255, 100, 255, a), (0, 0, SCREEN_W, SCREEN_H), 10)
            surf.blit(border_surf, (0, 0))
            
        if self.hammer_mode:
            mx, my = pygame.mouse.get_pos()
            pulse = 0.5 + 0.5 * math.sin(time * 8)
            pygame.draw.circle(surf, DANGER, (mx, my), int(20 + pulse * 4), 3)
            pygame.draw.line(surf, DANGER, (mx-15, my), (mx+15, my), 2)
            pygame.draw.line(surf, DANGER, (mx, my-15), (mx, my+15), 2)

    def _draw_blocker(self, surf, b, x, y, renderer):
        img = renderer.blockers[b.type]
        surf.blit(img, (x + (CELL - img.get_width())//2, y + (CELL - img.get_height())//2))
        if b.hp < BLOCKER_HP[b.type]:
            cx, cy = x + CELL//2, y + CELL//2
            pygame.draw.line(surf, (255, 255, 255, 200), (cx-10, cy-5), (cx+5, cy+10), 2)
            pygame.draw.line(surf, (255, 255, 255, 200), (cx+5, cy-10), (cx-5, cy+5), 2)


# ───────── Main game ─────────
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED, vsync=1)
        pygame.display.set_caption("Match-3 Synthwave")
        self.clock = pygame.time.Clock()
        self.audio = Audio()
        self.renderer = GemRenderer()
        self.state = GameState.MENU
        self.reduced_motion = False
        self.show_debug = False
        self.time_scale = 1.0
        self.high_score = self._load_highscore()
        self.font_xs = pygame.font.SysFont("Arial", 14, bold=True)
        self.font_sm = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_md = pygame.font.SysFont("Arial", 24, bold=True)
        self.font_lg = pygame.font.SysFont("Arial", 36, bold=True)
        self.font_xl = pygame.font.SysFont("Arial", 52, bold=True)
        self.font_huge = pygame.font.SysFont("Arial", 72, bold=True)
        self.bg_surface = self._make_bg()
        self.menu_gems = self._make_menu_gems()
        self.board = None
        self.menu_t = 0
        self.confetti = []
        
        # UI Rects
        self.hammer_btn_rect = pygame.Rect(SCREEN_W - 130, 130, 50, 50)
        self.shuffle_btn_rect = pygame.Rect(SCREEN_W - 70, 130, 50, 50)
        self.pause_btn_rect = pygame.Rect(SCREEN_W - 55, 16, 34, 34)
        
        # Menu UI rects
        self.theme_left_rect = pygame.Rect(SCREEN_W//2 - 160, 360, 40, 40)
        self.theme_right_rect = pygame.Rect(SCREEN_W//2 + 120, 360, 40, 40)
        self.mode_timed_rect = pygame.Rect(SCREEN_W//2 - 110, 270, 100, 40)
        self.mode_moves_rect = pygame.Rect(SCREEN_W//2 + 10, 270, 100, 40)
        self.selected_mode = "Timed"
        
        self.update_confetti_surfaces()

    def update_confetti_surfaces(self):
        confetti_emojis = self.renderer.themes[self.renderer.active_theme] + ["✨", "🎉"]
        self.confetti_surfaces = [self.renderer.debris_font.render(e, True, (255,255,255)).convert_alpha() for e in confetti_emojis]

    def _load_highscore(self):
        try:
            if HIGHSCORE_FILE.exists():
                data = json.loads(HIGHSCORE_FILE.read_text())
                return data.get("highscore", 0)
        except Exception: return 0
        return 0

    def _save_highscore(self, score):
        try: HIGHSCORE_FILE.write_text(json.dumps({"highscore": score}))
        except Exception: pass

    def _make_bg(self):
        s = pygame.Surface((SCREEN_W, SCREEN_H))
        for y in range(SCREEN_H):
            t = y / SCREEN_H
            r = int(lerp(BG_TOP[0], BG_BOTTOM[0], t))
            g = int(lerp(BG_TOP[1], BG_BOTTOM[1], t))
            b = int(lerp(BG_TOP[2], BG_BOTTOM[2], t))
            pygame.draw.line(s, (r, g, b), (0, y), (SCREEN_W, y))
        return s.convert()

    def _make_menu_gems(self):
        gems = []
        for _ in range(15):
            gems.append({
                'x': random.uniform(0, SCREEN_W), 'y': random.uniform(0, SCREEN_H),
                'vy': random.uniform(20, 60), 'type': random.randint(0, GEM_TYPES - 1),
                'rot': random.uniform(0, math.tau), 'vrot': random.uniform(-1, 1),
                'scale': random.uniform(0.5, 1.2), 'alpha': random.uniform(0.15, 0.4),
            })
        return gems

    def _new_board(self):
        self.board = Board(self.audio, self.reduced_motion, mode=self.selected_mode)
        self.board.renderer = self.renderer
        self.update_confetti_surfaces()

    def run(self):
        running = True
        while running:
            raw_dt = self.clock.tick(FPS) / 1000.0
            dt = min(raw_dt, 1/30) * self.time_scale
            self.menu_t += raw_dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == GameState.PLAYING: self.state = GameState.PAUSED; self.audio.stop_music()
                        elif self.state == GameState.PAUSED: self.state = GameState.PLAYING; self.audio.play_music()
                        elif self.state == GameState.MENU: running = False
                        elif self.state == GameState.GAME_OVER: self.state = GameState.MENU
                    elif event.key == pygame.K_p:
                        if self.state == GameState.PLAYING: self.state = GameState.PAUSED; self.audio.stop_music()
                        elif self.state == GameState.PAUSED: self.state = GameState.PLAYING; self.audio.play_music()
                    elif event.key == pygame.K_m: self.audio.toggle_mute()
                    elif event.key == pygame.K_r:
                        self.reduced_motion = not self.reduced_motion
                        if self.board: self.board.reduced_motion = self.reduced_motion
                    elif event.key == pygame.K_F1: self.show_debug = not self.show_debug
                    elif event.key == pygame.K_F2: self.time_scale = 0.2 if self.time_scale == 1.0 else 1.0
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        if self.state == GameState.MENU:
                            self._new_board(); self.state = GameState.PLAYING; self.audio.play('click'); self.audio.play_music()
                        elif self.state == GameState.GAME_OVER: self.state = GameState.MENU; self.audio.play('click')
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.state == GameState.PLAYING:
                        if self.pause_btn_rect.collidepoint(event.pos):
                            self.state = GameState.PAUSED; self.audio.stop_music(); self.audio.play('click')
                        elif self.hammer_btn_rect.collidepoint(event.pos):
                            self.board.use_hammer()
                        elif self.shuffle_btn_rect.collidepoint(event.pos):
                            self.board.use_shuffle()
                        else:
                            self.board.handle_drag_start(*event.pos)
                    elif self.state == GameState.MENU: self._handle_menu_click(*event.pos)
                    elif self.state == GameState.PAUSED: self._handle_pause_click(*event.pos)
                    elif self.state == GameState.GAME_OVER: self._handle_gameover_click(*event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    if self.state == GameState.PLAYING: self.board.handle_drag_move(*event.pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if self.state == GameState.PLAYING: self.board.handle_drag_end(*event.pos)

            if self.state == GameState.PLAYING:
                self.board.update(dt, game_active=True)
                if (self.board.mode == "Timed" and self.board.time_left <= 0) or \
                   (self.board.mode == "Moves" and self.board.moves_left <= 0 and self.board.state == 'idle'):
                    self.state = GameState.GAME_OVER
                    self.audio.stop_music()
                    if self.board.score > self.high_score:
                        self.high_score = self.board.score; self._save_highscore(self.board.score)
                    self.audio.play('over')
            elif self.state == GameState.MENU: self._update_menu(raw_dt)
            elif self.state == GameState.GAME_OVER: self._update_gameover(raw_dt)

            self.screen.blit(self.bg_surface, (0, 0))

            if self.state == GameState.MENU: self._draw_menu()
            elif self.state == GameState.PLAYING:
                self._draw_hud(); self.board.draw(self.screen, self.menu_t, self.font_sm, self.font_md, self.font_lg)
            elif self.state == GameState.PAUSED:
                self._draw_hud(); self.board.draw(self.screen, self.menu_t, self.font_sm, self.font_md, self.font_lg); self._draw_pause()
            elif self.state == GameState.GAME_OVER:
                self._draw_hud(); self.board.draw(self.screen, self.menu_t, self.font_sm, self.font_md, self.font_lg); self._draw_game_over()

            if self.show_debug: self._draw_debug()
            pygame.display.flip()

        pygame.quit()

    def _update_menu(self, dt):
        for g in self.menu_gems:
            g['y'] += g['vy'] * dt; g['rot'] += g['vrot'] * dt
            if g['y'] > SCREEN_H + 50:
                g['y'] = -50; g['x'] = random.uniform(0, SCREEN_W)

    def _update_gameover(self, dt):
        if not self.reduced_motion and random.random() < 0.3:
            self.confetti.append({
                'x': random.uniform(0, SCREEN_W), 'y': -10,
                'vy': random.uniform(100, 300), 'vx': random.uniform(-30, 30),
                'rot': random.uniform(0, math.tau), 'vrot': random.uniform(-5, 5),
                'sprite': random.choice(self.confetti_surfaces),
                'life': 3.0
            })
        for c in self.confetti:
            c['y'] += c['vy'] * dt; c['x'] += c['vx'] * dt
            c['rot'] += c['vrot'] * dt; c['life'] -= dt
        self.confetti = [c for c in self.confetti if c['life'] > 0 and c['y'] < SCREEN_H + 20]

    def _draw_menu(self):
        for g in self.menu_gems:
            s = self.renderer.theme_surfaces[self.renderer.active_theme][g['type']]
            sz = int(CELL * g['scale'])
            scaled = pygame.transform.smoothscale(s, (sz, sz))
            rotated = pygame.transform.rotate(scaled, math.degrees(g['rot']))
            rotated.set_alpha(int(255 * g['alpha']))
            self.screen.blit(rotated, (g['x'] - rotated.get_width() / 2, g['y'] - rotated.get_height() / 2))

        title = self.font_huge.render("MATCH", True, TEXT)
        title2 = self.font_huge.render("3", True, ACCENT)
        bob = math.sin(self.menu_t * 2) * 6
        self.screen.blit(title, (SCREEN_W / 2 - title.get_width() - 10, 140 + bob))
        self.screen.blit(title2, (SCREEN_W / 2 + 10, 140 + bob))

        subtitle = self.font_sm.render("SYNTHWAVE EDITION", True, TEXT_DIM)
        self.screen.blit(subtitle, (SCREEN_W / 2 - subtitle.get_width() / 2, 220 + bob))

        mx, my = pygame.mouse.get_pos()
        
        # Mode Selection
        hover_t = self.mode_timed_rect.collidepoint(mx, my)
        col_t = ACCENT if hover_t or self.selected_mode == "Timed" else PANEL_HI
        pygame.draw.rect(self.screen, col_t, self.mode_timed_rect, border_radius=8)
        t_txt = self.font_sm.render("TIMED", True, (30, 26, 60) if hover_t or self.selected_mode == "Timed" else TEXT)
        self.screen.blit(t_txt, (self.mode_timed_rect.centerx - t_txt.get_width()//2, self.mode_timed_rect.centery - t_txt.get_height()//2))
        
        hover_m = self.mode_moves_rect.collidepoint(mx, my)
        col_m = ACCENT if hover_m or self.selected_mode == "Moves" else PANEL_HI
        pygame.draw.rect(self.screen, col_m, self.mode_moves_rect, border_radius=8)
        m_txt = self.font_sm.render("MOVES", True, (30, 26, 60) if hover_m or self.selected_mode == "Moves" else TEXT)
        self.screen.blit(m_txt, (self.mode_moves_rect.centerx - m_txt.get_width()//2, self.mode_moves_rect.centery - m_txt.get_height()//2))

        # Theme Selector
        hover_l = self.theme_left_rect.collidepoint(mx, my)
        col_l = ACCENT if hover_l else PANEL_HI
        pygame.draw.rect(self.screen, col_l, self.theme_left_rect, border_radius=8)
        l_icon = self.renderer.icons['left']
        self.screen.blit(l_icon, (self.theme_left_rect.centerx - l_icon.get_width()//2, self.theme_left_rect.centery - l_icon.get_height()//2))
        
        hover_r = self.theme_right_rect.collidepoint(mx, my)
        col_r = ACCENT if hover_r else PANEL_HI
        pygame.draw.rect(self.screen, col_r, self.theme_right_rect, border_radius=8)
        r_icon = self.renderer.icons['right']
        self.screen.blit(r_icon, (self.theme_right_rect.centerx - r_icon.get_width()//2, self.theme_right_rect.centery - r_icon.get_height()//2))
        
        theme_txt = self.font_md.render(self.renderer.active_theme, True, ACCENT)
        self.screen.blit(theme_txt, (SCREEN_W/2 - theme_txt.get_width()/2, 365))
        
        preview_emojis = self.renderer.theme_surfaces[self.renderer.active_theme]
        spacing = 6
        total_w = sum(e.get_width() + spacing for e in preview_emojis) - spacing
        start_x = SCREEN_W/2 - total_w/2
        for e in preview_emojis:
            self.screen.blit(e, (start_x, 400))
            start_x += e.get_width() + spacing

        # Play Button
        btn_w, btn_h = 240, 64; btn_x = SCREEN_W / 2 - btn_w / 2; btn_y = 470
        hover = btn_x <= mx <= btn_x + btn_w and btn_y <= my <= btn_y + btn_h
        pulse = 1.0 + 0.03 * math.sin(self.menu_t * 4) if hover else 1.0
        bw, bh = int(btn_w * pulse), int(btn_h * pulse)
        bx, by = SCREEN_W / 2 - bw / 2, btn_y + (btn_h - bh) / 2
        btn_rect = pygame.Rect(bx, by, bw, bh)
        pygame.draw.rect(self.screen, ACCENT, btn_rect, border_radius=16)
        pygame.draw.rect(self.screen, (255, 255, 255), btn_rect, 3, border_radius=16)
        play_txt = self.font_lg.render("PLAY", True, (30, 26, 60))
        self.screen.blit(play_txt, (SCREEN_W / 2 - play_txt.get_width() / 2, by + bh / 2 - play_txt.get_height() / 2))

        if self.high_score > 0:
            hs_txt = self.font_sm.render(f"High Score: {self.high_score:,}", True, ACCENT)
            self.screen.blit(hs_txt, (SCREEN_W / 2 - hs_txt.get_width() / 2, 560))

        instr = [
            "Match 3+ emojis. Break 🧊, 📦, 🪨.",
            "Mix 💣 and 🌈 for huge combos!",
            "Trigger Frenzy Mode with x4 combos!",
            "",
            "P: pause  M: mute  R: reduced motion",
        ]
        for i, line in enumerate(instr):
            if not line: continue
            col = TEXT_DIM
            t = self.font_xs.render(line, True, col)
            self.screen.blit(t, (SCREEN_W / 2 - t.get_width() / 2, 610 + i * 22))

    def _handle_menu_click(self, mx, my):
        # Mode selection
        if self.mode_timed_rect.collidepoint(mx, my):
            self.selected_mode = "Timed"; self.audio.play('click'); return
        if self.mode_moves_rect.collidepoint(mx, my):
            self.selected_mode = "Moves"; self.audio.play('click'); return
            
        # Check arrows first
        if self.theme_left_rect.collidepoint(mx, my):
            idx = self.renderer.theme_names.index(self.renderer.active_theme)
            self.renderer.active_theme = self.renderer.theme_names[(idx - 1) % len(self.renderer.theme_names)]
            self.audio.play('click')
            return
        if self.theme_right_rect.collidepoint(mx, my):
            idx = self.renderer.theme_names.index(self.renderer.active_theme)
            self.renderer.active_theme = self.renderer.theme_names[(idx + 1) % len(self.renderer.theme_names)]
            self.audio.play('click')
            return
            
        btn_w, btn_h = 240, 64; btn_x = SCREEN_W / 2 - btn_w / 2; btn_y = 470
        if btn_x <= mx <= btn_x + btn_w and btn_y <= my <= btn_y + btn_h:
            self._new_board(); self.state = GameState.PLAYING; self.audio.play('click'); self.audio.play_music()

    def _handle_pause_click(self, mx, my):
        bw, bh = 200, 56; bx = SCREEN_W / 2 - bw / 2
        by = SCREEN_H / 2 - 40
        if bx <= mx <= bx + bw and by <= my <= by + bh:
            self.state = GameState.PLAYING; self.audio.play('click'); self.audio.play_music()
        by2 = SCREEN_H / 2 + 40
        if bx <= mx <= bx + bw and by2 <= my <= by2 + bh:
            self.state = GameState.MENU; self.audio.play('click')

    def _handle_gameover_click(self, mx, my):
        bw, bh = 200, 56; bx = SCREEN_W / 2 - bw / 2
        by = SCREEN_H / 2 + 100
        if bx <= mx <= bx + bw and by <= my <= by + bh:
            self._new_board(); self.state = GameState.PLAYING; self.audio.play('click'); self.audio.play_music()
        by2 = SCREEN_H / 2 + 170
        if bx <= mx <= bx + bw and by2 <= my <= by2 + bh:
            self.state = GameState.MENU; self.audio.play('click')

    def _draw_hud(self):
        panel = pygame.Rect(0, 0, SCREEN_W, 200)
        pygame.draw.rect(self.screen, PANEL, panel)
        pygame.draw.line(self.screen, PANEL_HI, (0, 200), (SCREEN_W, 200), 2)

        score_label = self.font_xs.render("SCORE", True, TEXT_DIM)
        self.screen.blit(score_label, (20, 16))
        score_txt = self.font_lg.render(f"{self.board.score:,}", True, TEXT)
        self.screen.blit(score_txt, (20, 34))

        lvl_label = self.font_xs.render("LEVEL", True, TEXT_DIM)
        self.screen.blit(lvl_label, (20, 80))
        lvl_txt = self.font_md.render(f"{self.board.level}", True, ACCENT)
        self.screen.blit(lvl_txt, (20, 98))

        bar_x, bar_y, bar_w, bar_h = 90, 106, 200, 14
        pygame.draw.rect(self.screen, GRID_CELL, (bar_x, bar_y, bar_w, bar_h), border_radius=7)
        progress = clamp(self.board.score / self.board.target_score, 0, 1)
        fill_w = int(bar_w * progress)
        if fill_w > 0: pygame.draw.rect(self.screen, GOOD, (bar_x, bar_y, fill_w, bar_h), border_radius=7)
        target_txt = self.font_xs.render(f"→ {self.board.target_score:,}", True, TEXT_DIM)
        self.screen.blit(target_txt, (bar_x + bar_w + 8, bar_y))

        mc_label = self.font_xs.render("MAX COMBO", True, TEXT_DIM)
        self.screen.blit(mc_label, (20, 130))
        mc_txt = self.font_md.render(f"x{self.board.max_combo}", True, DANGER)
        self.screen.blit(mc_txt, (20, 148))

        # Power-up Buttons
        mx, my = pygame.mouse.get_pos()
        
        # Shuffle Button
        hover_s = self.shuffle_btn_rect.collidepoint(mx, my)
        col_s = ACCENT if hover_s else PANEL_HI
        pygame.draw.rect(self.screen, col_s, self.shuffle_btn_rect, border_radius=10)
        pygame.draw.rect(self.screen, TEXT, self.shuffle_btn_rect, 2, border_radius=10)
        s_icon = self.renderer.icons['shuffle']
        self.screen.blit(s_icon, (self.shuffle_btn_rect.centerx - s_icon.get_width()//2, self.shuffle_btn_rect.centery - s_icon.get_height()//2 - 5))
        s_count = self.font_xs.render(f"x{self.board.shuffles_left}", True, ACCENT)
        self.screen.blit(s_count, (self.shuffle_btn_rect.centerx - s_count.get_width()//2, self.shuffle_btn_rect.bottom - 16))

        # Hammer Button
        hover_h = self.hammer_btn_rect.collidepoint(mx, my)
        col_h = DANGER if hover_h or self.board.hammer_mode else PANEL_HI
        pygame.draw.rect(self.screen, col_h, self.hammer_btn_rect, border_radius=10)
        pygame.draw.rect(self.screen, TEXT, self.hammer_btn_rect, 2, border_radius=10)
        h_icon = self.renderer.icons['hammer']
        self.screen.blit(h_icon, (self.hammer_btn_rect.centerx - h_icon.get_width()//2, self.hammer_btn_rect.centery - h_icon.get_height()//2 - 5))
        h_count = self.font_xs.render(f"x{self.board.hammers_left}", True, ACCENT)
        self.screen.blit(h_count, (self.hammer_btn_rect.centerx - h_count.get_width()//2, self.hammer_btn_rect.bottom - 16))

        # Pause Button
        hover_p = self.pause_btn_rect.collidepoint(mx, my)
        col_p = PANEL_HI if hover_p else PANEL
        pygame.draw.rect(self.screen, col_p, self.pause_btn_rect, border_radius=6)
        pygame.draw.rect(self.screen, TEXT, self.pause_btn_rect, 2, border_radius=6)
        p_icon = self.renderer.icons['pause']
        self.screen.blit(p_icon, (self.pause_btn_rect.centerx - p_icon.get_width()//2, self.pause_btn_rect.centery - p_icon.get_height()//2))

        # Timer / Moves Display
        if self.board.mode == "Timed":
            time_warn = self.board.time_left <= 10
            time_col = DANGER if time_warn else TEXT
            if time_warn:
                pulse = 0.5 + 0.5 * math.sin(self.menu_t * 8)
                time_col = (int(255 * (0.7 + 0.3 * pulse)), int(90 * (0.7 + 0.3 * pulse)), int(110 * (0.7 + 0.3 * pulse)))
            time_label = self.font_xs.render("TIME", True, TEXT_DIM)
            self.screen.blit(time_label, (SCREEN_W - 95, 60))
            time_txt = self.font_lg.render(f"{int(self.board.time_left):02d}", True, time_col)
            self.screen.blit(time_txt, (SCREEN_W - 95, 78))

            tb_x, tb_y, tb_w, tb_h = 20, 175, SCREEN_W - 40, 6
            pygame.draw.rect(self.screen, GRID_CELL, (tb_x, tb_y, tb_w, tb_h), border_radius=3)
            tp = clamp(self.board.time_left / GAME_TIME, 0, 1)
            tfw = int(tb_w * tp)
            if tfw > 0:
                tb_col = DANGER if time_warn else ACCENT
                pygame.draw.rect(self.screen, tb_col, (tb_x, tb_y, tfw, tb_h), border_radius=3)
        else:
            moves_warn = self.board.moves_left <= 5
            moves_col = DANGER if moves_warn else TEXT
            if moves_warn:
                pulse = 0.5 + 0.5 * math.sin(self.menu_t * 8)
                moves_col = (int(255 * (0.7 + 0.3 * pulse)), int(90 * (0.7 + 0.3 * pulse)), int(110 * (0.7 + 0.3 * pulse)))
            moves_label = self.font_xs.render("MOVES", True, TEXT_DIM)
            self.screen.blit(moves_label, (SCREEN_W - 95, 60))
            moves_txt = self.font_lg.render(f"{int(self.board.moves_left):02d}", True, moves_col)
            self.screen.blit(moves_txt, (SCREEN_W - 95, 78))

            tb_x, tb_y, tb_w, tb_h = 20, 175, SCREEN_W - 40, 6
            pygame.draw.rect(self.screen, GRID_CELL, (tb_x, tb_y, tb_w, tb_h), border_radius=3)
            tp = clamp(self.board.moves_left / MOVES_MODE, 0, 1)
            tfw = int(tb_w * tp)
            if tfw > 0:
                tb_col = DANGER if moves_warn else ACCENT
                pygame.draw.rect(self.screen, tb_col, (tb_x, tb_y, tfw, tb_h), border_radius=3)
            
        # Frenzy indicator
        if self.board.frenzy_t > 0:
            pulse = 0.5 + 0.5 * math.sin(self.menu_t * 10)
            col = (int(255*pulse), int(100*pulse), int(255*pulse))
            f_txt = self.font_md.render(f"FRENZY x2!", True, col)
            self.screen.blit(f_txt, (SCREEN_W/2 - f_txt.get_width()/2, 130))

    def _draw_pause(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180)); self.screen.blit(overlay, (0, 0))
        title = self.font_xl.render("PAUSED", True, TEXT)
        self.screen.blit(title, (SCREEN_W / 2 - title.get_width() / 2, SCREEN_H / 2 - 140))

        bw, bh = 200, 56; bx = SCREEN_W / 2 - bw / 2; mx, my = pygame.mouse.get_pos()
        by = SCREEN_H / 2 - 40
        hover = bx <= mx <= bx + bw and by <= my <= by + bh
        col = ACCENT if hover else PANEL_HI
        pygame.draw.rect(self.screen, col, (bx, by, bw, bh), border_radius=14)
        pygame.draw.rect(self.screen, TEXT, (bx, by, bw, bh), 2, border_radius=14)
        t = self.font_md.render("RESUME", True, (30, 26, 60) if hover else TEXT)
        self.screen.blit(t, (SCREEN_W / 2 - t.get_width() / 2, by + bh / 2 - t.get_height() / 2))

        by2 = SCREEN_H / 2 + 40
        hover2 = bx <= mx <= bx + bw and by2 <= my <= by2 + bh
        col2 = DANGER if hover2 else PANEL_HI
        pygame.draw.rect(self.screen, col2, (bx, by2, bw, bh), border_radius=14)
        pygame.draw.rect(self.screen, TEXT, (bx, by2, bw, bh), 2, border_radius=14)
        t2 = self.font_md.render("QUIT", True, (30, 26, 60) if hover2 else TEXT)
        self.screen.blit(t2, (SCREEN_W / 2 - t2.get_width() / 2, by2 + bh / 2 - t2.get_height() / 2))

    def _draw_game_over(self):
        for c in self.confetti:
            rotated = pygame.transform.rotate(c['sprite'], math.degrees(c['rot']))
            self.screen.blit(rotated, (c['x'] - rotated.get_width()/2, c['y'] - rotated.get_height()/2))
            
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200)); self.screen.blit(overlay, (0, 0))
        title = self.font_xl.render("GAME OVER", True, DANGER)
        self.screen.blit(title, (SCREEN_W / 2 - title.get_width() / 2, 140))

        is_new = self.board.score >= self.high_score and self.board.score > 0
        if is_new:
            pulse = 0.5 + 0.5 * math.sin(self.menu_t * 5)
            col = (int(ACCENT[0] * (0.8 + 0.2 * pulse)), int(ACCENT[1] * (0.8 + 0.2 * pulse)), int(ACCENT[2] * (0.8 + 0.2 * pulse)))
            new_txt = self.font_md.render("★ NEW HIGH SCORE! ★", True, col)
            self.screen.blit(new_txt, (SCREEN_W / 2 - new_txt.get_width() / 2, 210))

        stats = [
            ("SCORE", f"{self.board.score:,}", ACCENT),
            ("LEVEL", f"{self.board.level}", TEXT),
            ("MAX COMBO", f"x{self.board.max_combo}", DANGER),
            ("MATCHES", f"{self.board.matches_made}", TEXT),
            ("HIGH SCORE", f"{self.high_score:,}", ACCENT),
        ]
        y = 280
        for label, val, col in stats:
            lt = self.font_sm.render(label, True, TEXT_DIM)
            vt = self.font_md.render(val, True, col)
            self.screen.blit(lt, (SCREEN_W / 2 - 120, y))
            self.screen.blit(vt, (SCREEN_W / 2 + 120 - vt.get_width(), y))
            y += 36

        bw, bh = 200, 56; bx = SCREEN_W / 2 - bw / 2; mx, my = pygame.mouse.get_pos()
        by = SCREEN_H / 2 + 100
        hover = bx <= mx <= bx + bw and by <= my <= by + bh
        col = ACCENT if hover else PANEL_HI
        pygame.draw.rect(self.screen, col, (bx, by, bw, bh), border_radius=14)
        pygame.draw.rect(self.screen, TEXT, (bx, by, bw, bh), 2, border_radius=14)
        t = self.font_md.render("PLAY AGAIN", True, (30, 26, 60) if hover else TEXT)
        self.screen.blit(t, (SCREEN_W / 2 - t.get_width() / 2, by + bh / 2 - t.get_height() / 2))

        by2 = SCREEN_H / 2 + 170
        hover2 = bx <= mx <= bx + bw and by2 <= my <= by2 + bh
        col2 = PANEL_HI if hover2 else PANEL
        pygame.draw.rect(self.screen, col2, (bx, by2, bw, bh), border_radius=14)
        pygame.draw.rect(self.screen, TEXT, (bx, by2, bw, bh), 2, border_radius=14)
        t2 = self.font_md.render("MENU", True, TEXT)
        self.screen.blit(t2, (SCREEN_W / 2 - t2.get_width() / 2, by2 + bh / 2 - t2.get_height() / 2))

    def _draw_debug(self):
        info = [
            f"FPS: {self.clock.get_fps():.0f}",
            f"State: {self.state.name}",
            f"Board: {self.board.state if self.board else 'N/A'}",
            f"VFX: {len(self.board.vfx.parts) if self.board else 0}",
            f"Time scale: {self.time_scale}",
        ]
        for i, line in enumerate(info):
            t = self.font_xs.render(line, True, GOOD)
            self.screen.blit(t, (10, SCREEN_H - 100 + i * 16))

if __name__ == "__main__":
    Game().run()