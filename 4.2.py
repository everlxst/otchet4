import pygame
import pygame.midi
import random
import sys
import math
from collections import deque

pygame.init()
pygame.mixer.init()
try:
    pygame.midi.init()
    midi_available = True
except Exception:
    midi_available = False

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Волшебная Музыкальная Раскраска")
clock = pygame.time.Clock()

midi_output = None
if midi_available:
    try:
        midi_output = pygame.midi.Output(pygame.midi.get_default_output_id())
        midi_output.set_instrument(0)
    except Exception:
        midi_output = None

BG_COLOR = (245, 251, 255)
TEXT_COLOR = (67, 97, 238)
SHADOW_COLOR = (210, 220, 230)
CANVAS_BG = (240, 240, 240)
DRAW_BG = (255, 255, 255)
LINE_COLOR = (40, 40, 40)

PALETTE_DATA = [
    ((255, 89, 94), 60),
    ((255, 145, 0), 62),
    ((255, 202, 58), 64),
    ((138, 201, 38), 65),
    ((25, 130, 196), 67),
    ((43, 97, 238), 69),
    ((106, 76, 147), 71),
    ((255, 111, 181), 72),
]

active_color = PALETTE_DATA[2][0]
show_congrats = False
particles = []

NOTE_DURATION_MS = 400
active_notes = []

def play_piano_note(note_number):
    if midi_output:
        try:
            midi_output.note_on(note_number, 100)
            active_notes.append([note_number, pygame.time.get_ticks() + NOTE_DURATION_MS])
        except Exception:
            pass

def update_notes():
    if not midi_output:
        return
    now = pygame.time.get_ticks()
    for entry in active_notes[:]:
        note, off_at = entry
        if now >= off_at:
            try:
                midi_output.note_off(note, 100)
            except Exception:
                pass
            active_notes.remove(entry)

def play_win_fanfare():
    win_notes = [60, 64, 67, 72]
    for i, note in enumerate(win_notes):
        pygame.time.set_timer(pygame.USEREVENT + 10 + i, 160 * (i + 1), loops=1)

canvas_surface = pygame.Surface((800, 550))

def draw_clean_sun(surf):
    surf.fill(CANVAS_BG)
    pygame.draw.circle(surf, DRAW_BG, (400, 275), 120)
    for i in range(8):
        angle = i * (math.pi / 4)
        x2 = 400 + int(160 * math.cos(angle))
        y2 = 275 + int(160 * math.sin(angle))
        pygame.draw.line(surf, LINE_COLOR, (400, 275), (x2, y2), width=16)
    pygame.draw.circle(surf, CANVAS_BG, (400, 275), 90)
    pygame.draw.circle(surf, DRAW_BG, (400, 275), 88)
    pygame.draw.circle(surf, LINE_COLOR, (400, 275), 90, width=6)
    for i in range(8):
        angle = i * (math.pi / 4)
        x2 = 400 + int(160 * math.cos(angle))
        y2 = 275 + int(160 * math.sin(angle))
        pygame.draw.circle(surf, LINE_COLOR, (x2, y2), 8)

def draw_clean_house(surf):
    surf.fill(CANVAS_BG)
    pygame.draw.rect(surf, DRAW_BG, (283, 263, 234, 194))
    pygame.draw.polygon(surf, DRAW_BG, [(400, 123), (243, 257), (557, 257)])
    pygame.draw.rect(surf, LINE_COLOR, (280, 260, 240, 200), width=6)
    pygame.draw.polygon(surf, LINE_COLOR, [(400, 120), (240, 260), (560, 260)], width=6)
    pygame.draw.rect(surf, LINE_COLOR, (350, 310, 100, 90), width=5)
    pygame.draw.line(surf, LINE_COLOR, (400, 310), (400, 400), width=4)
    pygame.draw.line(surf, LINE_COLOR, (350, 350), (450, 350), width=4)

