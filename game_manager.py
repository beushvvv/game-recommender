"""
Управление играми и системными требованиями
Интерактивный инструмент для работы с базой данных игр

Использование:
    python game_manager.py          - запустить интерактивное меню
    python game_manager.py --help   - показать справку
"""

import sys
import os
from app import app, db, Game, Tag, GameTags, SystemRequirement

# Цвета для вывода в консоли
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def clear_screen():
    """Очистка экрана"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(text):
    """Печать заголовка"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}\n")

def print_game_info(game, show_requirements=True):
    """Печать информации об игре"""
    print(f"{Colors.GREEN}{Colors.BOLD}ID: {Colors.RESET}{game.id}")
    print(f"{Colors.GREEN}{Colors.BOLD}Название: {Colors.RESET}{game.title}")
    print(f"{Colors.GREEN}{Colors.BOLD}Жанр: {Colors.RESET}{game.genre}")
    print(f"{Colors.GREEN}{Colors.BOLD}Год: {Colors.RESET}{game.release_year}")
    print(f"{Colors.GREEN}{Colors.BOLD}Глубина сюжета: {Colors.RESET}{game.story_depth}/10")
    print(f"{Colors.GREEN}{Colors.BOLD}Выбор влияет: {Colors.RESET}{'Да' if game.has_choices else 'Нет'}")
    print(f"{Colors.GREEN}{Colors.BOLD}Описание: {Colors.RESET}{game.description[:200]}..." if len(game.description) > 200 else f"{Colors.GREEN}{Colors.BOLD}Описание: {Colors.RESET}{game.description}")
    print(f"{Colors.GREEN}{Colors.BOLD}Обложка: {Colors.RESET}{game.cover_url}")
    print(f"{Colors.GREEN}{Colors.BOLD}Интересные факты: {Colors.RESET}{game.trivia[:100]}..." if game.trivia and len(game.trivia) > 100 else f"{Colors.GREEN}{Colors.BOLD}Интересные факты: {Colors.RESET}{game.trivia}")
    
    # Теги
    if game.tags:
        tags_str = ', '.join([tag.name for tag in game.tags])
        print(f"{Colors.GREEN}{Colors.BOLD}Теги: {Colors.RESET}{tags_str}")
    
    # Системные требования
    if show_requirements:
        reqs = SystemRequirement.query.filter_by(game_id=game.id).all()
        if reqs:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}Системные требования:{Colors.RESET}")
            for req in reqs:
                req_type = "Минимальные" if req.requirement_type == 'min' else "Рекомендуемые"
                print(f"  {Colors.CYAN}{req_type}:{Colors.RESET}")
                if req.os: print(f"    ОС: {req.os}")
                if req.cpu: print(f"    Процессор: {req.cpu}")
                if req.ram: print(f"    ОЗУ: {req.ram}")
                if req.gpu: print(f"    Видеокарта: {req.gpu}")
                if req.directx: print(f"    DirectX: {req.directx}")
                if req.storage: print(f"    Место: {req.storage}")

def list_all_games():
    """Показать все игры"""
    with app.app_context():
        games = Game.query.order_by(Game.id).all()
        
        print_header(f"ВСЕ ИГРЫ ({len(games)})")
        
        print(f"{Colors.CYAN}{'ID':<6} {'Название':<45} {'Жанр':<18} {'Год':<6}{Colors.RESET}")
        print(f"{Colors.CYAN}{'-'*80}{Colors.RESET}")
        
        for game in games:
            print(f"{game.id:<6} {game.title[:42]:<45} {game.genre[:16]:<18} {game.release_year:<6}")
        
        print(f"\n{Colors.GREEN}Всего: {len(games)} игр{Colors.RESET}")

def search_game():
    """Поиск игры по названию"""
    search = input(f"\n{Colors.YELLOW}Введите название (или часть): {Colors.RESET}")
    
    with app.app_context():
        games = Game.query.filter(Game.title.ilike(f'%{search}%')).order_by(Game.id).all()
        
        if not games:
            print(f"{Colors.RED}❌ Игры не найдены{Colors.RESET}")
            return
        
        print_header(f"РЕЗУЛЬТАТЫ ПОИСКА: {len(games)}")
        
        for game in games:
            print(f"{Colors.GREEN}ID: {game.id}{Colors.RESET} - {game.title} ({game.release_year})")

