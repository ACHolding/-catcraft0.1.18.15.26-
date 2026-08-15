#!/usr/bin/env python3
"""
minecraftmytakeackondo0.1 — ac's minecraft my take

EXACTLY Minecraft Indev (finite island). Infdev infinite chunks YEETED.
Self-contained. Pure math + pygame. FILES=off.
Window title + logo: ac's minecraft my take
"""

from __future__ import annotations

import math
import os
import random
import sys
import time
from dataclasses import dataclass
from typing import Iterable, NamedTuple

try:
    import pygame
except ImportError:
    pygame = None

VERSION = "0.1"
BRAND = "ac's minecraft my take"
LOGO = BRAND
EDITION = "Minecraft Indev"
TITLE = "ac's minecraft my take"
FILES = False
INDEV_SEED = 20100131  # Indev-era stamp

# Indev Small Square map (wiki): 128 × 128 × 64 — Island theme
LEVEL_W = 128
LEVEL_D = 128
LEVEL_H = 64
WATER_LEVEL = 32
DAY_LENGTH = 900.0  # ~15 min Indev day/night cycle (seconds)

MOTDS = (
    "Finally Indev!",
    "Finite forever!",
    "Island type!",
    "Small · Square · Island!",
    "Day and night!",
    "ac's minecraft my take!",
    "No infinite maps!",
    "Indev 0.31 vibes!",
    "Generate new level!",
    "Wow!",
    "100% pure!",
    "FILES=off!",
    "Please stand by!",
    "Terraforming the island!",
    "Singleplayer!",
    "Not Infdev. Indev.",
    "Bedrock floor!",
    "Ocean border!",
)

TARGET_FPS = 60
WINDOW_SIZE = (800, 600)
INTERNAL_SIZE = (320, 200)
MAX_FACES_PER_FRAME = 1100
NEAR_PLANE = 0.08
FOV_DEGREES = 70.0
DEFAULT_RENDER_DISTANCE = 48.0
WALK_SPEED = 4.317
SPRINT_SPEED = 5.612
JUMP_SPEED = 8.0
GRAVITY = 28.0

AIR = 0
GRASS = 1
DIRT = 2
STONE = 3
SAND = 4
WOOD = 5
LEAVES = 6
WATER = 7
COBBLE = 8
BEDROCK = 9

BLOCK_NAMES = {
    AIR: "Air",
    GRASS: "Grass",
    DIRT: "Dirt",
    STONE: "Stone",
    SAND: "Sand",
    WOOD: "Wood",
    LEAVES: "Leaves",
    WATER: "Water",
    COBBLE: "Cobblestone",
    BEDROCK: "Bedrock",
}
HOTBAR = (GRASS, DIRT, STONE, SAND, WOOD, LEAVES, COBBLE, WATER)
SOLID = frozenset({GRASS, DIRT, STONE, SAND, WOOD, LEAVES, COBBLE, BEDROCK})

FACE_DATA: tuple[
    tuple[tuple[int, int, int], tuple[tuple[int, int, int], ...]], ...
] = (
    ((-1, 0, 0), ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0))),
    ((1, 0, 0), ((1, 0, 1), (1, 0, 0), (1, 1, 0), (1, 1, 1))),
    ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1))),
    ((0, 1, 0), ((0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0))),
    ((0, 0, -1), ((1, 0, 0), (0, 0, 0), (0, 1, 0), (1, 1, 0))),
    ((0, 0, 1), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))),
)
FACE_SHADE = (0.72, 0.86, 0.54, 1.00, 0.78, 0.90)

SKY_DAY = (110, 170, 255)
SKY_HORIZON_DAY = (180, 210, 245)
SKY_NIGHT = (8, 10, 28)
SKY_HORIZON_NIGHT = (20, 24, 48)
FOG_DAY = SKY_HORIZON_DAY
FOG_NIGHT = SKY_HORIZON_NIGHT


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def hash2(x: int, z: int, seed: int = 0) -> float:
    n = (x * 0x1F123BB5) ^ (z * 0x5F356495) ^ (seed * 0x6C8E9CF5)
    n = (n ^ (n >> 13)) * 0x45D9F3B
    n = (n ^ (n >> 16)) & 0xFFFFFFFF
    return n / 4294967296.0


def value_noise(x: float, z: float, scale: float, seed: int) -> float:
    sx, sz = x / scale, z / scale
    x0, z0 = math.floor(sx), math.floor(sz)
    tx, tz = smoothstep(sx - x0), smoothstep(sz - z0)
    a = lerp(hash2(x0, z0, seed), hash2(x0 + 1, z0, seed), tx)
    b = lerp(hash2(x0, z0 + 1, seed), hash2(x0 + 1, z0 + 1, seed), tx)
    return lerp(a, b, tz)


def fbm(x: float, z: float, seed: int, octaves: int = 3) -> float:
    amp, freq, total, norm = 0.5, 1.0, 0.0, 0.0
    for i in range(octaves):
        total += value_noise(x * freq, z * freq, 1.0, seed + i * 101) * amp
        norm += amp
        amp *= 0.5
        freq *= 2.0
    return total / norm


def color_mix(a, b, t):
    t = clamp(t, 0.0, 1.0)
    return (int(lerp(a[0], b[0], t)), int(lerp(a[1], b[1], t)), int(lerp(a[2], b[2], t)))


def color_scale(c, f):
    return (int(clamp(c[0] * f, 0, 255)), int(clamp(c[1] * f, 0, 255)), int(clamp(c[2] * f, 0, 255)))