def draw_clean_car(surf):
    surf.fill(CANVAS_BG)

    base_y = 340
    body_pts = [
        (150, base_y),
        (220, base_y - 140),
        (580, base_y - 140),
        (650, base_y)
    ]
    pygame.draw.polygon(surf, DRAW_BG, body_pts)
    pygame.draw.lines(surf, LINE_COLOR, False, body_pts, 6)
    pygame.draw.line(surf, LINE_COLOR, (150, base_y), (650, base_y), width=6)

    # === ОКНА (БОЛЬШИЕ ТРАПЕЦИИ) ===
    win1_pts = [(260, 300), (385, 300), (365, 230), (280, 230)]
    pygame.draw.polygon(surf, DRAW_BG, win1_pts)
    pygame.draw.lines(surf, LINE_COLOR, True, win1_pts, 5)

    win2_pts = [(415, 300), (540, 300), (520, 230), (435, 230)]
    pygame.draw.polygon(surf, DRAW_BG, win2_pts)
    pygame.draw.lines(surf, LINE_COLOR, True, win2_pts, 5)

    pygame.draw.line(surf, LINE_COLOR, (400, 230), (400, 300), 5)

    # === КОЛЁСА ===
    for cx in (260, 540):
        pygame.draw.circle(surf, LINE_COLOR, (cx, 370), 44)
        pygame.draw.circle(surf, DRAW_BG, (cx, 370), 36)
        pygame.draw.circle(surf, LINE_COLOR, (cx, 370), 16)
        pygame.draw.circle(surf, DRAW_BG, (cx, 370), 12)

    pygame.draw.circle(surf, LINE_COLOR, (150, base_y), 8)
    pygame.draw.circle(surf, LINE_COLOR, (650, base_y), 8)
    pygame.draw.rect(surf, LINE_COLOR, (395, 300, 12, 6), border_radius=2)

pic_drawers = {0: draw_clean_sun, 1: draw_clean_house, 2: draw_clean_car}
current_pic_id = 2
pic_drawers[current_pic_id](canvas_surface)

def flood_fill(surface, start_pos, fill_color):
    width, height = surface.get_size()
    target_color = surface.get_at(start_pos)[:3]

    if target_color == fill_color or target_color == LINE_COLOR or target_color == CANVAS_BG:
        return False
    if target_color != DRAW_BG:
        return False

    surface.lock()
    queue = deque([start_pos])
    filled = 0
    while queue:
        x, y = queue.popleft()
        if surface.get_at((x, y))[:3] != target_color:
            continue
        surface.set_at((x, y), fill_color)
        filled += 1
        if x > 0: queue.append((x - 1, y))
        if x < width - 1: queue.append((x + 1, y))
        if y > 0: queue.append((x, y - 1))
        if y < height - 1: queue.append((x, y + 1))
    surface.unlock()
    return filled > 0

def check_canvas_complete(surf):
    w, h = surf.get_size()
    for x in range(0, w, 4):
        for y in range(0, h, 4):
            if surf.get_at((x, y))[:3] == DRAW_BG:
                return False
    return True

class PaintBucket:
    def __init__(self, x, y, radius, color, note):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.note = note

    def draw(self, surface):
        if active_color == self.color:
            pygame.draw.circle(surface, self.color, (self.x, self.y), self.radius + 8, width=4)
        pygame.draw.circle(surface, SHADOW_COLOR, (self.x + 3, self.y + 5), self.radius)
        pygame.draw.circle(surface, self.color, (self.x, self.y), self.radius)
        pygame.draw.circle(surface, (255, 255, 255), (self.x, self.y), self.radius, width=3)

    def collide(self, pos):
        return (pos[0] - self.x) ** 2 + (pos[1] - self.y) ** 2 <= self.radius ** 2

class PictureButton:
    def __init__(self, x, y, width, height, text, pic_id):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.pic_id = pic_id

    def draw(self, surface, current_id):
        is_active = (current_id == self.pic_id)
        bg_col = (67, 97, 238) if is_active else (255, 255, 255)
        text_col = (255, 255, 255) if is_active else (67, 97, 238)
        pygame.draw.rect(surface, bg_col, self.rect, border_radius=12)
        pygame.draw.rect(surface, (67, 97, 238), self.rect, width=2, border_radius=12)
        font = pygame.font.SysFont("Comic Sans MS", 18, bold=True)
        txt = font.render(self.text, True, text_col)
        surface.blit(txt, txt.get_rect(center=self.rect.center))