def view_game_details():
    """Просмотр детальной информации об игре"""
    game_id = input(f"\n{Colors.YELLOW}Введите ID игры: {Colors.RESET}")
    
    with app.app_context():
        game = Game.query.get(game_id)
        
        if not game:
            print(f"{Colors.RED}❌ Игра с ID {game_id} не найдена{Colors.RESET}")
            return
        
        print_header(f"ИНФОРМАЦИЯ ОБ ИГРЕ")
        print_game_info(game, show_requirements=True)

def add_new_game():
    """Добавление новой игры"""
    print_header("ДОБАВЛЕНИЕ НОВОЙ ИГРЫ")
    
    with app.app_context():
        # Сбор информации
        title = input(f"{Colors.YELLOW}Название: {Colors.RESET}")
        
        # Проверка на существование
        existing = Game.query.filter_by(title=title).first()
        if existing:
            print(f"{Colors.RED}❌ Игра '{title}' уже существует (ID: {existing.id}){Colors.RESET}")
            return
        
        description = input(f"{Colors.YELLOW}Описание: {Colors.RESET}")
        genre = input(f"{Colors.YELLOW}Жанр: {Colors.RESET}")
        release_year = input(f"{Colors.YELLOW}Год выпуска: {Colors.RESET}")
        story_depth = input(f"{Colors.YELLOW}Глубина сюжета (1-10): {Colors.RESET}")
        has_choices = input(f"{Colors.YELLOW}Выбор влияет на сюжет? (y/n): {Colors.RESET}").lower() == 'y'
        cover_url = input(f"{Colors.YELLOW}Ссылка на обложку: {Colors.RESET}")
        trivia = input(f"{Colors.YELLOW}Интересные факты: {Colors.RESET}")
        
        # Теги
        tags_input = input(f"{Colors.YELLOW}Теги (через запятую): {Colors.RESET}")
        tags_list = [t.strip() for t in tags_input.split(',') if t.strip()]
        
        # Создаём игру
        game = Game(
            title=title,
            description=description,
            genre=genre,
            release_year=int(release_year) if release_year else None,
            story_depth=int(story_depth) if story_depth else None,
            has_choices=has_choices,
            cover_url=cover_url if cover_url else None,
            trivia=trivia if trivia else None
        )
        db.session.add(game)
        db.session.flush()
        
        # Добавляем теги
        for tag_name in tags_list:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
                db.session.flush()
            game_tag = GameTags(game_id=game.id, tag_id=tag.id)
            db.session.add(game_tag)
        
        db.session.commit()
        
        print(f"\n{Colors.GREEN}✅ Игра '{title}' добавлена с ID: {game.id}{Colors.RESET}")
        
        # Спросить про системные требования
        add_req = input(f"\n{Colors.YELLOW}Добавить системные требования? (y/n): {Colors.RESET}")
        if add_req.lower() == 'y':
            add_requirements_for_game(game.id)

def edit_game():
    """Редактирование игры"""
    game_id = input(f"\n{Colors.YELLOW}Введите ID игры для редактирования: {Colors.RESET}")
    
    with app.app_context():
        game = Game.query.get(game_id)
        
        if not game:
            print(f"{Colors.RED}❌ Игра с ID {game_id} не найдена{Colors.RESET}")
            return
        
        print_header(f"РЕДАКТИРОВАНИЕ: {game.title}")
        print(f"{Colors.CYAN}Оставьте поле пустым, чтобы не менять{Colors.RESET}\n")
        
        # Редактирование полей
        new_title = input(f"Название [{game.title}]: ").strip()
        if new_title:
            game.title = new_title
        
        new_description = input(f"Описание [{game.description[:50]}...]: ").strip()
        if new_description:
            game.description = new_description
        
        new_genre = input(f"Жанр [{game.genre}]: ").strip()
        if new_genre:
            game.genre = new_genre
        
        new_year = input(f"Год [{game.release_year}]: ").strip()
        if new_year:
            game.release_year = int(new_year)
        
        new_story = input(f"Глубина сюжета (1-10) [{game.story_depth}]: ").strip()
        if new_story:
            game.story_depth = int(new_story)
        
        new_choices = input(f"Выбор влияет (y/n) [{'y' if game.has_choices else 'n'}]: ").strip()
        if new_choices:
            game.has_choices = new_choices.lower() == 'y'
        
        new_cover = input(f"Обложка [{game.cover_url}]: ").strip()
        if new_cover:
            game.cover_url = new_cover
        
        new_trivia = input(f"Интересные факты [{game.trivia[:50]}...]: ").strip()
        if new_trivia:
            game.trivia = new_trivia
        
        db.session.commit()
        print(f"\n{Colors.GREEN}✅ Игра обновлена!{Colors.RESET}")

