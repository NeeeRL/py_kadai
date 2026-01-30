import pygame as pg
import sys, os, random, time
from typing import List, Tuple, Optional
import math

from pygame.draw import rect

pg.init()

# ---------------- フォント解決 ----------------
def get_jp_font(size: int) -> pg.font.Font:
    bundle = os.path.join("assets", "fonts", "NotoSansJP-VariableFont_wght.ttf")
    if os.path.exists(bundle):
        return pg.font.Font(bundle, size)
    candidates = [
        "Noto Sans CJK JP", "Noto Sans JP",
        "Yu Gothic UI", "Yu Gothic",
        "Meiryo", "MS Gothic",
        "Hiragino Sans", "Hiragino Kaku Gothic ProN",
    ]
    for name in candidates:
        path = pg.font.match_font(name)
        if path:
            return pg.font.Font(path, size)
    return pg.font.SysFont(None, size)

# ---------------- パラメータ(可変ではなくなったぜ) ----------------
FRAME_DELAY = 0.5
ENEMY_DELAY = 1.0

partylist = [
    {"name":"青龍","element":"風","hp":150,"max_hp":150,"ap":15,"dp":10,"skills":"竜巻"},
    {"name":"朱雀","element":"火","hp":150,"max_hp":150,"ap":25,"dp":10,"skills":"火を纏う"},
    {"name":"白虎","element":"土","hp":150,"max_hp":150,"ap":20,"dp":5,"skills":"引っ掻く"},
    {"name":"玄武","element":"水","hp":150,"max_hp":150,"ap":20,"dp":15,"skills":"鉄壁"},
    {"name":"青龍","element":"風","hp":150,"max_hp":150,"ap":15,"dp":10,"skills":"竜巻"},
    {"name":"朱雀","element":"火","hp":150,"max_hp":150,"ap":25,"dp":10,"skills":"火を纏う"},
]

# もしかしたら、elemを配列として渡した方が後々幸せかも(やらんけど) <- ごめん何言ってんの
SKILLS = {
    "竜巻": {
        "effect": "5ターンの間、風属性のダメージ5倍",
        "ct": 5,
        "buff" : {
            "num": 5, "elem": "風", "turn": 5
        }
    },
    "火を纏う": {
        "effect": "火・命ジェムをランダムに合計10個生成",
        "ct": 3,
        "makegem": {
            # ごめんここか
            "make": 10, "elem": ["火", "命"]
        }
    },
    "引っ掻く": {
        "effect": "相手の場のモンスターに最大hp50%ダメージ",
        "ct": 7,
        "attack" : {
            # 0.5 -> 50%
            "num": 0.5
        }
    },
    "鉄壁": {
        "effect": "1ターンの間、ダメージ90%カット(重複しない)",
        "ct": 4,
        "defence" : {
            "num": 0.9,
        }
    },
}

info = pg.display.Info()
screen_w = info.current_w
screen_h = info.current_h
WIN_H = screen_h * 0.92
WIN_W = int(WIN_H * 9/16)

os.environ['SDL_VIDEO_CENTERED'] = '1'

usable_width = WIN_W * 0.90

FIELD_Y = int(WIN_H * 0.55)
SLOT_PAD = 8
SLOT_W = int((usable_width - (SLOT_PAD * (6 - 1))) / 6)
puzzle_total_width = (SLOT_W * 6) + (SLOT_PAD * (6 - 1))
LEFT_MARGIN = (WIN_W - puzzle_total_width) // 2

# ドラッグ演出
DRAG_SCALE = 1.18
DRAG_SHADOW = (0, 0, 0, 90)

# ---------------- 定義 ----------------
ELEMENT_SYMBOLS = {"火": "$", "水": "~", "風": "@", "土": "#", "命": "&", "無": " "}
COLOR_RGB = {
    "火": (230, 70, 70), "水": (70, 150, 230), "風": (90, 200, 120),
    "土": (200, 150, 80), "命": (220, 90, 200), "無": (160,160,160)
}
GEMS = ["火", "水", "風", "土", "命"]
SLOTS = [chr(ord('A')+i) for i in range(14)]

