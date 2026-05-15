"""
Genesis Engine — Game Maker
Создаёт простые игры на Python/HTML5 через локальный AI.
"""
import os
import subprocess
from pathlib import Path

GAMES_DIR = Path(os.environ.get("JARVIS_SCRIPTS_DIR", str(Path.home() / "jarvis_scripts"))) / "games"
GAMES_DIR.mkdir(parents=True, exist_ok=True)

SNAKE_TEMPLATE = """
import pygame, random, sys

pygame.init()
W, H = 600, 400
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("{title}")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 36)

snake = [(W//2, H//2)]
direction = (20, 0)
food = (random.randrange(0, W, 20), random.randrange(0, H, 20))
score = 0

while True:
    for e in pygame.event.get():
        if e.type == pygame.QUIT: sys.exit()
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_UP and direction != (0,20): direction = (0,-20)
            elif e.key == pygame.K_DOWN and direction != (0,-20): direction = (0,20)
            elif e.key == pygame.K_LEFT and direction != (20,0): direction = (-20,0)
            elif e.key == pygame.K_RIGHT and direction != (-20,0): direction = (20,0)
    head = (snake[0][0]+direction[0], snake[0][1]+direction[1])
    if not (0 <= head[0] < W and 0 <= head[1] < H) or head in snake:
        screen.fill((0,0,0))
        screen.blit(font.render(f"Game Over! Score: {{score}}", True, (255,0,0)), (W//4, H//2))
        pygame.display.flip(); pygame.time.wait(3000); sys.exit()
    snake.insert(0, head)
    if head == food:
        score += 10
        food = (random.randrange(0,W,20), random.randrange(0,H,20))
    else:
        snake.pop()
    screen.fill((0,0,0))
    for s in snake: pygame.draw.rect(screen, (0,200,0), (*s, 18, 18))
    pygame.draw.rect(screen, (200,0,0), (*food, 18, 18))
    screen.blit(font.render(f"Score: {{score}}", True, (255,255,255)), (10, 10))
    pygame.display.flip()
    clock.tick(10)
"""

HTML_GAME_TEMPLATE = """<!DOCTYPE html>
<html><head><title>{title}</title>
<style>body{{background:#111;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;color:white;font-family:sans-serif}}
canvas{{border:2px solid #00ff00}}</style></head>
<body><h2>{title}</h2><canvas id="c" width="400" height="400"></canvas>
<p id="score">Score: 0</p>
<script>
const c=document.getElementById('c'),ctx=c.getContext('2d');
let snake=[{{x:200,y:200}}],dir={{x:20,y:0}},food=randFood(),score=0;
function randFood(){{return{{x:Math.floor(Math.random()*20)*20,y:Math.floor(Math.random()*20)*20}}}}
document.addEventListener('keydown',e=>{{
  if(e.key=='ArrowUp'&&dir.y!=20)dir={{x:0,y:-20}};
  if(e.key=='ArrowDown'&&dir.y!=-20)dir={{x:0,y:20}};
  if(e.key=='ArrowLeft'&&dir.x!=20)dir={{x:-20,y:0}};
  if(e.key=='ArrowRight'&&dir.x!=-20)dir={{x:20,y:0}};
}});
function loop(){{
  const head={{x:snake[0].x+dir.x,y:snake[0].y+dir.y}};
  if(head.x<0||head.x>=400||head.y<0||head.y>=400||snake.some(s=>s.x==head.x&&s.y==head.y)){{
    alert('Game Over! Score: '+score);snake=[{{x:200,y:200}}];dir={{x:20,y:0}};score=0;food=randFood();
  }}
  snake.unshift(head);
  if(head.x==food.x&&head.y==food.y){{score+=10;food=randFood();document.getElementById('score').textContent='Score: '+score;}}
  else snake.pop();
  ctx.fillStyle='#111';ctx.fillRect(0,0,400,400);
  ctx.fillStyle='#00ff00';snake.forEach(s=>ctx.fillRect(s.x,s.y,18,18));
  ctx.fillStyle='#ff4444';ctx.fillRect(food.x,food.y,18,18);
}}
setInterval(loop,150);
</script></body></html>"""


def create_game(game_type: str, title: str = "My Game") -> dict:
    """
    Создаёт игру по типу.
    game_type: 'snake_py', 'snake_html', 'text_rpg'
    """
    try:
        if game_type == "snake_py":
            path = GAMES_DIR / f"{title.replace(' ', '_')}.py"
            path.write_text(SNAKE_TEMPLATE.format(title=title), encoding="utf-8")
            return {"success": True, "path": str(path), "run": f"python {path}"}
        elif game_type == "snake_html":
            path = GAMES_DIR / f"{title.replace(' ', '_')}.html"
            path.write_text(HTML_GAME_TEMPLATE.format(title=title), encoding="utf-8")
            return {"success": True, "path": str(path), "run": f"termux-open {path}"}
        elif game_type == "text_rpg":
            path = GAMES_DIR / f"{title.replace(' ', '_')}.py"
            _write_text_rpg(path, title)
            return {"success": True, "path": str(path), "run": f"python {path}"}
        else:
            return {"success": False, "error": f"Неизвестный тип: {game_type}. Доступно: snake_py, snake_html, text_rpg"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _write_text_rpg(path: Path, title: str):
    path.write_text(f'''# {title} — Text RPG
import random

print("=== {title} ===")
name = input("Введи имя героя: ")
hp = 100
attack = 15
gold = 0

enemies = [
    {{"name": "Гоблин", "hp": 30, "atk": 8}},
    {{"name": "Орк", "hp": 60, "atk": 15}},
    {{"name": "Дракон", "hp": 150, "atk": 35}},
]

print(f"\nДобро пожаловать, {{name}}! Твой HP: {{hp}}")

for enemy in enemies:
    print(f"\n⚔️  Появился {{enemy['name']}}! HP: {{enemy['hp']}}")
    e_hp = enemy["hp"]
    while hp > 0 and e_hp > 0:
        action = input("1=Атаковать, 2=Убежать: ")
        if action == "2":
            print("Ты убежал!")
            break
        dmg = random.randint(attack - 5, attack + 5)
        e_hp -= dmg
        print(f"Ты наносишь {{dmg}} урона. HP врага: {{max(0, e_hp)}}")
        if e_hp <= 0:
            reward = random.randint(10, 50)
            gold += reward
            print(f"✅ Победа! +{{reward}} золота. Всего золота: {{gold}}")
            break
        e_dmg = random.randint(enemy["atk"] - 3, enemy["atk"] + 3)
        hp -= e_dmg
        print(f"Враг атакует! -{{e_dmg}} HP. Твой HP: {{max(0, hp)}}")
        if hp <= 0:
            print("💀 Ты погиб. Игра окончена.")
            break

if hp > 0:
    print(f"\n🏆 Ты победил всех врагов! Золото: {{gold}}")
''', encoding="utf-8")