def add_requirements_for_game(game_id):
    """Добавление системных требований для конкретной игры"""
    with app.app_context():
        game = Game.query.get(game_id)
        if not game:
            print(f"{Colors.RED}❌ Игра не найдена{Colors.RESET}")
            return
        
        print_header(f"ДОБАВЛЕНИЕ СИСТЕМНЫХ ТРЕБОВАНИЙ: {game.title}")
        
        # Удаляем старые требования
        SystemRequirement.query.filter_by(game_id=game_id).delete()
        
        # Минимальные требования
        print(f"\n{Colors.CYAN}Минимальные требования:{Colors.RESET}")
        min_os = input("  ОС: ").strip()
        min_cpu = input("  Процессор: ").strip()
        min_ram = input("  ОЗУ: ").strip()
        min_gpu = input("  Видеокарта: ").strip()
        min_dx = input("  DirectX: ").strip()
        min_storage = input("  Место на диске: ").strip()
        
        if any([min_os, min_cpu, min_ram, min_gpu, min_dx, min_storage]):
            min_req = SystemRequirement(
                game_id=game_id,
                requirement_type='min',
                os=min_os if min_os else None,
                cpu=min_cpu if min_cpu else None,
                ram=min_ram if min_ram else None,
                gpu=min_gpu if min_gpu else None,
                directx=min_dx if min_dx else None,
                storage=min_storage if min_storage else None
            )
            db.session.add(min_req)
        
        # Рекомендуемые требования
        print(f"\n{Colors.CYAN}Рекомендуемые требования:{Colors.RESET}")
        rec_os = input("  ОС: ").strip()
        rec_cpu = input("  Процессор: ").strip()
        rec_ram = input("  ОЗУ: ").strip()
        rec_gpu = input("  Видеокарта: ").strip()
        rec_dx = input("  DirectX: ").strip()
        rec_storage = input("  Место на диске: ").strip()
        
        if any([rec_os, rec_cpu, rec_ram, rec_gpu, rec_dx, rec_storage]):
            rec_req = SystemRequirement(
                game_id=game_id,
                requirement_type='rec',
                os=rec_os if rec_os else None,
                cpu=rec_cpu if rec_cpu else None,
                ram=rec_ram if rec_ram else None,
                gpu=rec_gpu if rec_gpu else None,
                directx=rec_dx if rec_dx else None,
                storage=rec_storage if rec_storage else None
            )
            db.session.add(rec_req)
        
        db.session.commit()
        print(f"\n{Colors.GREEN}✅ Системные требования добавлены!{Colors.RESET}")

def manage_requirements():
    """Управление системными требованиями"""
    game_id = input(f"\n{Colors.YELLOW}Введите ID игры: {Colors.RESET}")
    
    with app.app_context():
        game = Game.query.get(game_id)
        if not game:
            print(f"{Colors.RED}❌ Игра не найдена{Colors.RESET}")
            return
        
        print_header(f"СИСТЕМНЫЕ ТРЕБОВАНИЯ: {game.title}")
        
        reqs = SystemRequirement.query.filter_by(game_id=game_id).all()
        
        if reqs:
            for req in reqs:
                req_type = "Минимальные" if req.requirement_type == 'min' else "Рекомендуемые"
                print(f"\n{Colors.CYAN}{req_type}:{Colors.RESET}")
                if req.os: print(f"  ОС: {req.os}")
                if req.cpu: print(f"  Процессор: {req.cpu}")
                if req.ram: print(f"  ОЗУ: {req.ram}")
                if req.gpu: print(f"  Видеокарта: {req.gpu}")
                if req.directx: print(f"  DirectX: {req.directx}")
                if req.storage: print(f"  Место: {req.storage}")
        else:
            print(f"{Colors.YELLOW}Нет системных требований для этой игры{Colors.RESET}")
        
        print(f"\n{Colors.YELLOW}1. Добавить/обновить требования{Colors.RESET}")
        print(f"{Colors.YELLOW}2. Вернуться в меню{Colors.RESET}")
        
        choice = input(f"\nВыберите действие: ")
        if choice == '1':
            add_requirements_for_game(game_id)

