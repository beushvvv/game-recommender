"""
Управление обложками игр (без requests)
Использование:
    python manage_covers.py                    - показать все обложки
    python manage_covers.py --list             - список всех игр с ID
    python manage_covers.py --list "часть"     - поиск по названию
    python manage_covers.py --check            - показать ссылки на обложки
    python manage_covers.py "Название"         - показать обложку конкретной игры
    python manage_covers.py "Название" "url"   - установить обложку
"""

import sys
import urllib.request
from app import app, db, Game

# Цвета для вывода в консоли
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text, color=Colors.RESET, bold=False):
    prefix = Colors.BOLD if bold else ''
    print(f"{prefix}{color}{text}{Colors.RESET}")

def check_url(url):
    """Проверяет, доступна ли ссылка на обложку (без requests)"""
    if not url or not url.startswith('http'):
        return False
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status == 200
    except:
        return False

def get_all_games():
    """Получить список всех игр с ID"""
    with app.app_context():
        return Game.query.order_by(Game.id).all()

def show_all_covers():
    """Показать все обложки"""
    with app.app_context():
        games = Game.query.order_by(Game.id).all()
        
        print_colored("\n" + "="*80, Colors.CYAN, bold=True)
        print_colored(f"{'ID':<6} {'Название':<40} {'Обложка':<60}", Colors.CYAN, bold=True)
        print_colored("="*80, Colors.CYAN, bold=True)
        
        for game in games:
            cover = game.cover_url or '❌ Нет обложки'
            if cover and cover.startswith('http'):
                # Пытаемся проверить
                try:
                    if check_url(cover):
                        cover_display = f"{Colors.GREEN}✓{Colors.RESET} {cover[:55]}"
                    else:
                        cover_display = f"{Colors.RED}✗{Colors.RESET} {cover[:55]}"
                except:
                    cover_display = f"{Colors.YELLOW}?{Colors.RESET} {cover[:55]}"
            else:
                cover_display = f"{Colors.YELLOW}⚠️ {cover[:55]}{Colors.RESET}"
            
            print(f"{game.id:<6} {game.title[:38]:<40} {cover_display}")
        
        print_colored("="*80, Colors.CYAN, bold=True)
        print_colored(f"Всего игр: {len(games)}", Colors.BLUE, bold=True)

def show_game_cover(title):
    """Показать обложку конкретной игры"""
    with app.app_context():
        game = Game.query.filter(Game.title.ilike(f'%{title}%')).first()
        
        if not game:
            print_colored(f"❌ Игра '{title}' не найдена", Colors.RED)
            return
        
        print_colored(f"\n{'='*60}", Colors.CYAN, bold=True)
        print_colored(f"ID: {game.id}", Colors.BLUE)
        print_colored(f"Название: {game.title}", Colors.BLUE)
        print_colored(f"Жанр: {game.genre}", Colors.BLUE)
        print_colored(f"Год: {game.release_year}", Colors.BLUE)
        print_colored(f"Обложка:", Colors.BLUE)
        print_colored(f"  {game.cover_url or '❌ Нет обложки'}", Colors.YELLOW)
        print_colored("="*60, Colors.CYAN, bold=True)

def set_cover(title, url):
    """Установить обложку для игры"""
    with app.app_context():
        # Ищем игру по точному названию или частичному совпадению
        game = Game.query.filter(Game.title == title).first()
        
        if not game:
            game = Game.query.filter(Game.title.ilike(f'%{title}%')).first()
        
        if not game:
            print_colored(f"❌ Игра '{title}' не найдена", Colors.RED)
            print_colored("\n📋 Доступные игры (первые 20):", Colors.YELLOW)
            games = Game.query.order_by(Game.id).limit(20).all()
            for g in games:
                print(f"   {g.id}. {g.title}")
            return
        
        if not url.startswith('http') and not url.startswith('/static'):
            print_colored(f"⚠️ URL должен начинаться с http://, https:// или /static/", Colors.YELLOW)
            return
        
        print_colored(f"\n🎮 Игра: {game.title} (ID: {game.id})", Colors.CYAN)
        print_colored(f"📷 Новая обложка: {url}", Colors.BLUE)
        
        confirm = input(f"\nУстановить обложку для '{game.title}'? (y/n): ")
        
        if confirm.lower() == 'y':
            old_url = game.cover_url
            game.cover_url = url
            db.session.commit()
            print_colored(f"✅ Обложка обновлена!", Colors.GREEN)
            print_colored(f"   Было: {old_url}", Colors.RED)
            print_colored(f"   Стало: {url}", Colors.GREEN)
        else:
            print_colored("❌ Отменено", Colors.RED)