# ---------------- 画像 ----------------
def load_monster_image(name: str) -> pg.Surface:
    m = {
        "スライム":"slime.png", "ゴブリン":"goblin.png",
        "オオコウモリ":"bat.png", "ウェアウルフ":"werewolf.png",
        "ドラゴン":"dragon.png", 
        "青龍":"seiryu.png", "朱雀":"suzaku.png", 
        "白虎":"byakko.png", "玄武":"genbu.png"
    }
    fn = m.get(name)
    if fn:
        path = os.path.join("assets","monsters",fn)
        if os.path.exists(path):
            img = pg.image.load(path).convert_alpha()
            return pg.transform.smoothscale(img, (256,256))
    surf = pg.Surface((256,256), pg.SRCALPHA); surf.fill((60,60,60,200))
    return surf

# ---------------- HPバー ----------------
def hp_bar_surf(current: int, max_hp: int, w: int, h: int) -> pg.Surface:
    ratio = max(0, min(1, current / max_hp if max_hp > 0 else 0))
    bar_w = w
    fill_w = int(bar_w * ratio)

    if ratio >= 0.6: col = (40, 200, 90)
    elif ratio >= 0.3: col = (230, 200, 60)
    else: col = (230, 70, 70)

    surf = pg.Surface((w, h), pg.SRCALPHA)
    bg = pg.Surface((bar_w, h), pg.SRCALPHA)
    bg.fill((0, 0, 0, 120))
    surf.blit(bg, (0, 0))
    fg = pg.Surface((fill_w, h), pg.SRCALPHA)
    fg.fill(col)
    surf.blit(fg, (0, 0))
    return surf

# ---------------- 盤面ロジック ----------------
def init_field()->List[List[str]]:
    return [[random.choice(GEMS) for i in range(6)] for j in range(5)]

def get_all_runs(line: List[str]) -> List[Tuple[int, int]]:
    runs = []
    n = len(line)
    i = 0
    while i < n:
        j = i + 1
        while j < n and line[j] == line[i]:
            j += 1
        
        length = j - i
        # 3つ以上、かつ「無」以外ならマッチとみなす
        if length >= 3 and line[i] in GEMS:
            runs.append((i, length))
        
        i = j
    return runs

# 盤面全体スキャン
def scan_grid(grid: List[List[str]]) -> List[dict[str, int]]:
    matches = []
    rows = len(grid)
    cols = len(grid[0])

    # 横方向（行）を捜査
    for y in range(rows):
        runs = get_all_runs(grid[y])
        for start_x, length in runs:
            matches.append({
                "type": "yoko",
                "y": y,
                "x": start_x,
                "length": length
            })

    # 縦方向（列）を捜査
    for x in range(cols):
        col_list = [grid[y][x] for y in range(rows)]
        runs = get_all_runs(col_list)
        for start_y, length in runs:
            matches.append({
                "type": "tate",
                "x": x,
                "y": start_y,
                "length": length
            })

    return matches

# 鎌足
def get_clusters(field: List[List[str]], matches: List[dict]) -> List[dict]:
    matched_coords = set()
    for m in matches:
        if m["type"] == "yoko":
            for k in range(m["x"], m["x"] + m["length"]):
                matched_coords.add((k, m["y"]))
        else: # tate
            for k in range(m["y"], m["y"] + m["length"]):
                matched_coords.add((m["x"], k))

    clusters = []
    visited = set()

    for cx, cy in matched_coords:
        if (cx, cy) in visited:
            continue

        color = field[cy][cx]
        gem_group = []
        
        stack = [(cx, cy)]
        visited.add((cx, cy))

        while stack:
            curr_x, curr_y = stack.pop()
            gem_group.append((curr_x, curr_y))

            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                nx, ny = curr_x + dx, curr_y + dy
                
                if (nx, ny) in matched_coords and (nx, ny) not in visited:
                    if field[ny][nx] == color:
                        visited.add((nx, ny))
                        stack.append((nx, ny))

        clusters.append({
            "color": color,
            "count": len(gem_group),
            "coords": gem_group
        })

    return clusters

