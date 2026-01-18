import pygame as pg
import sys, os, random, time
from typing import List, Tuple, Optional

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

# ---------------- 可変パラメータ ----------------
FRAME_DELAY = 0.5
ENEMY_DELAY = 1.0
WIN_W, WIN_H = 980, 720

FIELD_Y = 300
SLOT_W = 60
SLOT_PAD = 8
LEFT_MARGIN = 540

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
        "ドラゴン":"dragon.png"
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

def leftmost_run(field:List[str])->Optional[Tuple[int,int]]:
    n=len(field); i=0
    while i<n:
        j=i+1
        while j<n and field[j]==field[i]: j+=1
        L=j-i
        if L>=3 and field[i] in GEMS: return (i,L)
        i=j
    return None

def scan_grid(grid: List[List[str]]) -> List[dict[str, int]]:
    matches = []
    rows = len(grid)
    cols = len(grid[0])

    for y in range(rows):
        result = leftmost_run(grid[y])
        if result:
            start_x, length = result
            matches.append({ "type": "yoko", "y": y, "x": start_x, "length": length })

    for x in range(cols):
        col_list = [grid[y][x] for y in range(rows)]
        result = leftmost_run(col_list)
        if result:
            start_y, length = result
            matches.append({ "type": "tate", "x": x, "y": start_y, "length": length })

    return matches

def grav(field:List[List[str]]):
    rows = len(field)
    cols = len(field[0])
    
    for x in range(cols):
        alive_gems = []
        for y in range(rows):
            if field[y][x] != "無":
                alive_gems.append(field[y][x])

        missing_count = rows - len(alive_gems)
        new_gems = [random.choice(GEMS) for _ in range(missing_count)]
        new_column = new_gems + alive_gems
        for y in range(rows):
            field[y][x] = new_column[y]

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

    for x in range(cols):
        tx = LEFT_MARGIN + x * (SLOT_W + SLOT_PAD)
        if x < len(SLOTS):
            s = font.render(SLOTS[x], True, (220, 220, 220))
            screen.blit(s, (tx + (SLOT_W - s.get_width()) // 2, FIELD_Y - 28))

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

def draw_top(screen, enemy, party, font):
    img = load_monster_image(enemy["name"])
    screen.blit(img, (40, 40))

    name = font.render(enemy["name"], True, (240, 240, 240))
    screen.blit(name, (320, 40))
    enemy_bar = hp_bar_surf(enemy["hp"], enemy["max_hp"], 420, 18)
    screen.blit(enemy_bar, (320, 80))

    enemy_hp_text = font.render(f"{enemy['hp']}/{enemy['max_hp']}", True, (240, 240, 240))
    screen.blit(enemy_hp_text, (750, 78))

    label = font.render("パーティ", True, (240, 240, 240))
    screen.blit(label, (320, 110))

    party_bar = hp_bar_surf(party["hp"], party["max_hp"], 420, 18)
    screen.blit(party_bar, (320, 140))

    party_hp_text = font.render(f"{int(party['hp'])}/{party['max_hp']}", True, (240, 240, 240))
    screen.blit(party_hp_text, (750, 138))

def draw_message(screen, text, font):
    surf = font.render(text, True, (230,230,230))
    screen.blit(surf,(40,450))

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


# ---------------- メイン ----------------
def main():
    pg.init()
    screen = pg.display.set_mode((WIN_W, WIN_H))
    pg.display.set_caption("Puzzle & Monsters - GUI Prototype")
    font = get_jp_font(20)

    party = {
        "player_name":"Player",
        "allies":[
            {"name":"青龍","element":"風","hp":150,"max_hp":150,"ap":15,"dp":10},
            {"name":"朱雀","element":"火","hp":150,"max_hp":150,"ap":25,"dp":10},
            {"name":"白虎","element":"土","hp":150,"max_hp":150,"ap":20,"dp":5},
            {"name":"玄武","element":"水","hp":150,"max_hp":150,"ap":20,"dp":15},
        ],
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
        for e in pg.event.get():
            if e.type == pg.QUIT:
                running = False

            elif e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                grid_pos = get_grid_pos_at_mouse(mx, my)
                
                if grid_pos:
                    drag_src = grid_pos
                    cx, cy = grid_pos
                    drag_elem = field[cy][cx]

            elif e.type == pg.MOUSEMOTION:
                mx, my = e.pos
                hover_pos = get_grid_pos_at_mouse(mx, my)

                if drag_src is not None and hover_pos is not None:
                    drop_pos = get_grid_pos_at_mouse(mx, my)

                    if hover_pos != drag_src:
                        sx, sy = drag_src
                        dx, dy = hover_pos

                        if abs(sx - dx) <= 1 and abs(sy - dy) <= 1:
                            field[sy][sx], field[dy][dx] = field[dy][dx], field[sy][sx]
                            turn_processed = True
                            drag_src = hover_pos


            elif e.type == pg.MOUSEBUTTONUP and e.button == 1:
                turn_processed = False


                # ドラッグしていたなら、手を離した時点でパズル判定へ
                if drag_src is not None:
                    turn_processed = True
                    
                    drag_src = None
                    drag_elem = None
                    message = "drop now"


                # === パズル処理ロジック ===
                if turn_processed:
                    combo = 0
                    while True:
                        # 1. まず縦横のラインを探す
                        raw_matches = scan_grid(field)
                        if not raw_matches: break 

                        # 2. ★追加★ T字やL字を結合して「塊」のリストにする
                        clusters = get_clusters(field, raw_matches)

                        # 3. 塊（コンボ）ごとに処理
                        for cluster in clusters:
                            combo += 1
                            
                            elem = cluster["color"]
                            count = cluster["count"]     # その塊のジェム数
                            coords = cluster["coords"]   # その塊の座標リスト
                            
                            # ダメージ・回復計算
                            # ※ count（個数）を使って計算します
                            if elem == "命":
                                # 回復量は個数が多いほど増える計算
                                heal = jitter(20 * (1.5 ** ((count - 3) + combo)))
                                party["hp"] = min(party["max_hp"], party["hp"] + heal)
                                message = f"HP +{heal}"
                            else:
                                dmg = party_attack_from_gems(elem, count, combo, party, enemy)
                                message = f"{elem}攻撃！ {dmg} ダメージ"

                            # 盤面からの削除
                            # cluster["coords"] に消すべき全座標が入っています
                            for (gx, gy) in coords:
                                field[gy][gx] = "無"

                            # 描画更新
                            screen.fill((22, 22, 28))
                            draw_top(screen, enemy, party, font)
                            draw_field(screen, field, font)
                            draw_message(screen, f"コンボ {combo}！ {message}", font)
                            pg.display.flip()
                            time.sleep(0.3)

                        # 全コンボ処理終了後、落下
                        grav(field)
                        
                        # （以下、以前と同じ落下後の描画処理...）
                        screen.fill((22, 22, 28))
                        draw_top(screen, enemy, party, font)
                        draw_field(screen, field, font)
                        draw_message(screen, "落下＆補充", font)
                        pg.display.flip()
                        time.sleep(FRAME_DELAY)

                        if enemy["hp"] <= 0:
                            message = f"{enemy['name']} を倒した！"
                            break
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
                            # field = init_field() # ★もし新しい敵で盤面リセットしたいならコメント外す
                            message = f"さらに奥へ… 次は {enemy['name']}"
                        else:
                            message = "ダンジョン制覇！おめでとう！（ESCで終了）"

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
