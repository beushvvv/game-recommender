from app import app, db, Game

with app.app_context():
    # Обновляем ссылки
    updates = {
        'The Legend of Zelda: Breath of the Wild': 'https://upload.wikimedia.org/wikipedia/en/c/c6/The_Legend_of_Zelda_Breath_of_the_Wild.jpg'
    }
    
    for title, url in updates.items():
        game = Game.query.filter_by(title=title).first()
        if game:
            game.cover_url = url
            print(f"Обновлено: {title}")
    
    db.session.commit()
    print("✅ Все обложки обновлены!")