def check_broken_covers():
    """Проверить все обложки на доступность"""
    with app.app_context():
        games = Game.query.filter(Game.cover_url.isnot(None)).all()
        
        print_colored("\n" + "="*80, Colors.CYAN, bold=True)
        print_colored("Проверка обложек...", Colors.CYAN, bold=True)
        print_colored("="*80, Colors.CYAN, bold=True)
        
        broken = []
        working = []
        
        for game in games:
            if game.cover_url and game.cover_url.startswith('http'):
                try:
                    if check_url(game.cover_url):
                        working.append(game)
                        print_colored(f"✅ {game.title[:40]:<40} - работает", Colors.GREEN)
                    else:
                        broken.append(game)
                        print_colored(f"❌ {game.title[:40]:<40} - НЕ РАБОТАЕТ", Colors.RED)
                except:
                    broken.append(game)
                    print_colored(f"⚠️ {game.title[:40]:<40} - ошибка проверки", Colors.YELLOW)
            else:
                print_colored(f"📁 {game.title[:40]:<40} - локальная обложка", Colors.CYAN)
        
        print_colored("="*80, Colors.CYAN, bold=True)
        print_colored(f"✅ Работает: {len(working)}", Colors.GREEN)
        print_colored(f"❌ Не работает: {len(broken)}", Colors.RED)
        
        if broken:
            print_colored("\n📋 Список нерабочих обложек:", Colors.YELLOW, bold=True)
            for game in broken:
                print_colored(f"   {game.id}. {game.title}", Colors.YELLOW)
                print_colored(f"      {game.cover_url}", Colors.RED)

def list_games(search=None):
    """Список всех игр с ID"""
    with app.app_context():
        if search:
            games = Game.query.filter(Game.title.ilike(f'%{search}%')).order_by(Game.id).all()
        else:
            games = Game.query.order_by(Game.id).all()
        
        print_colored("\n" + "="*70, Colors.CYAN, bold=True)
        print_colored(f"{'ID':<6} {'Название':<50} {'Жанр':<20} {'Год':<6}", Colors.CYAN, bold=True)
        print_colored("="*70, Colors.CYAN, bold=True)
        
        for game in games:
            print(f"{game.id:<6} {game.title[:48]:<50} {game.genre[:18]:<20} {game.release_year:<6}")
        
        print_colored("="*70, Colors.CYAN, bold=True)
        print_colored(f"Всего: {len(games)} игр", Colors.BLUE, bold=True)

def show_help():
    """Показать справку"""
    print_colored("""
╔═══════════════════════════════════════════════════════════════════════╗
║                    Управление обложками игр                          ║
╠═══════════════════════════════════════════════════════════════════════╣
║  Использование:                                                       ║
║    python manage_covers.py                    - показать все обложки  ║
║    python manage_covers.py --list             - список всех игр       ║
║    python manage_covers.py --list "часть"     - поиск по названию     ║
║    python manage_covers.py --check            - проверить нерабочие   ║
║    python manage_covers.py "Название"         - показать обложку игры ║
║    python manage_covers.py "Название" "url"   - установить обложку    ║
║                                                                       ║
║  Примеры:                                                             ║
║    python manage_covers.py --list                                   ║
║    python manage_covers.py --list Ведьмак                           ║
║    python manage_covers.py "Ведьмак 3"                              ║
║    python manage_covers.py "Mortal Kombat" "https://..."            ║
║    python manage_covers.py --check                                  ║
║                                                                       ║
║  Где брать обложки:                                                  ║
║    • Steam: https://shared.akamai.steamstatic.com/...                ║
║    • IGDB:  https://images.igdb.com/igdb/image/upload/...            ║
║    • Локально: /static/images/название.jpg                          ║
╚═══════════════════════════════════════════════════════════════════════╝
    """, Colors.CYAN)

def main():
    args = sys.argv[1:]
    
    if not args:
        show_all_covers()
    elif args[0] == '--help' or args[0] == '-h':
        show_help()
    elif args[0] == '--list':
        if len(args) > 1:
            list_games(args[1])
        else:
            list_games()
    elif args[0] == '--check':
        check_broken_covers()
    elif len(args) == 1:
        show_game_cover(args[0])
    elif len(args) == 2:
        set_cover(args[0], args[1])
    else:
        print_colored("❌ Неверные параметры. Используй --help для справки", Colors.RED)

if __name__ == '__main__':
    main()