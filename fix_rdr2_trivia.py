from app import app, db, Game

def fix_rdr2_trivia():
    with app.app_context():
        # Ищем игру
        game = Game.query.filter(Game.title.ilike('%Red Dead Redemption 2%')).first()
        
        if not game:
            print("❌ Игра 'Red Dead Redemption 2' не найдена в базе.")
            return
        
        print(f"🎯 Найдена игра: {game.title} (ID: {game.id})")
        print(f"📝 Старый текст фактов:\n{game.trivia}\n")
        
        # Новый текст
        new_trivia = "Имеет один из самых детализированных открытых миров. На разработку ушло 8 лет и сотни миллионов долларов."
        
        print(f"🔄 Новый текст фактов:\n{new_trivia}\n")
        
        # Запрашиваем подтверждение
        confirm = input("Обновить интересные факты для этой игры? (y/n): ")
        
        if confirm.lower() == 'y':
            game.trivia = new_trivia
            db.session.commit()
            print("✅ Интересные факты обновлены успешно!")
        else:
            print("❌ Отменено.")

if __name__ == '__main__':
    fix_rdr2_trivia()