def delete_game():
    """Удаление игры"""
    game_id = input(f"\n{Colors.YELLOW}Введите ID игры для удаления: {Colors.RESET}")
    
    with app.app_context():
        game = Game.query.get(game_id)
        
        if not game:
            print(f"{Colors.RED}❌ Игра с ID {game_id} не найдена{Colors.RESET}")
            return
        
        print_header(f"УДАЛЕНИЕ ИГРЫ")
        print(f"{Colors.RED}{Colors.BOLD}ВНИМАНИЕ! Это действие удалит игру и все связанные данные:{Colors.RESET}")
        print(f"  - Статусы пользователей")
        print(f"  - Теги")
        print(f"  - Системные требования")
        
        print(f"\n{Colors.YELLOW}Игра: {game.title} (ID: {game.id}){Colors.RESET}")
        
        confirm = input(f"\n{Colors.RED}Введите название игры для подтверждения: {Colors.RESET}")
        
        if confirm == game.title:
            # Удаляем связанные данные
            UserGameStatus.query.filter_by(game_id=game_id).delete()
            GameTags.query.filter_by(game_id=game_id).delete()
            SystemRequirement.query.filter_by(game_id=game_id).delete()
            db.session.delete(game)
            db.session.commit()
            print(f"{Colors.GREEN}✅ Игра '{game.title}' удалена!{Colors.RESET}")
        else:
            print(f"{Colors.RED}❌ Отменено{Colors.RESET}")

def show_menu():
    """Показать главное меню"""
    clear_screen()
    print(f"""
{Colors.CYAN}{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║                    УПРАВЛЕНИЕ ИГРАМИ                          ║
╠══════════════════════════════════════════════════════════════╣
║  {Colors.GREEN}1{Colors.CYAN}. Показать все игры                                     ║
║  {Colors.GREEN}2{Colors.CYAN}. Поиск игры                                            ║
║  {Colors.GREEN}3{Colors.CYAN}. Просмотр детальной информации                          ║
║  {Colors.GREEN}4{Colors.CYAN}. Добавить новую игру                                   ║
║  {Colors.GREEN}5{Colors.CYAN}. Редактировать игру                                    ║
║  {Colors.GREEN}6{Colors.CYAN}. Управление системными требованиями                    ║
║  {Colors.GREEN}7{Colors.CYAN}. Удалить игру                                          ║
║  {Colors.GREEN}0{Colors.CYAN}. Выход                                                 ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
    """)

def main():
    """Главная функция"""
    while True:
        show_menu()
        choice = input(f"{Colors.YELLOW}Выберите действие: {Colors.RESET}")
        
        if choice == '1':
            list_all_games()
            input(f"\n{Colors.CYAN}Нажмите Enter для продолжения...{Colors.RESET}")
        elif choice == '2':
            search_game()
            input(f"\n{Colors.CYAN}Нажмите Enter для продолжения...{Colors.RESET}")
        elif choice == '3':
            view_game_details()
            input(f"\n{Colors.CYAN}Нажмите Enter для продолжения...{Colors.RESET}")
        elif choice == '4':
            add_new_game()
            input(f"\n{Colors.CYAN}Нажмите Enter для продолжения...{Colors.RESET}")
        elif choice == '5':
            edit_game()
            input(f"\n{Colors.CYAN}Нажмите Enter для продолжения...{Colors.RESET}")
        elif choice == '6':
            manage_requirements()
            input(f"\n{Colors.CYAN}Нажмите Enter для продолжения...{Colors.RESET}")
        elif choice == '7':
            delete_game()
            input(f"\n{Colors.CYAN}Нажмите Enter для продолжения...{Colors.RESET}")
        elif choice == '0':
            print(f"\n{Colors.GREEN}До свидания!{Colors.RESET}")
            sys.exit(0)
        else:
            print(f"{Colors.RED}❌ Неверный выбор{Colors.RESET}")
            input(f"\n{Colors.CYAN}Нажмите Enter для продолжения...{Colors.RESET}")

if __name__ == '__main__':
    main()