buckets = []
for i, (color, note) in enumerate(PALETTE_DATA):
    bx = 875 if i % 2 == 0 else 935
    by = 140 + (i // 2) * 115
    buckets.append(PaintBucket(bx, by, 25, color, note))

menu_buttons = [
    PictureButton(40, 25, 130, 45, "Солнышко", 0),
    PictureButton(195, 25, 130, 45, "Домик", 1),
    PictureButton(350, 25, 130, 45, "Машинка", 2),
]

ok_btn_rect = pygame.Rect(380, 420, 240, 60)

running = True
while running:
    screen.fill(BG_COLOR)
    update_notes()

    for btn in menu_buttons:
        btn.draw(screen, current_pic_id)

    screen.blit(canvas_surface, (30, 95))
    pygame.draw.rect(screen, (67, 97, 238), (30, 95, 800, 550), width=4, border_radius=5)

    for bucket in buckets:
        bucket.draw(screen)

    for p in particles[:]:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["radius"] -= 0.15
        p["life"] -= 0.03
        if p["radius"] > 0 and p["life"] > 0:
            alpha = int(max(0, min(255, p["life"] * 255)))
            r = max(1, int(p["radius"]))
            p_surface = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(p_surface, p["color"] + (alpha,), (r, r), r)
            screen.blit(p_surface, (int(p["x"] - r), int(p["y"] - r)))
        else:
            particles.remove(p)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            continue

        if pygame.USEREVENT + 10 <= event.type <= pygame.USEREVENT + 13:
            idx = event.type - (pygame.USEREVENT + 10)
            play_piano_note([60, 64, 67, 72][idx])
            continue

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if show_congrats:
                if ok_btn_rect.collidepoint(event.pos):
                    show_congrats = False
                    particles.clear()
                    pic_drawers[current_pic_id](canvas_surface)
                continue

            clicked_menu = False
            for btn in menu_buttons:
                if btn.rect.collidepoint(event.pos):
                    current_pic_id = btn.pic_id
                    pic_drawers[current_pic_id](canvas_surface)
                    particles.clear()
                    clicked_menu = True
                    break
            if clicked_menu:
                continue

            clicked_bucket = False
            for bucket in buckets:
                if bucket.collide(event.pos):
                    active_color = bucket.color
                    play_piano_note(bucket.note)
                    clicked_bucket = True
                    break
            if clicked_bucket:
                continue

            canvas_x = event.pos[0] - 30
            canvas_y = event.pos[1] - 95
            if 0 <= canvas_x < 800 and 0 <= canvas_y < 550:
                if flood_fill(canvas_surface, (canvas_x, canvas_y), active_color):
                    chosen_note = 60
                    for b in buckets:
                        if b.color == active_color:
                            chosen_note = b.note
                    play_piano_note(chosen_note)

                    for _ in range(15):
                        particles.append({
                            "x": float(event.pos[0]),
                            "y": float(event.pos[1]),
                            "vx": random.uniform(-4, 4),
                            "vy": random.uniform(-4, 4),
                            "radius": float(random.randint(5, 12)),
                            "color": active_color,
                            "life": 1.0,
                        })

                    if check_canvas_complete(canvas_surface):
                        show_congrats = True
                        play_win_fanfare()

    if show_congrats:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 85))
        screen.blit(overlay, (0, 0))

        box_rect = pygame.Rect(230, 200, 540, 300)
        pygame.draw.rect(screen, SHADOW_COLOR, box_rect.move(6, 8), border_radius=40)
        pygame.draw.rect(screen, (255, 255, 255), box_rect, border_radius=40)
        pygame.draw.rect(screen, (138, 201, 38), box_rect, width=5, border_radius=40)

        font_big = pygame.font.SysFont("Comic Sans MS", 34, bold=True)
        font_small = pygame.font.SysFont("Comic Sans MS", 22, bold=True)

        t1 = font_big.render("Ура! Ты молодец!", True, (255, 89, 94))
        t2 = font_small.render("Какая красивая картинка получилась!", True, (67, 97, 238))
        screen.blit(t1, t1.get_rect(centerx=box_rect.centerx, y=box_rect.y + 55))
        screen.blit(t2, t2.get_rect(centerx=box_rect.centerx, y=box_rect.y + 130))

        pygame.draw.rect(screen, SHADOW_COLOR, ok_btn_rect.move(2, 3), border_radius=15)
        pygame.draw.rect(screen, (138, 201, 38), ok_btn_rect, border_radius=15)
        pygame.draw.rect(screen, (255, 255, 255), ok_btn_rect, width=2, border_radius=15)
        btn_txt = font_small.render("Играть еще", True, (255, 255, 255))
        screen.blit(btn_txt, btn_txt.get_rect(center=ok_btn_rect.center))

    pygame.display.flip()
    clock.tick(60)

if midi_output:
    try:
        del midi_output
    except Exception:
        pass
if midi_available:
    pygame.midi.quit()
pygame.quit()
sys.exit()