def random_motd() -> str:
    return random.choice(MOTDS)


@dataclass(slots=True)
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class Face(NamedTuple):
    x: int
    y: int
    z: int
    block: int
    face_index: int


class Progress:
    def __init__(self, win, clock, fonts) -> None:
        self.win = win
        self.clock = clock
        self.font, self.big, self.logo = fonts
        self.label = "Generating level"
        self.fraction = 0.0
        self.stage = "Starting..."
        self._bg = None

    def _dirt_bg(self):
        if self._bg is not None:
            return self._bg
        w, h = self.win.get_size()
        s = pygame.Surface((w, h))
        for y in range(0, h, 16):
            for x in range(0, w, 16):
                n = hash2(x // 16, y // 16, 7)
                c = int(90 + n * 40)
                pygame.draw.rect(s, (c, int(c * 0.7), int(c * 0.42)), (x, y, 16, 16))
        dark = pygame.Surface((w, h), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 120))
        s.blit(dark, (0, 0))
        self._bg = s
        return s

    def _panel(self, x, y, bw, bh, fill=(40, 40, 40)):
        r = pygame.Rect(x, y, bw, bh)
        pygame.draw.rect(self.win, (0, 0, 0), r.inflate(4, 4))
        pygame.draw.rect(self.win, fill, r)
        pygame.draw.rect(self.win, (220, 220, 220), r, 2)
        return r

    def _text_in_box(self, font, text, rect, color=(255, 255, 255)):
        label = text if (text and text.strip()) else "..."
        img = font.render(label, True, color)
        if img.get_width() > rect.width - 8:
            img = self.font.render(label, True, color)
        sh = self.font.render(label, True, (0, 0, 0))
        tx = rect.centerx - img.get_width() // 2
        ty = rect.centery - img.get_height() // 2
        self.win.blit(sh, (tx + 1, ty + 1))
        self.win.blit(img, (tx, ty))

    def set(self, fraction: float, stage: str = "", label: str | None = None) -> None:
        self.fraction = clamp(fraction, 0.0, 1.0)
        if stage:
            self.stage = stage
        if label is not None:
            self.label = label
        self.draw()

    def draw(self) -> None:
        assert pygame is not None
        self.clock.tick(60)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                raise SystemExit(0)
        w, h = self.win.get_size()
        self.win.blit(self._dirt_bg(), (0, 0))
        brand = self._panel((w - 440) // 2, h // 2 - 130, 440, 44, (20, 60, 20))
        self._text_in_box(self.logo, LOGO, brand, (80, 255, 80))
        title = self._panel((w - 440) // 2, h // 2 - 70, 440, 36, (50, 50, 50))
        self._text_in_box(self.big, self.label or "Generating level", title)
        stage = self._panel((w - 440) // 2, h // 2 - 26, 440, 32, (55, 55, 40))
        self._text_in_box(self.font, self.stage or "Starting...", stage, (255, 255, 180))
        bw, bh = 440, 28
        bx, by = (w - bw) // 2, h // 2 + 20
        bar = self._panel(bx, by, bw, bh, (70, 70, 70))
        fill = int((bw - 4) * self.fraction)
        if fill > 0:
            pygame.draw.rect(self.win, (90, 200, 90), (bx + 2, by + 2, fill, bh - 4))
        self._text_in_box(self.font, "%s — %d%%" % (self.label, int(self.fraction * 100)), bar)
        pct = self._panel((w - 200) // 2, by + bh + 14, 200, 28, (45, 45, 45))
        self._text_in_box(self.font, "%d%% complete" % int(self.fraction * 100), pct)
        foot = self._panel((w - 440) // 2, h - 48, 440, 28, (35, 35, 35))
        self._text_in_box(self.font, EDITION + " · Island · Small · Square", foot, (200, 200, 200))
        pygame.display.flip()


class TextureBank:
    SIZE = 8
    BASE = {
        GRASS: (74, 157, 62),
        DIRT: (126, 86, 52),
        STONE: (126, 132, 137),
        SAND: (218, 202, 139),
        WOOD: (139, 96, 52),
        LEAVES: (55, 129, 54),
        WATER: (58, 122, 222),
        COBBLE: (110, 110, 110),
        BEDROCK: (48, 48, 53),
    }

    def __init__(self) -> None:
        self.grids = {}
        self.averages = {}
        for block in HOTBAR + (BEDROCK,):
            for face in range(6):
                grid = self._generate(block, face)
                self.grids[(block, face)] = grid
                pixels = [c for row in grid for c in row]
                self.averages[(block, face)] = tuple(
                    sum(c[i] for c in pixels) // len(pixels) for i in range(3)
                )

    def _generate(self, block, face):
        size = self.SIZE
        grid = []
        for v in range(size):
            row = []
            for u in range(size):
                noise = hash2(u + block * 31, v + face * 17, 404)
                base = self.BASE[block]
                factor = 0.84 + noise * 0.30
                if block == GRASS:
                    if face == 3:
                        base = (69, 157, 59)
                    elif face == 2:
                        base = (119, 79, 47)
                    else:
                        base = (119, 79, 47)
                        if v == 0 or (v == 1 and hash2(u, face, 12) > 0.42):
                            base = (70, 151, 57)
                elif block == STONE and noise > 0.82:
                    base = (96, 103, 109)
                elif block == COBBLE:
                    base = (90, 90, 90) if noise < 0.5 else (130, 130, 130)
                    factor = 1.0
                elif block == WOOD and face in (2, 3):
                    ring = abs(math.sin(math.hypot(u - 3.5, v - 3.5) * 2.4))
                    base = color_mix((91, 61, 35), (178, 126, 68), ring)
                    factor = 1.0
                elif block == LEAVES:
                    base = (43, 111, 43) if noise < 0.35 else (65, 143, 57)
                elif block == WATER:
                    base = color_mix((40, 90, 200), (90, 160, 255), noise)
                    factor = 1.0
                elif block == BEDROCK:
                    base = (34, 35, 40) if noise < 0.52 else (65, 66, 70)
                    factor = 1.0
                row.append(color_scale(base, factor))
            grid.append(row)
        return grid


class IndevLevel:
    """Finite Indev Island · Small · Square. Infdev streaming YEETED."""

    def __init__(self, seed: int = INDEV_SEED) -> None:
        self.seed = seed
        self.w = LEVEL_W
        self.d = LEVEL_D
        self.h = LEVEL_H
        self.blocks = bytearray(self.w * self.h * self.d)
        self.mesh: list[Face] = []
        self.day_time = 0.25  # morning

    def _idx(self, x: int, y: int, z: int) -> int:
        return (y * self.d + z) * self.w + x

    def in_bounds(self, x: int, y: int, z: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h and 0 <= z < self.d

    def get(self, pos: tuple[int, int, int]) -> int:
        x, y, z = pos
        if not self.in_bounds(x, y, z):
            # Indev island ocean border
            if y < WATER_LEVEL:
                return WATER
            return AIR
        return self.blocks[self._idx(x, y, z)]

    def set(self, pos: tuple[int, int, int], block: int) -> None:
        x, y, z = pos
        if not self.in_bounds(x, y, z):
            return
        if y == 0 and block != BEDROCK:
            return
        if self.get(pos) == BEDROCK and block != BEDROCK:
            return
        self.blocks[self._idx(x, y, z)] = block & 0xFF

    def generate(self, progress: Progress | None = None) -> None:
        if progress:
            progress.set(0.02, "Preparing Indev island", "Generating level")
        cx, cz = self.w * 0.5, self.d * 0.5
        max_r = min(cx, cz) - 4.0

        for z in range(self.d):
            if progress and z % 8 == 0:
                progress.set(0.05 + 0.55 * (z / self.d), "Raising land %d/%d" % (z + 1, self.d))
            for x in range(self.w):
                dx, dz = x + 0.5 - cx, z + 0.5 - cz
                dist = math.sqrt(dx * dx + dz * dz)
                island = clamp(1.0 - dist / max_r, 0.0, 1.0)
                island = island * island * (3 - 2 * island)
                n = fbm(x * 0.05, z * 0.05, self.seed)
                n2 = fbm(x * 0.12, z * 0.12, self.seed + 9, 2)
                height = int(WATER_LEVEL - 2 + island * (10 + n * 14 + n2 * 4))
                height = int(clamp(height, 1, self.h - 8))
                beach = island < 0.35

                for y in range(self.h):
                    if y == 0:
                        b = BEDROCK
                    elif y > height:
                        b = WATER if y <= WATER_LEVEL else AIR
                    elif y == height:
                        b = SAND if beach or height <= WATER_LEVEL + 1 else GRASS
                    elif y >= height - 3:
                        b = SAND if beach else DIRT
                    else:
                        b = STONE
                    self.blocks[self._idx(x, y, z)] = b

        if progress:
            progress.set(0.65, "Growing trees", "Generating level")
        for z in range(2, self.d - 2):
            for x in range(2, self.w - 2):
                # surface
                top = 0
                for y in range(self.h - 1, -1, -1):
                    if self.get((x, y, z)) in SOLID:
                        top = y
                        break
                if self.get((x, top, z)) != GRASS:
                    continue
                if hash2(x * 13, z * 17, self.seed + 501) < 0.978:
                    continue
                trunk = 3 + int(hash2(x, z, self.seed + 502) * 2)
                for y in range(top + 1, top + trunk + 1):
                    if y < self.h:
                        self.set((x, y, z), WOOD)
                ly = top + trunk
                for ox in range(-2, 3):
                    for oz in range(-2, 3):
                        for oy in range(-1, 2):
                            if abs(ox) + abs(oz) + abs(oy) > 4:
                                continue
                            p = (x + ox, ly + oy, z + oz)
                            if self.get(p) == AIR:
                                self.set(p, LEAVES)
                if ly + 2 < self.h:
                    self.set((x, ly + 2, z), LEAVES)

        if progress:
            progress.set(0.82, "Building meshes", "Building meshes")
        self.rebuild_mesh(progress)

    def rebuild_mesh(self, progress: Progress | None = None) -> None:
        mesh: list[Face] = []
        total = self.w * self.d
        done = 0
        for z in range(self.d):
            for x in range(self.w):
                for y in range(self.h):
                    block = self.get((x, y, z))
                    if block == AIR:
                        continue
                    for fi, (normal, _) in enumerate(FACE_DATA):
                        nb = self.get((x + normal[0], y + normal[1], z + normal[2]))
                        if block == WATER:
                            visible = nb == AIR
                        else:
                            visible = nb == AIR or nb == WATER
                        if visible:
                            mesh.append(Face(x, y, z, block, fi))
                done += 1
            if progress and z % 8 == 0:
                progress.set(0.82 + 0.16 * (done / total), "Building meshes %d%%" % int(100 * done / total))
        self.mesh = mesh

    def highest_solid(self, x: int, z: int) -> int:
        x = int(clamp(x, 0, self.w - 1))
        z = int(clamp(z, 0, self.d - 1))
        for y in range(self.h - 1, -1, -1):
            b = self.get((x, y, z))
            if b in SOLID and b != LEAVES:
                return y
        return WATER_LEVEL

    def tick_day(self, dt: float) -> None:
        self.day_time = (self.day_time + dt / DAY_LENGTH) % 1.0

    def daylight(self) -> float:
        # 0 night … 1 noon — Indev-ish curve
        t = self.day_time
        # sun up ~0.25 to 0.75
        if 0.25 <= t <= 0.75:
            u = (t - 0.25) / 0.5
            return math.sin(u * math.pi)
        if t < 0.25:
            return clamp(1.0 - (0.25 - t) / 0.1, 0.0, 1.0) * 0.15
        return clamp(1.0 - (t - 0.75) / 0.1, 0.0, 1.0) * 0.15


def raycast(world: IndevLevel, origin, direction, max_distance=6.0):
    ox, oy, oz = origin
    dx, dy, dz = direction
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length < 1e-9:
        return None, None
    dx, dy, dz = dx / length, dy / length, dz / length
    cell = [math.floor(ox), math.floor(oy), math.floor(oz)]
    if world.get(tuple(cell)) in SOLID:
        return tuple(cell), None
    steps, t_delta, t_max = [], [], []
    origins = (ox, oy, oz)
    dirs = (dx, dy, dz)
    for axis in range(3):
        d = dirs[axis]
        if d > 0:
            steps.append(1)
            t_delta.append(1.0 / d)
            t_max.append((cell[axis] + 1.0 - origins[axis]) / d)
        elif d < 0:
            steps.append(-1)
            t_delta.append(-1.0 / d)
            t_max.append((origins[axis] - cell[axis]) / -d)
        else:
            steps.append(0)
            t_delta.append(float("inf"))
            t_max.append(float("inf"))
    previous = tuple(cell)
    distance = 0.0
    while distance <= max_distance:
        axis = min(range(3), key=t_max.__getitem__)
        previous = tuple(cell)
        cell[axis] += steps[axis]
        distance = t_max[axis]
        t_max[axis] += t_delta[axis]
        pos = tuple(cell)
        if world.get(pos) in SOLID:
            return pos, previous
    return None, None


class Player:
    WIDTH = 0.62
    HEIGHT = 1.80
    EYE_HEIGHT = 1.62

    def __init__(self) -> None:
        self.pos = Vec3(LEVEL_W * 0.5, WATER_LEVEL + 4, LEVEL_D * 0.5)
        self.velocity = Vec3()
        self.yaw = math.radians(25)
        self.pitch = math.radians(-8)
        self.on_ground = False

    def eye(self):
        return self.pos.x, self.pos.y + self.EYE_HEIGHT, self.pos.z

    def look_vector(self):
        cp = math.cos(self.pitch)
        return math.sin(self.yaw) * cp, math.sin(self.pitch), math.cos(self.yaw) * cp

    def respawn(self, world: IndevLevel) -> None:
        sx, sz = world.w // 2, world.d // 2
        self.pos = Vec3(sx + 0.5, world.highest_solid(sx, sz) + 1.001, sz + 0.5)
        self.velocity = Vec3()
        self.on_ground = False

    def colliding_blocks(self, world: IndevLevel):
        half = self.WIDTH * 0.5
        eps = 1e-6
        for x in range(math.floor(self.pos.x - half + eps), math.floor(self.pos.x + half - eps) + 1):
            for y in range(math.floor(self.pos.y + eps), math.floor(self.pos.y + self.HEIGHT - eps) + 1):
                for z in range(math.floor(self.pos.z - half + eps), math.floor(self.pos.z + half - eps) + 1):
                    if world.get((x, y, z)) in SOLID:
                        yield x, y, z

    def intersects_voxel(self, voxel):
        x, y, z = voxel
        half = self.WIDTH * 0.5
        return (
            self.pos.x + half > x
            and self.pos.x - half < x + 1
            and self.pos.y + self.HEIGHT > y
            and self.pos.y < y + 1
            and self.pos.z + half > z
            and self.pos.z - half < z + 1
        )

    def _move_axis(self, world, axis, amount):
        if abs(amount) < 1e-10:
            return
        setattr(self.pos, axis, getattr(self.pos, axis) + amount)
        collisions = list(self.colliding_blocks(world))
        if not collisions:
            return
        half = self.WIDTH * 0.5
        eps = 1e-5
        if axis == "x":
            self.pos.x = (
                min(x - half - eps for x, _y, _z in collisions)
                if amount > 0
                else max(x + 1 + half + eps for x, _y, _z in collisions)
            )
            self.velocity.x = 0.0
        elif axis == "z":
            self.pos.z = (
                min(z - half - eps for _x, _y, z in collisions)
                if amount > 0
                else max(z + 1 + half + eps for _x, _y, z in collisions)
            )
            self.velocity.z = 0.0
        else:
            if amount > 0:
                self.pos.y = min(y - self.HEIGHT - eps for _x, y, _z in collisions)
            else:
                self.pos.y = max(y + 1 + eps for _x, y, _z in collisions)
                self.on_ground = True
            self.velocity.y = 0.0

    def physics_step(self, world, wish_x, wish_z, jump, sprint, dt):
        length = math.hypot(wish_x, wish_z)
        if length > 1.0:
            wish_x, wish_z = wish_x / length, wish_z / length
        speed = SPRINT_SPEED if sprint else WALK_SPEED
        sy, cy = math.sin(self.yaw), math.cos(self.yaw)
        self.velocity.x = (wish_x * cy + wish_z * sy) * speed
        self.velocity.z = (-wish_x * sy + wish_z * cy) * speed
        if jump and self.on_ground:
            self.velocity.y = JUMP_SPEED
            self.on_ground = False
        self.velocity.y = max(-40.0, self.velocity.y - GRAVITY * dt)
        self.on_ground = False
        self._move_axis(world, "x", self.velocity.x * dt)
        self._move_axis(world, "z", self.velocity.z * dt)
        self._move_axis(world, "y", self.velocity.y * dt)
        # Indev void under map
        if self.pos.y < -5:
            self.respawn(world)


def clip_near(poly):
    if not poly:
        return []
    output = []
    previous = poly[-1]
    previous_inside = previous[2] >= NEAR_PLANE
    for current in poly:
        current_inside = current[2] >= NEAR_PLANE
        if current_inside != previous_inside:
            dz = current[2] - previous[2]
            t = (NEAR_PLANE - previous[2]) / dz if abs(dz) > 1e-12 else 0.0
            output.append((lerp(previous[0], current[0], t), lerp(previous[1], current[1], t), NEAR_PLANE))
        if current_inside:
            output.append(current)
        previous, previous_inside = current, current_inside
    return output


class SoftwareRenderer:
    def __init__(self, textures: TextureBank) -> None:
        assert pygame is not None
        self.width, self.height = INTERNAL_SIZE
        self.scene = pygame.Surface(INTERNAL_SIZE).convert()
        self.textures = textures
        self.focal = self.width * 0.5 / math.tan(math.radians(FOV_DEGREES) * 0.5)
        self.render_distance = DEFAULT_RENDER_DISTANCE
        self.font = pygame.font.Font(None, 20)
        self.small_font = pygame.font.Font(None, 16)
        self.faces_drawn = 0
        self.polygons_drawn = 0
        self.icons = {b: self._build_icon(b) for b in HOTBAR}
        self._sky_cache_key = None
        self.sky = pygame.Surface(INTERNAL_SIZE).convert()

    def _build_icon(self, block):
        icon = pygame.Surface((32, 32)).convert()
        grid = self.textures.grids[(block, 3)]
        for y, row in enumerate(grid):
            for x, color in enumerate(row):
                pygame.draw.rect(icon, color, (x * 4, y * 4, 4, 4))
        pygame.draw.rect(icon, (32, 36, 39), icon.get_rect(), 2)
        return icon

    def _update_sky(self, daylight: float) -> tuple:
        top = color_mix(SKY_NIGHT, SKY_DAY, daylight)
        horiz = color_mix(SKY_HORIZON_NIGHT, SKY_HORIZON_DAY, daylight)
        fog = color_mix(FOG_NIGHT, FOG_DAY, daylight)
        key = (top, horiz)
        if key != self._sky_cache_key:
            for y in range(self.height):
                t = y / max(1, self.height - 1)
                pygame.draw.line(self.sky, color_mix(top, horiz, t ** 0.75), (0, y), (self.width, y))
            self._sky_cache_key = key
        return fog

    def project(self, p):
        inv = self.focal / p[2]
        return (
            int(clamp(self.width * 0.5 + p[0] * inv, -4096, 4096)),
            int(clamp(self.height * 0.5 - p[1] * inv, -4096, 4096)),
        )

    def _draw_face_fast(self, world_vertices, camera, sy, cy, sp, cp, block, face_index, distance, fog_color):
        shade = FACE_SHADE[face_index]
        fog = clamp((distance - self.render_distance * 0.55) / (self.render_distance * 0.45), 0.0, 1.0)
        transformed = []
        for px, py, pz in world_vertices:
            dx, dy, dz = px - camera[0], py - camera[1], pz - camera[2]
            x1 = dx * cy - dz * sy
            z1 = dx * sy + dz * cy
            y1 = dy * cp - z1 * sp
            z2 = dy * sp + z1 * cp
            transformed.append((x1, y1, z2))
        clipped = clip_near(transformed)
        if len(clipped) < 3:
            return
        color = color_scale(self.textures.averages[(block, face_index)], shade)
        color = color_mix(color, fog_color, fog)
        # night darken
        pygame.draw.polygon(self.scene, color, [self.project(pt) for pt in clipped])
        self.polygons_drawn += 1

    def render_world(self, world: IndevLevel, player: Player) -> None:
        daylight = world.daylight()
        fog_color = self._update_sky(daylight)
        # dim faces at night
        night = 1.0 - daylight * 0.85
        self.scene.blit(self.sky, (0, 0))
        camera = player.eye()
        max_d2 = self.render_distance * self.render_distance
        sy, cy = math.sin(player.yaw), math.cos(player.yaw)
        sp, cp = math.sin(player.pitch), math.cos(player.pitch)
        candidates = []
        append = candidates.append
        for face in world.mesh:
            normal = FACE_DATA[face.face_index][0]
            cx = face.x + 0.5 + normal[0] * 0.5
            cy_ = face.y + 0.5 + normal[1] * 0.5
            cz = face.z + 0.5 + normal[2] * 0.5
            dx, dy, dz = cx - camera[0], cy_ - camera[1], cz - camera[2]
            d2 = dx * dx + dy * dy + dz * dz
            if d2 > max_d2:
                continue
            if normal[0] * -dx + normal[1] * -dy + normal[2] * -dz <= 0.001:
                continue
            cam_x = dx * cy - dz * sy
            cam_z = dx * sy + dz * cy
            if cam_z < -1.5 or abs(cam_x) > max(3.0, cam_z * 1.55 + 2.0):
                continue
            append((d2, face))
        candidates.sort(key=lambda i: i[0], reverse=True)
        if len(candidates) > MAX_FACES_PER_FRAME:
            candidates = candidates[:MAX_FACES_PER_FRAME]
        self.faces_drawn = len(candidates)
        self.polygons_drawn = 0
        for d2, face in candidates:
            verts = tuple(
                (face.x + vx, face.y + vy, face.z + vz)
                for vx, vy, vz in FACE_DATA[face.face_index][1]
            )
            # bake night into fog a bit
            fc = color_mix(fog_color, (0, 0, 0), night * 0.35)
            self._draw_face_fast(verts, camera, sy, cy, sp, cp, face.block, face.face_index, math.sqrt(d2), fc)

    def draw_selection(self, player, target):
        if target is None:
            return
        x, y, z = target
        eps = 0.003
        corners = (
            (x - eps, y - eps, z - eps), (x + 1 + eps, y - eps, z - eps),
            (x + 1 + eps, y + 1 + eps, z - eps), (x - eps, y + 1 + eps, z - eps),
            (x - eps, y - eps, z + 1 + eps), (x + 1 + eps, y - eps, z + 1 + eps),
            (x + 1 + eps, y + 1 + eps, z + 1 + eps), (x - eps, y + 1 + eps, z + 1 + eps),
        )
        sy, cy = math.sin(player.yaw), math.cos(player.yaw)
        sp, cp = math.sin(player.pitch), math.cos(player.pitch)
        cam = player.eye()
        projected = []
        for px, py, pz in corners:
            dx, dy, dz = px - cam[0], py - cam[1], pz - cam[2]
            x1 = dx * cy - dz * sy
            z1 = dx * sy + dz * cy
            y1 = dy * cp - z1 * sp
            z2 = dy * sp + z1 * cp
            projected.append(self.project((x1, y1, z2)) if z2 >= NEAR_PLANE else None)
        for a, b in ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)):
            if projected[a] and projected[b]:
                pygame.draw.line(self.scene, (245, 250, 255), projected[a], projected[b], 2)

    def draw_hud(self, selected_index, fps, player, debug, world: IndevLevel):
        cx, cy = self.width // 2, self.height // 2
        pygame.draw.line(self.scene, (18, 20, 22), (cx - 7, cy), (cx + 7, cy), 3)
        pygame.draw.line(self.scene, (18, 20, 22), (cx, cy - 7), (cx, cy + 7), 3)
        pygame.draw.line(self.scene, (245, 247, 250), (cx - 6, cy), (cx + 6, cy), 1)
        pygame.draw.line(self.scene, (245, 247, 250), (cx, cy - 6), (cx, cy + 6), 1)
        slot = 38
        total = len(HOTBAR) * slot + 8
        x0, y0 = (self.width - total) // 2, self.height - 48
        pygame.draw.rect(self.scene, (22, 25, 28), (x0, y0, total, 44), border_radius=4)
        for i, block in enumerate(HOTBAR):
            rect = pygame.Rect(x0 + 4 + i * slot, y0 + 4, 36, 36)
            color = (237, 240, 244) if i == selected_index else (88, 95, 101)
            pygame.draw.rect(self.scene, color, rect, 2, border_radius=2)
            self.scene.blit(self.icons[block], (rect.x + 2, rect.y + 2))
            self.scene.blit(self.small_font.render(str(i + 1), True, (0, 0, 0)), (rect.x + 3, rect.y + 2))
            self.scene.blit(self.small_font.render(str(i + 1), True, (255, 255, 255)), (rect.x + 2, rect.y + 1))
        name = BLOCK_NAMES[HOTBAR[selected_index]]
        ni = self.font.render(name, True, (255, 255, 255))
        self.scene.blit(self.font.render(name, True, (0, 0, 0)), (self.width // 2 - ni.get_width() // 2 + 1, y0 - 18))
        self.scene.blit(ni, (self.width // 2 - ni.get_width() // 2, y0 - 19))
        if debug:
            lines = (
                "FPS %.1f  faces %d" % (fps, self.faces_drawn),
                "XYZ %.1f / %.1f / %.1f" % (player.pos.x, player.pos.y, player.pos.z),
                "day %.2f  light %.2f  %s" % (world.day_time, world.daylight(), EDITION),
            )
            for i, line in enumerate(lines):
                self.scene.blit(self.small_font.render(line, True, (255, 255, 0)), (8, 8 + i * 14))


def draw_text_centered(surf, font, text, cx, y, color=(255, 255, 255)):
    img = font.render(text, True, color)
    shadow = font.render(text, True, (0, 0, 0))
    x = cx - img.get_width() // 2
    surf.blit(shadow, (x + 2, y + 2))
    surf.blit(img, (x, y))


def draw_motd_box(surf, font, text, cx, cy):
    label = text if text.strip() else random_motd()
    img = font.render(label, True, (255, 255, 0))
    bw = max(160, img.get_width() + 28)
    bh = img.get_height() + 16
    rect = pygame.Rect(cx - bw // 2, cy - bh // 2, bw, bh)
    pygame.draw.rect(surf, (0, 0, 0), rect.inflate(4, 4))
    pygame.draw.rect(surf, (50, 45, 10), rect)
    pygame.draw.rect(surf, (255, 220, 0), rect, 2)
    surf.blit(font.render(label, True, (0, 0, 0)), (rect.centerx - img.get_width() // 2 + 1, rect.centery - img.get_height() // 2 + 1))
    surf.blit(img, (rect.centerx - img.get_width() // 2, rect.centery - img.get_height() // 2))


def button_rect(win_w, cy, bw=220, bh=30):
    return pygame.Rect((win_w - bw) // 2, cy, bw, bh)


def draw_button(surf, font, rect, label, hover=False):
    base = (140, 140, 140) if hover else (110, 110, 110)
    pygame.draw.rect(surf, (0, 0, 0), rect.inflate(2, 2))
    pygame.draw.rect(surf, base, rect)
    pygame.draw.rect(surf, (255, 255, 255), rect, 1)
    text = label if label.strip() else "Button"
    img = font.render(text, True, (255, 255, 255))
    surf.blit(font.render(text, True, (0, 0, 0)), (rect.centerx - img.get_width() // 2 + 1, rect.centery - img.get_height() // 2 + 1))
    surf.blit(img, (rect.centerx - img.get_width() // 2, rect.centery - img.get_height() // 2))


def make_dirt_bg(w, h):
    s = pygame.Surface((w, h))
    for y in range(0, h, 16):
        for x in range(0, w, 16):
            n = hash2(x // 16, y // 16, 11)
            c = int(95 + n * 35)
            pygame.draw.rect(s, (c, int(c * 0.68), int(c * 0.4)), (x, y, 16, 16))
    dark = pygame.Surface((w, h), pygame.SRCALPHA)
    dark.fill((0, 0, 0, 110))
    s.blit(dark, (0, 0))
    return s


def run_title_menu(win, clock, fonts) -> str:
    font, big, logo = fonts
    w, h = win.get_size()
    bg = make_dirt_bg(w, h)
    buttons = [("Singleplayer", "play"), ("Quit Game", "quit")]
    motd = random_motd()
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)
    while True:
        clock.tick(60)
        mx, my = pygame.mouse.get_pos()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return "quit"
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return "quit"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, (_lab, action) in enumerate(buttons):
                    if button_rect(w, 250 + i * 42).collidepoint(mx, my):
                        return action
        win.blit(bg, (0, 0))
        draw_text_centered(win, logo, LOGO, w // 2, 52, (60, 200, 60))
        draw_text_centered(win, big, EDITION, w // 2, 118, (255, 255, 255))
        draw_motd_box(win, font, motd, w // 2 + 80, 168)
        for i, (lab, _) in enumerate(buttons):
            r = button_rect(w, 250 + i * 42)
            draw_button(win, font, r, lab, hover=r.collidepoint(mx, my))
        draw_text_centered(win, font, "Copyright Mojang AB. Do not distribute!", w // 2, h - 36, (170, 170, 170))
        draw_text_centered(win, font, "Island · Small · Square · FILES=off", w // 2, h - 18, (140, 140, 140))
        pygame.display.flip()


def run_pause_menu(win, clock, fonts) -> str:
    font, big, _logo = fonts
    w, h = win.get_size()
    buttons = [("Back to game", "resume"), ("Generate new level", "new"), ("Quit to title", "quit")]
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)
    while True:
        clock.tick(60)
        mx, my = pygame.mouse.get_pos()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return "quit"
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return "resume"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, (_lab, action) in enumerate(buttons):
                    if button_rect(w, 180 + i * 42).collidepoint(mx, my):
                        return action
        win.blit(overlay, (0, 0))
        title_r = button_rect(w, 130, 340, 34)
        pygame.draw.rect(win, (0, 0, 0), title_r.inflate(2, 2))
        pygame.draw.rect(win, (60, 60, 60), title_r)
        pygame.draw.rect(win, (255, 255, 255), title_r, 1)
        menu_title = "Game menu — Indev"
        t_img = font.render(menu_title, True, (255, 255, 255))
        win.blit(font.render(menu_title, True, (0, 0, 0)), (title_r.centerx - t_img.get_width() // 2 + 1, title_r.centery - t_img.get_height() // 2 + 1))
        win.blit(t_img, (title_r.centerx - t_img.get_width() // 2, title_r.centery - t_img.get_height() // 2))
        for i, (lab, _) in enumerate(buttons):
            r = button_rect(w, 180 + i * 42)
            draw_button(win, font, r, lab, hover=r.collidepoint(mx, my))
        pygame.display.flip()


class Game:
    def __init__(self, seed: int = INDEV_SEED) -> None:
        if pygame is None:
            raise RuntimeError("pygame required: pip install pygame")
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        pygame.init()
        pygame.display.set_caption(TITLE)
        flags = pygame.RESIZABLE | getattr(pygame, "SCALED", 0)
        self.window = pygame.display.set_mode(WINDOW_SIZE, flags)
        self.clock = pygame.time.Clock()
        self.fonts = (
            pygame.font.Font(None, 22),
            pygame.font.Font(None, 32),
            pygame.font.Font(None, 42),
        )
        self.seed = seed
        self.textures = TextureBank()
        self.renderer = SoftwareRenderer(self.textures)
        self.running = True
        self.debug = False
        self.selected_index = 0
        self.fps_smooth = 60.0
        self.world: IndevLevel | None = None
        self.player: Player | None = None

    def _capture(self, on: bool) -> None:
        pygame.event.set_grab(on)
        pygame.mouse.set_visible(not on)
        pygame.mouse.get_rel()

    def new_world(self) -> None:
        progress = Progress(self.window, self.clock, self.fonts)
        progress.set(0.0, "Preparing Indev island", "Generating level")
        self.world = IndevLevel(self.seed)
        self.world.generate(progress)
        progress.set(0.98, "Spawning player", "Loading spawn")
        self.player = Player()
        self.player.respawn(self.world)
        progress.set(1.0, "Done — entering Indev", "Generating level")
        self._capture(True)

    def _mine_or_place(self, place: bool) -> None:
        assert self.world and self.player
        hit, adjacent = raycast(self.world, self.player.eye(), self.player.look_vector(), 6.0)
        if place:
            if hit is None or adjacent is None or self.world.get(adjacent) != AIR:
                return
            self.world.set(adjacent, HOTBAR[self.selected_index])
            if self.player.intersects_voxel(adjacent):
                self.world.set(adjacent, AIR)
        else:
            if hit is not None and self.world.get(hit) != BEDROCK:
                self.world.set(hit, AIR)
        self.world.rebuild_mesh()

    def run(self) -> int:
        while self.running:
            action = run_title_menu(self.window, self.clock, self.fonts)
            if action != "play":
                break
            self.new_world()
            in_game = True
            while in_game and self.running:
                dt = min(self.clock.tick(TARGET_FPS) / 1000.0, 1.0 / 30.0)
                self.fps_smooth = lerp(self.fps_smooth, self.clock.get_fps() or 60.0, 0.08)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        in_game = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            choice = run_pause_menu(self.window, self.clock, self.fonts)
                            if choice == "resume":
                                self._capture(True)
                            elif choice == "new":
                                self.new_world()
                            else:
                                in_game = False
                        elif event.key == pygame.K_F3:
                            self.debug = not self.debug
                        elif event.key == pygame.K_r:
                            assert self.player and self.world
                            self.player.respawn(self.world)
                        elif pygame.K_1 <= event.key <= pygame.K_8:
                            self.selected_index = event.key - pygame.K_1
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:
                            self._mine_or_place(False)
                        elif event.button == 3:
                            self._mine_or_place(True)
                    elif event.type == pygame.MOUSEWHEEL:
                        self.selected_index = (self.selected_index - event.y) % len(HOTBAR)

                if not in_game or not self.running:
                    break

                assert self.world and self.player
                mx, my = pygame.mouse.get_rel()
                self.player.yaw += mx * 0.00245
                self.player.pitch = clamp(self.player.pitch - my * 0.00245, math.radians(-89), math.radians(89))
                keys = pygame.key.get_pressed()
                wish_x = float(keys[pygame.K_d]) - float(keys[pygame.K_a])
                wish_z = float(keys[pygame.K_w]) - float(keys[pygame.K_s])
                self.player.physics_step(
                    self.world,
                    wish_x,
                    wish_z,
                    bool(keys[pygame.K_SPACE]),
                    bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]),
                    dt,
                )
                self.world.tick_day(dt)

                self.renderer.render_world(self.world, self.player)
                hit, _ = raycast(self.world, self.player.eye(), self.player.look_vector(), 6.0)
                self.renderer.draw_selection(self.player, hit)
                self.renderer.draw_hud(self.selected_index, self.fps_smooth, self.player, self.debug, self.world)
                pygame.transform.scale(self.renderer.scene, self.window.get_size(), self.window)
                pygame.display.flip()

        pygame.quit()
        return 0


def self_test() -> int:
    ok = True

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        print(("PASS: " if cond else "FAIL: ") + name)
        ok = ok and cond

    check("no numpy", "numpy" not in sys.modules)
    check("logo", LOGO == "ac's minecraft my take" and TITLE == LOGO)
    check("edition Indev", EDITION == "Minecraft Indev")
    check("finite size", LEVEL_W == 128 and LEVEL_D == 128 and LEVEL_H == 64)
    check("FILES off", FILES is False)

    world = IndevLevel(123)
    world.generate()
    check("has mesh", len(world.mesh) > 100)
    check("bedrock floor", world.get((64, 0, 64)) == BEDROCK)
    check("ocean border", world.get((-1, WATER_LEVEL - 1, 64)) == WATER)
    surface = world.highest_solid(64, 64)
    check("spawn height", 1 <= surface < LEVEL_H)
    hit, adj = raycast(world, (64.5, surface + 5, 64.5), (0, -1, 0), 10)
    check("raycast", hit is not None)
    p = Player()
    p.respawn(world)
    check("spawn in bounds", world.in_bounds(int(p.pos.x), int(p.pos.y), int(p.pos.z)))
    world.day_time = 0.5
    check("noon light", world.daylight() > 0.9)
    world.day_time = 0.0
    check("midnight dark", world.daylight() < 0.3)
    check("no Infdev chunks", not hasattr(world, "chunks") and not hasattr(world, "ensure_around"))

    print("")
    if ok:
        print("ALL TESTS PASSED")
        return 0
    print("SOME TESTS FAILED")
    return 1


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if pygame is None:
        print("Install pygame: python -m pip install pygame")
        return 1
    return Game().run()


if __name__ == "__main__":
    raise SystemExit(main())
