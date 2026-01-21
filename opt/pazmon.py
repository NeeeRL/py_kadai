import pygame as pg
import sys, os, random, time
from typing import List, Tuple, Optional

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

SKILLS = {
    "竜巻": {
        "effect": "風属性のダメージ2倍",
        "ct": 6,

    },
    "火を纏う": {
        "effect": "火ジェムをランダムに6個生成",
        "ct": 3,
        "value": {
            "make": 6, "elem": "火"
        }
    },
    "引っ掻く": {
        "effect": "相手の場のモンスターに最大hpの30%ダメージ",
        "ct": 7,

    },
    "鉄壁": {
        "effect": "相手の動きを２ターン遅らせる",
        "ct": 8,

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

def animation_fall(screen, field, font, party, enemy):
    rows = len(field)
    cols = len(field[0])
    
    # --- どこからどこへ動くかを計算する ---
    moves = [] # { "elem":ジェム, "x":ピクセルX, "start_y":開始Y, "end_y":終了Y }
    
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
        draw_top(screen, enemy, party, font)
        

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

def party_attack_from_gems(elem:str, run_len:int, combo:int, party:dict, monster:dict)->int:
    combo_coeff = 1.5 ** ((run_len - 3) + combo)
    if elem=="命":
        heal=jitter(20*combo_coeff); party["hp"]=min(party["max_hp"], party["hp"]+heal); return 0
    ally = next((a for a in party["allies"] if a["element"]==elem), None)
    if not ally: return 0
    base=max(1, ally["ap"]-monster["dp"])
    dmg=jitter(base*attr_coeff(elem,monster["element"])*combo_coeff)
    monster["hp"]=max(0,monster["hp"]-dmg); return dmg

def enemy_attack(party:dict, monster:dict)->int:
    base=max(1, monster["ap"]-party["dp"])
    dmg=jitter(base); party["hp"]=max(0,party["hp"]-dmg); return dmg

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

def draw_field(screen, field: list[list[str]], font, 
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

def draw_members(screen, partylist) -> list:
    party_buttons = []

    for i, menber in enumerate(partylist):
        rect_x = LEFT_MARGIN + i * (SLOT_W + SLOT_PAD)
        rect_y = WIN_H * 0.4
        rect = pg.Rect(rect_x, rect_y, SLOT_W, SLOT_W)
        party_buttons.append({
            "rect": rect,
            "data": partylist[i]
        })
        pg.draw.rect(screen, (35, 35, 40), rect, border_radius=8)
        
        elem = menber["element"]
        # 黒
        border_color = COLOR_RGB[elem]
        
        pg.draw.rect(screen, border_color, rect, width=4, border_radius=8)

        img = menber["display_image"]

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

def draw_top(screen, enemy, party, font) -> list:
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
    party_buttons = draw_members(screen, partylist)
    
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
def skills(member_data, field):
    name = member_data['skills']
    skill_data = SKILLS.get(name)

    if not skill_data:
        return "スキルデータが見つかりません"
    # value ではなく、メイクジェムみたいなキーにしちゃって、値と区別をつけた方がいいかもしれぬ
    if "value" in skill_data:
        message = makegem(skill_data, field)
        return message
    else:
        return f"発動！: {skill_data['effect']}"

def makegem(skill, field) -> str:
    rows = len(field)
    cols = len(field[0])

    ef = skill["value"]
    target_gem = ef["elem"]
    make_gem_count = ef["make"]

    not_target = []

    for y in range(rows):
        for x in range(cols):
            if field[y][x] != target_gem:
                    not_target.append((x, y))
    
    message = str(skill['effect'])

    if not not_target:
        return message

    count = min(len(not_target), make_gem_count)

    chose = random.sample(not_target, count)

    for x, y in chose:
        field[y][x] = target_gem

    return message
# ---------------- メイン ----------------
def main():
    # kakudai hyouji
    screen = pg.display.set_mode((WIN_W, WIN_H))
    pg.display.set_caption("Puzzle & Monsters - GUI Prototype")
    font = get_jp_font(20)

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
    while running:
        party_buttons = draw_top(screen, enemy, party, font)
        for e in pg.event.get():
            if e.type == pg.QUIT:
                running = False

            elif e.type == pg.KEYDOWN:
                # if e.key == pg.K_ESCAPE:
                #    running = False

                print('a')
            elif e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                mouse_pos = e.pos
                for btn in party_buttons:
                    if btn["rect"].collidepoint(mouse_pos):
                        
                        target_data = btn["data"]
                        # 必要ないかも
                        message = skills(target_data, field)

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

                            bonus = (count - 3) * 0.10

                            score = 1.00 + bonus
                            
                            to_do[elem] += score 

                            # 盤面からの削除
                            for (gx, gy) in coords:
                                field[gy][gx] = "無"

                            # 描画更新
                            screen.fill((22, 22, 28))
                            draw_top(screen, enemy, party, font)
                            draw_field(screen, field, font)
                            draw_message(screen, f"コンボ {combo}！ {message}", font)
                            pg.display.flip()
                            time.sleep(0.4)

                        animation_fall(screen, field, font, party, enemy)
                        
                    # ダメージ・回復計算
                    for elem, value in to_do.items():
                        if value == 0:
                            continue

                        if elem == "命":
                            heal = jitter(20 * value)
                            party["hp"] = min(party["max_hp"], party["hp"] + heal)
                            message = f"HP +{heal}"
                        else:
                            dmg = party_attack_from_gems(elem, value, combo, party, enemy)
                            message = f"{elem}攻撃！ {dmg} ダメージ"


                    if enemy["hp"] <= 0:
                        message = f"{enemy['name']} を倒した！"

                    if enemy["hp"] > 0:
                        edmg = enemy_attack(party, enemy)
                        message = f"{enemy['name']}の攻撃！ -{edmg}"
                        
                        # 攻撃エフェクト
                        screen.fill((22, 22, 28))
                        draw_top(screen, enemy, party, font)
                        draw_field(screen, field, font)
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
                    
                    # （以下、以前と同じ落下後の描画処理...）
                    screen.fill((22, 22, 28))
                    draw_top(screen, enemy, party, font)
                    draw_field(screen, field, font)
                    pg.display.flip()
                    time.sleep(FRAME_DELAY)

        screen.fill((22, 22, 28))
        draw_top(screen, enemy, party, font)
        
        draw_field(screen, field, font, hover_pos=hover_pos, drag_src=drag_src, drag_elem=drag_elem)
        
        
        draw_message(screen, message, font)
        pg.display.flip()
        clock.tick(60)

    pg.quit()
    sys.exit()

if __name__=="__main__":
    main()