def animation_fall(screen, field, font, sukill_turn, party, enemy):
    rows = len(field)
    cols = len(field[0])
    
    # --- どこからどこへ動くかを計算する ---
    moves = []
    
    for x in range(cols):
        old_gems = []
        for y in range(rows):
            if field[y][x] != "無":
                old_gems.append({
                    "elem": field[y][x],
                    "original_y": y
                })
        
        missing_count = rows - len(old_gems)
        new_gems_list = [random.choice(GEMS) for _ in range(missing_count)]
        
        write_y = rows - 1
        
        for item in reversed(old_gems):
            elem = item["elem"]
            org_y = item["original_y"]
            dest_y = write_y
            
            # 座標計算
            px = LEFT_MARGIN + x * (SLOT_W + SLOT_PAD)
            start_px = FIELD_Y + org_y * (SLOT_W + SLOT_PAD)
            end_px   = FIELD_Y + dest_y * (SLOT_W + SLOT_PAD)
            
            moves.append({
                "elem": elem, "x": px,
                "start_y": start_px, "end_y": end_px
            })
            
            field[dest_y][x] = elem
            write_y -= 1
            
        for i, elem in enumerate(reversed(new_gems_list)):
            dest_y = write_y
            
            px = LEFT_MARGIN + x * (SLOT_W + SLOT_PAD)
            end_px   = FIELD_Y + dest_y * (SLOT_W + SLOT_PAD)
            start_px = FIELD_Y + (dest_y - missing_count - 1) * (SLOT_W + SLOT_PAD) - 20
            
            moves.append({
                "elem": elem, "x": px,
                "start_y": start_px, "end_y": end_px
            })
            
            field[dest_y][x] = elem
            write_y -= 1

    # --- アニメーションループ ---
    duration = 0.45
    start_time = time.time()
    
    while True:
        now = time.time()
        progress = (now - start_time) / duration
        if progress > 1.0: progress = 1.0
        
        t = progress * progress
        
        pg.event.pump() # フリーズ防止
        
        screen.fill((22, 22, 28))
        draw_top(screen, enemy, party, font, sukill_turn )


        for y in range(rows):
            for x in range(cols):
                rect_x = LEFT_MARGIN + x * (SLOT_W + SLOT_PAD)
                rect_y = FIELD_Y + y * (SLOT_W + SLOT_PAD)
                pg.draw.rect(screen, (35, 35, 40), (rect_x, rect_y, SLOT_W, SLOT_W), border_radius=8)

        for m in moves:
            current_y = m["start_y"] + (m["end_y"] - m["start_y"]) * t
            draw_gem_at(screen, m["elem"], int(m["x"] + SLOT_W//2), int(current_y + SLOT_W//2), font=font)

        draw_message(screen, "落下中...", font)
        pg.display.flip()

        if progress >= 1.0:
            time.sleep(0.5)
            break

        # ここに遅延入れるとぬるぬるしすぎなくなる



# ---------------- ダメージ/回復 ----------------
def jitter(v:float, r:float=0.10)->int:
    return max(1, int(v*random.uniform(1-r,1+r)))

def attr_coeff(att,defe):
    cyc={"火":"風","風":"土","土":"水","水":"火"}
    if att in cyc and cyc[att]==defe: return 2.0
    if defe in cyc and cyc[defe]==att: return 0.5
    return 1.0

def party_attack_from_gems(elem:str, run_len:int, combo:int, party:dict, monster:dict, buffs)->int:
    combo_coeff = 1.5 ** ((run_len - 3) + combo)
    if elem=="命":
        heal=jitter(20*combo_coeff); party["hp"]=min(party["max_hp"], party["hp"]+heal); return 0
    ally = next((a for a in party["allies"] if a["element"]==elem), None)
    if not ally: return 0
    base=max(1, ally["ap"] -monster["dp"])
    print(f"elem: {elem} buffs: {buffs}")
    dmg=jitter(base*attr_coeff(elem,monster["element"])*combo_coeff)*buffs
    monster["hp"]=max(0,monster["hp"]-dmg); return dmg

def enemy_attack(party:dict, monster:dict, def_cut)->int:
    base=max(1, monster["ap"]-party["dp"])
    dmg=round(jitter(base)*(1 - def_cut)); party["hp"]=max(0,party["hp"]-dmg); return dmg

# ---------------- 描画ユーティリティ ----------------
def slot_rect(i: int) -> pg.Rect:
    tx = LEFT_MARGIN + i * (SLOT_W + SLOT_PAD)
    return pg.Rect(tx, FIELD_Y, SLOT_W, SLOT_W)

def draw_gem_at(screen, elem: str, x: int, y: int, scale=1.0, with_shadow=False, font=None):
    r = int((SLOT_W//2 - 10) * scale)
    if with_shadow:
        shadow = pg.Surface((r*2+6, r*2+6), pg.SRCALPHA)
        pg.draw.circle(shadow, DRAG_SHADOW, (r+3, r+3), r+3)
        screen.blit(shadow, (x-r-3, y-r-3))
    
    color = COLOR_RGB[elem]
    pg.draw.circle(screen, color, (x, y), r)
    sym = ELEMENT_SYMBOLS[elem]
    f = font if font else get_jp_font(int(26*scale))
    s = f.render(sym, True, (0,0,0))
    screen.blit(s, (x - s.get_width()//2, y - s.get_height()//2))

def draw_field(screen, field: list[list[str]], font, animation_list,
               hover_pos: Optional[tuple[int, int]] = None,
               drag_src: Optional[tuple[int, int]] = None, 
               drag_elem: Optional[str] = None):

    rows = len(field)
    cols = len(field[0])


    for y in range(rows):
        for x in range(cols):
            elem = field[y][x]
            rect_x = LEFT_MARGIN + x * (SLOT_W + SLOT_PAD)
            rect_y = FIELD_Y + y * (SLOT_W + SLOT_PAD)
            rect = pg.Rect(rect_x, rect_y, SLOT_W, SLOT_W)

            scale = 1.0

            for anim in animation_list:
                if anim["x"] == x and anim["y"] == y:
                    now = time.time()
                    elapsed = now - anim["start_time"]
                    progress = elapsed / anim["duration"]

                    if 0 <= progress <= 1.0:
                        # sin(0) -> 0, sin(π/2) -> 1, sin(π) -> 0
                        # これで 1.0 -> 1.5 -> 1.0 という動きになる(choi kaeta kara uso tsuteru)
                        wave = math.sin(progress * math.pi)
                        scale = 1.0 + (0.6 * wave) 
                    break

            is_hover = (hover_pos == (x, y))
            base_color = (60, 60, 80) if is_hover else (35, 35, 40)
            pg.draw.rect(screen, base_color, rect, border_radius=8)

            if drag_src == (x, y):
                continue

            if elem and elem != "無": 
                cx, cy = rect.center
                color = COLOR_RGB.get(elem, (100, 100, 100)) 
                pg.draw.circle(screen, color, (cx, cy), SLOT_W // 2 - 10)
                
                sym = ELEMENT_SYMBOLS.get(elem, "?")
                s = font.render(sym, True, (0, 0, 0))
                screen.blit(s, (cx - s.get_width() // 2, cy - s.get_height() // 2))

                draw_gem_at(screen, elem, cx, cy, scale=scale, font=font)

    if drag_elem is not None:
        mx, my = pg.mouse.get_pos()
        draw_gem_at(screen, drag_elem, mx, my - 4, scale=DRAG_SCALE, with_shadow=True, font=font)

def draw_heart_icon(screen, x, y, size=20, color=(255, 100, 100)):
    r = size // 4
    # 左の丸
    pg.draw.circle(screen, color, (x - r, y - r), r)
    # 右の丸
    pg.draw.circle(screen, color, (x + r, y - r), r)
    # 下の逆三角形
    triangle_points = [
        (x - size//2, y - r), # 左上
        (x + size//2, y - r), # 右上
        (x, y + size//2)      # 下の頂点
    ]
    pg.draw.polygon(screen, color, triangle_points)

def draw_members(screen, partylist, sukill_turn) -> list:
    party_buttons = []

    # スキルデータctと、sukill_turnのindexによってスキル発動できるなら背景を白くする

    for i, member in enumerate(partylist):
        skillname = member['skills']
        skill_data = SKILLS.get(skillname)
        if skill_data is None:
            print("エラー: スキルは見つかりません")
            continue

        ct = skill_data["ct"]


        rect_x = LEFT_MARGIN + i * (SLOT_W + SLOT_PAD)
        rect_y = WIN_H * 0.4

        elem = member["element"]
        # 黒
        border_color = COLOR_RGB[elem]
        bg_color = (35, 35, 40)

        if sukill_turn[i] >= ct:
            t = time.time() * 5
            wave = (math.sin(t) + 1) / 2  # 0.0 〜 1.0 に正規化
            
            color_min = (35, 35, 40)
            color_max = (60, 60, 80)

            speed = 4.0
            t = time.time()
            wave = (math.sin(t * speed) + 1) / 2

            r = color_min[0] + (color_max[0] - color_min[0]) * wave
            g = color_min[1] + (color_max[1] - color_min[1]) * wave
            b = color_min[2] + (color_max[2] - color_min[2]) * wave

            bg_color = (int(r), int(g), int(b))

            rect_y -= 5


        rect = pg.Rect(rect_x, rect_y, SLOT_W, SLOT_W)
        
        party_buttons.append({
            "rect": rect,
            "data": partylist[i]
        })

        pg.draw.rect(screen, bg_color, rect, border_radius=8)
        pg.draw.rect(screen, border_color, rect, width=4, border_radius=8)

        img = member["display_image"]

        img_rect = img.get_rect(center=rect.center)
        screen.blit(img, img_rect)

    return party_buttons

def draw_unit_status(screen, cx, y, current_hp, max_hp, font, heart_color):
    bar_w = int(WIN_W * 0.81)
    bar_h = int(WIN_H * 0.02)
    icon_size = 20
    gap = 8
    padding = 6

    content_width = icon_size + gap + bar_w
    
    start_x = cx - (content_width // 2)

    border_rect = pg.Rect(
        start_x - padding, 
        y - padding, 
        content_width + padding * 2, 
        max(icon_size, bar_h) + padding * 2
    )
    pg.draw.rect(screen, (150, 150, 180), border_rect, width=1, border_radius=4)

    heart_center_x = start_x + (icon_size // 2)
    heart_center_y = y + (max(icon_size, bar_h) // 2)
    draw_heart_icon(screen, heart_center_x, heart_center_y, size=icon_size, color=heart_color)

    bar_x = start_x + icon_size + gap
    bar_y = y + (max(icon_size, bar_h) - bar_h) // 2
    
    hp_surf = hp_bar_surf(current_hp, max_hp, bar_w, bar_h)
    screen.blit(hp_surf, (bar_x, bar_y))

    text = f"{int(current_hp)}/{max_hp}"
    t_surf = font.render(text, True, (255, 255, 255))
    
    # 右寄せ計算
    text_x = (bar_x + bar_w) - t_surf.get_width()
    text_y = bar_y - 10

    # 文字が見えやすいように少し影をつける（オプション）
    shadow = font.render(text, True, (0, 0, 0))
    screen.blit(shadow, (text_x + 1, text_y + 1))
    
    screen.blit(t_surf, (text_x, text_y))

def draw_top(screen, enemy, party, font, sukill_turn ) -> list:
    cx = WIN_W // 2

    # --- 敵画像 ---
    img = enemy["display_image"]
    screen.blit(img, (cx - 128, 10))

    # --- 敵の名前 ---
    name = font.render(enemy["name"], True, (255, 255, 255))
    name_rect = name.get_rect(center=(cx, 250))
    screen.blit(name, name_rect)

    # --- 敵のステータス ---
    draw_unit_status(
        screen, cx, 280, 
        enemy["hp"], enemy["max_hp"], 
        font, (200, 100, 255)
    )

    # --- 味方のステータス ---
    draw_unit_status(
        screen, cx, int(WIN_H * 0.5), 
        party["hp"], party["max_hp"], 
        font, (255, 80, 80)
    )

    
    # pa-thi-you no atari hantei wo kaerichi toshite kaesu youni suru
    party_buttons = draw_members(screen, partylist, sukill_turn)
    
    return party_buttons

def draw_message(screen, text, font):
    surf = font.render(text, True, (230,230,230))
    screen.blit(surf,(40,460))

def keep_aspect(img, max_w, max_h):
    w, h = img.get_size()
    
    scale_w = max_w / w
    scale_h = max_h / h
    
    scale = min(scale_w, scale_h)
    
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    return pg.transform.smoothscale(img, (new_w, new_h))

# ---------------- skills ----------------
def skills(target_data, field, buffs, gem_animations, enemy, def_cut) -> tuple[str,int]:
    name = target_data['skills']
    skill_data = SKILLS.get(name)

    defc = def_cut

    message = ""

    if not skill_data:
        return "スキルデータが見つかりません", defc
    if "makegem" in skill_data:
        message = makegem(skill_data, field, gem_animations)
    elif "buff" in skill_data:
        message = buff_party(skill_data, buffs)
    elif "attack" in skill_data:
        message = AttackSkill(skill_data, enemy)
    elif "defence" in skill_data:
        message, defc = defence(skill_data, def_cut)
    # 念の為
    else:
        return f"{skill_data['effect']}", defc
    
    return message, defc

# def_cutどうやって返そう...
def defence(skill, def_cut) -> tuple[str, int]:
    message = str(skill['effect'])
    ef = skill["defence"]
    num = ef["num"]

    def_cut = num

    return message, def_cut



def AttackSkill(skill, enemy) -> str:
    message = str(skill['effect'])
    ef = skill["attack"]
    num = ef["num"]
    damage = int(enemy["max_hp"] * num)

    enemy["hp"] = max(0, enemy["hp"] - damage)

    return message

def buff_party(skill, buffs) -> str:
    ef = skill["buff"]
    target_gem = ef["elem"]
    num = ef["num"]
    turn = ef["turn"]
    message = str(skill['effect'])

    buffs[target_gem].append({'count': turn, 'num': num}) 


    return message

def makegem(skill, field, animation_list) -> str:
    rows = len(field)
    cols = len(field[0])

    ef = skill["makegem"]
    # 変更する配列が入っている
    target_gems = ef["elem"]
    make_gem_count = ef["make"]

    skip_set = set(target_gems)
    not_target = []

    for y in range(rows):
        for x in range(cols):
            current_gem = field[y][x]
            if current_gem not in skip_set:
                not_target.append((x, y))
    
    message = str(skill['effect'])

    if not not_target:
        return message

    count = min(len(not_target), make_gem_count)

    chose = random.sample(not_target, count)

    for x, y in chose:
        # 作るジェムが複数種あるなら、そこからランダムに選ぶ
        new_gem = random.choice(target_gems)
        
        field[y][x] = new_gem
        animation_list.append({ "x": x, "y": y, "start_time": time.time(), "duration": 0.6})

    return message
# ---------------- メイン ----------------
def main():
    # kakudai hyouji
    screen = pg.display.set_mode((WIN_W, WIN_H))
    pg.display.set_caption("Puzzle & Monsters - GUI Prototype")
    font = get_jp_font(20)
    gem_animations = []

    skill_queue = [] 
    current_processing = None

    party = {
        "player_name":"Player",
        "allies": partylist,
        "hp":600, "max_hp":600, "dp":(10+10+5+15)/4
    }
    enemies = [
        {"name":"スライム","element":"水","hp":100,"max_hp":100,"ap":10,"dp":1},
        {"name":"ゴブリン","element":"土","hp":200,"max_hp":200,"ap":20,"dp":5},
        {"name":"オオコウモリ","element":"風","hp":300,"max_hp":300,"ap":30,"dp":10},
        {"name":"ウェアウルフ","element":"風","hp":400,"max_hp":400,"ap":40,"dp":15},
        {"name":"ドラゴン","element":"火","hp":600,"max_hp":600,"ap":50,"dp":20},
    ]
    enemy_idx=0
    enemy = enemies[enemy_idx]
    field = init_field()

    drag_src: Optional[tuple[int, int]] = None
    drag_elem: Optional[str] = None
    hover_pos: Optional[tuple[int, int]] = None

    for member in party["allies"]:
        raw = load_monster_image(member["name"])
        img = keep_aspect(raw, int(SLOT_W * 0.9), int(SLOT_W * 0.9))
        member["display_image"] = img
    for en in enemies:
        raw = load_monster_image(en["name"])
        img = keep_aspect(raw, int(WIN_W * 0.1), int(WIN_W * 0.1))
        en["display_image"] = img

    clock = pg.time.Clock()

    def get_grid_pos_at_mouse(mx: int, my: int) -> Optional[tuple[int, int]]:
        grid_x = (mx - LEFT_MARGIN) // (SLOT_W + SLOT_PAD)
        grid_y = (my - FIELD_Y) // (SLOT_W + SLOT_PAD)
        
        rows = len(field)
        cols = len(field[0])

        if 0 <= grid_x < cols and 0 <= grid_y < rows:
            return (grid_x, grid_y)
        return None

    running = True
    message = ""
    # bairitsu それぞれの属性のところに、効果時間と倍率をもった辞書の集まりにしてやって、効果時間が０なら辞書から削除、ターン終了時に効果時間を０にしてやればいい
    buffs = {
                "火": [
                        # example
                        #  {'count': x, 'num': y}
                    ],
                "水": [],
                "風": [],
                "土": [],
                "命": []
            }
    # --- index -> hidari kara no junban de skill turn wo teigi ---
    sukill_turn = [0, 0, 0, 0, 0, 0]
    turn = 0

    # (1 - def_cut)を相手の攻撃力にかける。
    def_cut = 0.0

    while running:
        party_buttons = draw_top(screen, enemy, party, font, sukill_turn )
        for e in pg.event.get():
            if e.type == pg.QUIT:
                running = False

            elif e.type == pg.KEYDOWN:
                # if e.key == pg.K_ESCAPE:
                #    running = False

                print('a')
            elif e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                mouse_pos = e.pos
                for i, btn in enumerate(party_buttons):
                    skill_name = btn["data"]["skills"]
                    skill_data = SKILLS.get(skill_name)
                    if skill_data is None:
                        print("エラー: スキルは見つかりません")
                        continue

                    ct = skill_data["ct"]
                    if (btn["rect"].collidepoint(mouse_pos) and sukill_turn[i] >= ct):
                        skill_queue.append({
                            "data": btn["data"], # 誰のスキルか
                            "start_time": 0.0, # 開始時間は後で決める
                            "index": i # 誰が使ったか
                        })
                        
                        sukill_turn[i] = 0
                        target_data = btn["data"]

                mx, my = mouse_pos
                grid_pos = get_grid_pos_at_mouse(mx, my)
                
                if grid_pos:
                    drag_src = grid_pos
                    cx, cy = grid_pos
                    drag_elem = field[cy][cx]

            elif e.type == pg.MOUSEMOTION:
                mx, my = e.pos

                if drag_src is not None :
                    rows = len(field)
                    cols = len(field[0])

                    raw_x = (mx - LEFT_MARGIN) // (SLOT_W + SLOT_PAD)
                    raw_y = (my - FIELD_Y) // (SLOT_W + SLOT_PAD)

                    nx = max(0, min(cols - 1, raw_x))
                    ny = max(0, min(rows - 1, raw_y))

                    hover_pos = (nx, ny)


                    if hover_pos != drag_src:
                        sx, sy = drag_src

                        if abs(sx - nx) <= 1 and abs(sy - ny) <= 1:
                            field[sy][sx], field[ny][nx] = field[ny][nx], field[sy][sx]
                            turn_processed = True
                            drag_src = hover_pos
                else:
                    hover_pos = get_grid_pos_at_mouse(mx, my)


            elif e.type == pg.MOUSEBUTTONUP and e.button == 1:
                turn_processed = False


                # ドラッグしていたなら、手を離した時点でパズル判定へ(仕様)
                if drag_src is not None:
                    turn_processed = True

                    

                    drag_src = None
                    drag_elem = None
                    message = "drop now"


                if turn_processed:
                    combo = 0
                    to_do = {"火": 0, "水": 0, "風": 0, "土": 0, "命": 0}

                    while True:
                        raw_matches = scan_grid(field)
                        if not raw_matches: break 

                        clusters = get_clusters(field, raw_matches)

                        for cluster in clusters:
                            combo += 1

                            elem = cluster["color"]
                            count = cluster["count"]     # その塊のジェム数
                            coords = cluster["coords"]   # その塊の座標リスト

                            # 倍率バカすぎるかも
                            bonus = (count - 3) * 0.8

                            score = 1.00 + bonus

                            to_do[elem] += score 

                            # 盤面からの削除
                            for (gx, gy) in coords:
                                field[gy][gx] = "無"
                            current_time = time.time()
                            gem_animations = [a for a in gem_animations if current_time - a["start_time"] < a["duration"]]

                            # 描画関数に渡す
                            # 描画更新
                            screen.fill((22, 22, 28))
                            draw_top(screen, enemy, party, font, sukill_turn)
                            draw_field(screen, field, font, gem_animations)
                            draw_message(screen, f"コンボ {combo}！ {message}", font)
                            pg.display.flip()
                            time.sleep(0.4)

                        animation_fall(screen, field, font, sukill_turn, party, enemy)

                    # ダメージ・回復計算
                    for elem, value in to_do.items():
                        if value == 0:
                            continue

                        if elem == "命":
                            heal = jitter(20 * value)
                            party["hp"] = min(party["max_hp"], party["hp"] + heal)
                            message = f"HP +{heal}"
                        else:
                            default = 1.00
                            for i in buffs[elem]:
                                default *= i["num"]

                            dmg = party_attack_from_gems(elem, value, combo, party, enemy, default)
                            message = f"{elem}攻撃！ {dmg} ダメージ"


                    if enemy["hp"] <= 0:
                        message = f"{enemy['name']} を倒した！"

                    if enemy["hp"] > 0:
                        edmg = enemy_attack(party, enemy, def_cut)
                        message = f"{enemy['name']}の攻撃！ -{edmg}"
                        
                        # 攻撃エフェクト
                        screen.fill((22, 22, 28))
                        draw_top(screen, enemy, party, font, sukill_turn )
                        draw_field(screen, field, font, gem_animations)
                        draw_message(screen, message, font)
                        pg.display.flip()
                        time.sleep(FRAME_DELAY)

                        if party["hp"] <= 0:
                            message = "パーティは力尽きた…（ESCで終了）"
                    
                    else:
                        # 敵が倒れた -> 次の敵へ
                        enemy_idx += 1
                        if enemy_idx < len(enemies):
                            enemy = enemies[enemy_idx]
                            message = f"さらに奥へ… 次は {enemy['name']}"
                        else:
                            message = "ダンジョン制覇！おめでとう！（ESCで終了）"


                    for i in range(len(sukill_turn)):
                        sukill_turn[i] += 1

                    for i in range(len(sukill_turn)):
                        print(f"sukiru ta-n: {sukill_turn[i]}")


                    for i, gem in enumerate(buffs):
                        print(f"buff : {gem} :{buffs[gem]}")

                    turn += 1
                    # 基本的にカットは１ターンにする
                    def_cut = 0.0

                    for elem in buffs:
                        new_list = []
                        
                        for b in buffs[elem]:
                            b["count"] -= 1
                            
                            if b["count"] > 0:
                                new_list.append(b)
                        buffs[elem] = new_list


                    screen.fill((22, 22, 28))
                    draw_top(screen, enemy, party, font, sukill_turn )
                    draw_field(screen, field, font, gem_animations)
                    pg.display.flip()
                    time.sleep(FRAME_DELAY)

        if current_processing is None and len(skill_queue) > 0:
            current_processing = skill_queue.pop(0)
            current_processing["start_time"] = time.time()
            
            s_name = current_processing["data"]["skills"]

        if current_processing is not None:
            now = time.time()
            elapsed = now - current_processing["start_time"]

            if elapsed >= 2.0:
                target_data = current_processing["data"]
                
                res_msg, defc = skills(target_data, field, buffs, gem_animations, enemy, def_cut)
                def_cut = defc
                print(def_cut)
                message = res_msg
                
                current_processing = None
                
                # スキルによる撃破
                if enemy["hp"] <= 0:
                    message = f"{enemy['name']} を倒した！"
                    enemy_idx += 1
                    
                    if enemy_idx < len(enemies):
                        enemy = enemies[enemy_idx]
                        message += f" 次は {enemy['name']}"
                    else:
                        message = "ダンジョン制覇！おめでとう！（ESCで終了）"

        screen.fill((22, 22, 28))
        draw_top(screen, enemy, party, font, sukill_turn )
        
        draw_field(screen, field, font, gem_animations, hover_pos=hover_pos, drag_src=drag_src, drag_elem=drag_elem)
        
        
        draw_message(screen, message, font)
    
        if current_processing is not None:
            # 暗幕
            overlay = pg.Surface((WIN_W, WIN_H), pg.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))

            # キャラ画像や文字
            p_data = current_processing["data"]
            
            img = p_data["display_image"]
            big_img = pg.transform.scale(img, (256, 256)) 
            img_rect = big_img.get_rect(center=(WIN_W//2, WIN_H//2 - 50))
            screen.blit(big_img, img_rect)
            
            skill_name = p_data["skills"]
            text_surf = font.render(skill_name, True, (255, 255, 0))
            text_rect = text_surf.get_rect(center=(WIN_W//2, WIN_H//2 + 100))
            screen.blit(text_surf, text_rect)

        pg.display.flip()
        clock.tick(60)


    pg.quit()
    sys.exit()

if __name__=="__main__":
    main()
