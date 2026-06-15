from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import func
from collections import Counter

app = Flask(__name__)
import os
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-local')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:пароль@localhost/game_recommender')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Модели данных
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    theme_preference = db.Column(db.String(10), default='dark')
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Game(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    cover_url = db.Column(db.String(500))
    release_year = db.Column(db.Integer)
    genre = db.Column(db.String(100))
    developer = db.Column(db.String(255))
    story_depth = db.Column(db.Integer)
    has_choices = db.Column(db.Boolean, default=False)
    trivia = db.Column(db.Text)
    
    tags = db.relationship('Tag', secondary='game_tags', lazy='subquery',
                           backref=db.backref('games', lazy=True))

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class GameTags(db.Model):
    __tablename__ = 'game_tags'
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), primary_key=True)

class UserGameStatus(db.Model):
    __tablename__ = 'user_game_status'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), primary_key=True)
    status = db.Column(db.String(20))
    user_rating = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Добавь эту строку!
    game = db.relationship('Game', backref='user_statuses_backref')

class SystemRequirement(db.Model):
    __tablename__ = 'system_requirements'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    requirement_type = db.Column(db.String(10))  # 'min' или 'rec'
    os = db.Column(db.String(100))
    cpu = db.Column(db.String(200))
    ram = db.Column(db.String(50))
    gpu = db.Column(db.String(200))
    directx = db.Column(db.String(50))
    storage = db.Column(db.String(50))
    
    game = db.relationship('Game', backref=db.backref('requirements', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_recommendations_for_user(user_id, limit=4):
    """
    Возвращает список рекомендуемых игр с пояснением причин
    на основе статусов пользователя (только played/playing, исключая dropped)
    """
    from collections import Counter
    
    # Получаем игры, которые пользователь прошел или играет
    user_games = db.session.query(UserGameStatus).filter(
        UserGameStatus.user_id == user_id,
        UserGameStatus.status.in_(['played', 'playing'])
    ).all()
    
    # ID всех игр пользователя (чтобы не рекомендовать уже имеющиеся)
    all_user_game_ids = [ug.game_id for ug in db.session.query(UserGameStatus).filter(
        UserGameStatus.user_id == user_id
    ).all()]
    
    # Если нет пройденных игр
    if not user_games:
        # Показываем самые популярные игры
        popular_games = db.session.query(
            Game, func.count(UserGameStatus.game_id).label('total')
        ).join(UserGameStatus).group_by(Game.id).order_by(
            func.count(UserGameStatus.game_id).desc()
        ).limit(limit).all()
        
        recommendations = []
        for game, count in popular_games:
            recommendations.append({
                'game': game,
                'reason': f'Популярная игра среди пользователей ({count} человек)'
            })
        return recommendations
    
    # Собираем все теги и жанры из игр пользователя
    tag_counter = Counter()
    genre_counter = Counter()
    games_with_tags = []
    
    for user_game in user_games:
        game = user_game.game
        if game and game.tags:
            for tag in game.tags:
                tag_counter[tag.id] += 1
                games_with_tags.append({
                    'game': game.title,
                    'tag': tag.name
                })
        if game and game.genre:
            genre_counter[game.genre] += 1
    
    # Топ тегов и жанров
    top_tags = tag_counter.most_common(5)
    top_genres = genre_counter.most_common(2)
    
    # Собираем рекомендации
    recommendations = []
    
    # 1. Рекомендации по тегам (основные)
    if top_tags:
        top_tag_ids = [tag_id for tag_id, _ in top_tags[:5]]
        top_tag_names = []
        for tag_id, _ in top_tags[:5]:
            tag = Tag.query.get(tag_id)
            if tag:
                top_tag_names.append(tag.name)
        
        # Ищем игры с этими тегами
        tag_games = db.session.query(Game).join(GameTags).filter(
            GameTags.tag_id.in_(top_tag_ids),
            ~Game.id.in_(all_user_game_ids)
        ).group_by(Game.id).order_by(
            func.count(GameTags.tag_id).desc()
        ).limit(limit).all()
        
        for game in tag_games:
            # Находим общие теги для этой игры
            common_tags = []
            for tag in game.tags:
                if tag.id in top_tag_ids:
                    common_tags.append(tag.name)
            
            reason = f"Тебе понравились игры с тегами: {', '.join(common_tags[:3])}"
            recommendations.append({
                'game': game,
                'reason': reason,
                'type': 'tag'
            })
    
    # 2. Если не хватило рекомендаций, добавляем по жанрам
    if len(recommendations) < limit and top_genres:
        top_genre_name = top_genres[0][0]
        
        genre_games = Game.query.filter(
            Game.genre == top_genre_name,
            ~Game.id.in_(all_user_game_ids),
            ~Game.id.in_([r['game'].id for r in recommendations])
        ).limit(limit - len(recommendations)).all()
        
        for game in genre_games:
            recommendations.append({
                'game': game,
                'reason': f'Ты часто выбираешь жанр {top_genre_name}',
                'type': 'genre'
            })
    
    # 3. Если всё еще мало, добавляем случайные игры
    if len(recommendations) < limit:
        random_games = Game.query.filter(
            ~Game.id.in_(all_user_game_ids),
            ~Game.id.in_([r['game'].id for r in recommendations])
        ).order_by(func.random()).limit(limit - len(recommendations)).all()
        
        for game in random_games:
            recommendations.append({
                'game': game,
                'reason': 'Случайная рекомендация, попробуй что-то новое',
                'type': 'random'
            })
    
    return recommendations[:limit]

def calculate_gamer_profile(user_id):
    """Рассчитывает профиль геймера на основе пройденных игр"""
    
    with app.app_context():
        # Получаем игры со статусом 'played'
        played_games = db.session.query(Game).join(
            UserGameStatus, UserGameStatus.game_id == Game.id
        ).filter(
            UserGameStatus.user_id == user_id,
            UserGameStatus.status == 'played'
        ).all()
        
        dropped_games = db.session.query(Game).join(
            UserGameStatus, UserGameStatus.game_id == Game.id
        ).filter(
            UserGameStatus.user_id == user_id,
            UserGameStatus.status == 'dropped'
        ).count()
        
        total_played = len(played_games)
        if total_played == 0:
            return None
        
        # Собираем теги из пройденных игр
        tag_counter = {}
        story_depth_sum = 0
        logic_games = 0
        action_games = 0
        horror_games = 0
        puzzle_games = 0
        strategy_games = 0
        creative_games = 0
        hard_games = 0
        
        for game in played_games:
            story_depth_sum += game.story_depth or 5
            
            for tag in game.tags:
                tag_name = tag.name
                tag_counter[tag_name] = tag_counter.get(tag_name, 0) + 1
                
                # Классифицируем теги
                if tag_name in ['Головоломка', 'Детектив', 'Стратегия', 'Пазл']:
                    logic_games += 1
                if tag_name in ['Экшен', 'Шутер', 'Сражения']:
                    action_games += 1
                if tag_name in ['Хоррор', 'Ужасы']:
                    horror_games += 1
                if tag_name in ['Головоломка', 'Пазл', 'Детектив']:
                    puzzle_games += 1
                if tag_name in ['Стратегия', 'Тактика']:
                    strategy_games += 1
                if tag_name in ['Песочница', 'Строительство', 'Творчество']:
                    creative_games += 1
                if tag_name in ['Сложная', 'Souls-like', 'Выживание']:
                    hard_games += 1
        
        # Нормализуем значения (0-100)
        def normalize(value, max_val=None):
            if max_val:
                return min(100, int(value / max_val * 100)) if max_val > 0 else 0
            return min(100, value)
        
        # Рассчитываем характеристики
        avg_story_depth = story_depth_sum / total_played if total_played > 0 else 5
        
        # 1. Усидчивость (на основе story_depth и кол-ва пройденных игр)
        patience = normalize(avg_story_depth * 10, 100)
        
        # 2. Концентрация (% пройденных от общего числа начатых)
        total_started = total_played + dropped_games
        focus = normalize(int(total_played / total_started * 100)) if total_started > 0 else 50
        
        # 3. IQ/Находчивость (на основе логических игр)
        iq = normalize(logic_games * 15, 100) if logic_games > 0 else 20
        
        # 4. Поток (Flow) - на основе story_depth и RPG тегов
        flow = normalize(avg_story_depth * 12, 100)
        
        # 5. Реакция (на основе экшен-игр)
        reaction = normalize(action_games * 12, 100)
        
        # 6. Стрессоустойчивость (на основе хорроров и сложных игр)
        stress_tolerance = normalize((horror_games + hard_games) * 15, 100)
        
        # 7. Креативность (на основе песочниц/творческих игр)
        creativity = normalize(creative_games * 20, 100)
        
        return {
            'patience': patience,           # Усидчивость
            'focus': focus,                 # Концентрация
            'iq': iq,                       # IQ/Находчивость
            'flow': flow,                   # Поток
            'reaction': reaction,           # Скорость реакции
            'stress_tolerance': stress_tolerance,  # Стрессоустойчивость
            'creativity': creativity,       # Креативность
            'total_played': total_played,
            'avg_story_depth': round(avg_story_depth, 1)
        }

def get_recommendations_by_profile(user_id, limit=4):
    """Рекомендации на основе профиля геймера (сильные стороны) с пояснениями"""
    with app.app_context():
        profile = calculate_gamer_profile(user_id)
        if not profile:
            return []
        
        # Определяем сильные стороны пользователя (где значение > 60)
        strong_traits = []
        trait_scores = {
            'patience': profile['patience'],
            'focus': profile['focus'],
            'iq': profile['iq'],
            'flow': profile['flow'],
            'reaction': profile['reaction'],
            'stress_tolerance': profile['stress_tolerance'],
            'creativity': profile['creativity']
        }
        
        # Сортируем по убыванию и берём топ-3 характеристики
        sorted_traits = sorted(trait_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        strong_traits = [trait for trait, _ in sorted_traits]
        
        # Маппинг характеристик на теги/жанры и пояснения
        trait_to_tags = {
            'patience': {
                'tags': ['RPG', 'Сюжет', 'Глубокий сюжет', 'Открытый мир', 'Длинная'],
                'reason': 'ты усидчивый и любишь длинные игры с глубоким сюжетом'
            },
            'focus': {
                'tags': ['Стелс', 'Концентрация', 'Внимание', 'Тактика'],
                'reason': 'ты умеешь концентрироваться и любишь продуманные механики'
            },
            'iq': {
                'tags': ['Головоломка', 'Детектив', 'Стратегия', 'Выбор влияет', 'Логическая'],
                'reason': 'у тебя отличная логика и тебе нравятся головоломки'
            },
            'flow': {
                'tags': ['Сюжет', 'Атмосферное', 'Погружение', 'Квест', 'Нарратив'],
                'reason': 'ты ценишь погружение в сюжет и атмосферу'
            },
            'reaction': {
                'tags': ['Экшен', 'Шутер', 'Сражения', 'Быстрый', 'Динамичный'],
                'reason': 'у тебя хорошая реакция и ты любишь динамичные игры'
            },
            'stress_tolerance': {
                'tags': ['Хоррор', 'Сложная', 'Souls-like', 'Выживание', 'Триллер'],
                'reason': 'ты стрессоустойчив и не боишься сложных испытаний'
            },
            'creativity': {
                'tags': ['Песочница', 'Строительство', 'Творчество', 'Инди', 'Эксперименты'],
                'reason': 'у тебя развито творческое мышление'
            }
        }
        
        # Собираем все теги для рекомендаций
        recommended_tags = []
        recommendation_reasons = {}
        
        for trait in strong_traits:
            trait_info = trait_to_tags.get(trait, {})
            for tag in trait_info.get('tags', []):
                if tag not in recommended_tags:
                    recommended_tags.append(tag)
                    recommendation_reasons[tag] = trait_info.get('reason', f'тебе подходит характеристика {trait}')
        
        # ID игр, которые уже есть у пользователя
        user_game_ids = [ug.game_id for ug in UserGameStatus.query.filter_by(user_id=user_id).all()]
        
        # Ищем игры по тегам
        recommendations = []
        if recommended_tags:
            tag_objects = Tag.query.filter(Tag.name.in_(recommended_tags)).all()
            tag_ids = [tag.id for tag in tag_objects]
            
            if tag_ids:
                # Получаем игры с подсчётом совпадающих тегов
                games_with_matches = db.session.query(
                    Game, func.count(GameTags.tag_id).label('match_count')
                ).join(GameTags).filter(
                    GameTags.tag_id.in_(tag_ids),
                    ~Game.id.in_(user_game_ids)
                ).group_by(Game.id).order_by(
                    func.count(GameTags.tag_id).desc()
                ).limit(limit * 2).all()
                
                # Формируем результат с пояснениями
                for game, match_count in games_with_matches:
                    # Находим, какие именно характеристики подошли
                    matched_traits = []
                    for trait in strong_traits:
                        trait_tags = trait_to_tags.get(trait, {}).get('tags', [])
                        game_tag_names = [tag.name for tag in game.tags]
                        if any(tag in trait_tags for tag in game_tag_names):
                            matched_traits.append(trait)
                    
                    # Создаём пояснение
                    trait_names = {
                        'patience': 'усидчивость',
                        'focus': 'концентрация',
                        'iq': 'логика и находчивость',
                        'flow': 'погружение в сюжет',
                        'reaction': 'реакция',
                        'stress_tolerance': 'стрессоустойчивость',
                        'creativity': 'креативность'
                    }
                    
                    # Правильные формы для слова "развит/развита/развито"
                    feminine_traits = ['focus', 'reaction', 'stress_tolerance', 'creativity', 'patience']  # развита
                    neuter_traits = ['iq', 'flow']  # развито
                    
                    if matched_traits:
                        if len(matched_traits) == 1:
                            trait = matched_traits[0]
                            trait_text = trait_names.get(trait, trait)
                            if trait in feminine_traits:
                                reason = f"Рекомендуется, потому что у тебя развита {trait_text}"
                            elif trait in neuter_traits:
                                reason = f"Рекомендуется, потому что у тебя развито {trait_text}"
                            else:
                                reason = f"Рекомендуется, потому что у тебя развиты {trait_text}"
                        else:
                            traits_text = ', '.join([trait_names.get(t, t) for t in matched_traits[:2]])
                            reason = f"Рекомендуется, потому что у тебя развиты {traits_text}"
                    else:
                        reason = "Подходит под твой игровой профиль"
                    
                    recommendations.append({
                        'game': game,
                        'reason': reason,
                        'match_count': match_count
                    })
                    
                    if len(recommendations) >= limit:
                        break
        
        # Если не хватило, добавляем популярные игры с общим пояснением
        if len(recommendations) < limit:
            popular_games = Game.query.filter(
                ~Game.id.in_(user_game_ids),
                ~Game.id.in_([r['game'].id for r in recommendations])
            ).order_by(func.random()).limit(limit - len(recommendations)).all()
            
            for game in popular_games:
                recommendations.append({
                    'game': game,
                    'reason': 'Популярная игра, которая может тебе понравиться',
                    'match_count': 0
                })
        
        return recommendations[:limit]

@app.route('/test-500')
def test_500():
    return non_existent_variable  # вызовет NameError

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    filter_status = request.args.get('status', 'all')
    per_page = 12
    
    # Получаем игры с фильтром по статусу (если выбран)
    games = []
    pagination = None
    
    # Словарь статусов для всех игр пользователя (для отображения значков)
    user_game_statuses = {}
    
    if current_user.is_authenticated:
        # Получаем все статусы пользователя
        user_statuses = UserGameStatus.query.filter_by(user_id=current_user.id).all()
        for us in user_statuses:
            user_game_statuses[us.game_id] = us.status
    
    if filter_status != 'all' and current_user.is_authenticated:
        # Находим ID игр с выбранным статусом
        user_game_ids = [ug.game_id for ug in UserGameStatus.query.filter_by(
            user_id=current_user.id, 
            status=filter_status
        ).all()]
        
        if user_game_ids:
            pagination = Game.query.filter(Game.id.in_(user_game_ids)).paginate(
                page=page, per_page=per_page, error_out=False
            )
            games = pagination.items
        else:
            games = []
            pagination = None
    else:
        # Обычная пагинация для всех игр
        pagination = Game.query.paginate(page=page, per_page=per_page, error_out=False)
        games = pagination.items
    
    # Получаем рекомендации
    recommended_games = []
    if current_user.is_authenticated:
        recommended_games = get_recommendations_for_user(current_user.id, limit=4)
    
    # Получаем статусы игр пользователя для отображения категорий
    user_status_counts = {}
    user_status_games = {}
    if current_user.is_authenticated:
        statuses = UserGameStatus.query.filter_by(user_id=current_user.id).all()
        for s in statuses:
            user_status_counts[s.status] = user_status_counts.get(s.status, 0) + 1
        
        for status in ['played', 'playing', 'want', 'dropped']:
            games_with_status = UserGameStatus.query.filter_by(
                user_id=current_user.id, 
                status=status
            ).join(Game).limit(3).all()
            user_status_games[status] = [ug.game for ug in games_with_status]
    
    category_title = ''
    if filter_status != 'all':
        status_names = {
            'played': 'Пройденные игры',
            'playing': 'Игры, в которые я играю',
            'want': 'Игры, которые я планирую',
            'dropped': 'Игры, которые я бросил'
        }
        category_title = status_names.get(filter_status, 'Игры')
    
    return render_template(
        'index.html', 
        games=games, 
        pagination=pagination,
        recommended_games=recommended_games,
        user_status_counts=user_status_counts,
        user_status_games=user_status_games,
        current_filter=filter_status,
        category_title=category_title,
        is_empty_category=(filter_status != 'all' and not games),
        user_game_statuses=user_game_statuses  # ← передаём статусы игр пользователя
    )

@app.route('/game/<int:game_id>')
def game_page(game_id):
    game = Game.query.get_or_404(game_id)
    
    user_status = None
    if current_user.is_authenticated:
        user_status = UserGameStatus.query.filter_by(
            user_id=current_user.id, 
            game_id=game_id
        ).first()
    
    # Похожие игры на основе тегов
    similar_games = []
    if game.tags:
        # Берем ID тегов текущей игры
        tag_ids = [tag.id for tag in game.tags]
        
        # Ищем игры с такими же тегами, исключая текущую
        similar_games = Game.query.join(GameTags).filter(
            GameTags.tag_id.in_(tag_ids),
            Game.id != game.id
        ).group_by(Game.id).order_by(
            db.func.count(GameTags.tag_id).desc()
        ).limit(4).all()
    
    return render_template(
        'game.html', 
        game=game, 
        user_status=user_status,
        similar_games=similar_games
    )

@app.route('/api/game/<int:game_id>/status', methods=['POST'])
@login_required
def update_status(game_id):
    status = request.json.get('status')
    
    user_status = UserGameStatus.query.filter_by(
        user_id=current_user.id, 
        game_id=game_id
    ).first()
    
    if user_status:
        user_status.status = status
        user_status.updated_at = datetime.now()
    else:
        user_status = UserGameStatus(
            user_id=current_user.id,
            game_id=game_id,
            status=status
        )
        db.session.add(user_status)
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/game/<int:game_id>/status', methods=['DELETE'])
@login_required
def delete_status(game_id):
    """Удаление статуса игры"""
    user_status = UserGameStatus.query.filter_by(
        user_id=current_user.id, 
        game_id=game_id
    ).first()
    
    if user_status:
        db.session.delete(user_status)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Статус удален'})
    
    return jsonify({'success': False, 'message': 'Статус не найден'}), 404

@app.route('/api/theme', methods=['POST'])
@login_required
def save_theme():
    """Сохраняет выбранную тему пользователя"""
    data = request.get_json()
    theme = data.get('theme')
    
    # Проверяем, что тема допустима
    allowed_themes = ['light', 'dark', 'neon', 'monochrome']
    if theme in allowed_themes:
        current_user.theme_preference = theme
        db.session.commit()
        return jsonify({'success': True, 'theme': theme})
    
    return jsonify({'success': False, 'error': 'Invalid theme'}), 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        # Проверяем и пароль через check_password
        if user and user.check_password(password):
            login_user(user)
            flash(f'С возвращением, {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Проверка длины пароля
        if len(password) < 6:
            flash('Пароль должен быть минимум 6 символов')
            return render_template('register.html')

        # Проверка длины пароля (серверная)
        if len(password) > 50:
            flash('Пароль не может быть длиннее 50 символов', 'danger')
            return render_template('register.html', username=username, email=email)

        # Проверка существования пользователя
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует')
            return render_template('register.html')
        
        # Создание пользователя с хешированным паролем
        user = User(
            username=username,
            email=email
        )
        user.set_password(password)  # ← хешируем пароль
        
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        flash('Регистрация прошла успешно!', 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    statuses = UserGameStatus.query.filter_by(user_id=current_user.id).all()
    games_with_status = []
    for s in statuses:
        game = Game.query.get(s.game_id)
        if game:
            games_with_status.append({
                'game': game,
                'status': s.status,
                'updated': s.updated_at
            })
    return render_template('profile.html', games_with_status=games_with_status)

@app.route('/profile/stats')
@login_required
def profile_stats():
    profile = calculate_gamer_profile(current_user.id)
    recommendations_by_profile = get_recommendations_by_profile(current_user.id, limit=4)
    return render_template('profile_stats.html', stats=profile, recommended_by_profile=recommendations_by_profile)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(debug=debug_mode, port=5001)