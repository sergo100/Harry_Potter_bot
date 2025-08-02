# Harry Potter bot
# Автор: Сергей Сергиенко
# Год: 2025
# Telegram: @space_ranger3209
# Github: https://github.com/sergo100
# Все права защищены

import json
import logging
import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from dotenv import load_dotenv

# Загрузка токена из .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Настройка логирования
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- Загрузка вопросов и персонажей (пути БЕЗ 'potter_bot/', т.к. запускаем из potter_bot) ---
try:
    with open("questions.json", "r", encoding="utf-8") as f:
        questions = json.load(f)
except FileNotFoundError:
    logging.error("⛔️ ОШИБКА: Файл 'questions.json' не найден. Убедитесь, что он находится в папке 'potter_bot'.")
    questions = [] # Инициализация пустым списком, чтобы избежать ошибок

try:
    with open("character_results.json", "r", encoding="utf-8") as f:
        character_results = json.load(f)
except FileNotFoundError:
    logging.error("⛔️ ОШИБКА: Файл 'character_results.json' не найден. Убедитесь, что он находится в папке 'potter_bot'.")
    character_results = {} # Инициализация пустым словарем

# Пользовательские сессии
user_sessions = {}

# Функция для отображения главного меню с кнопкой "Начать"
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id_override=None):
    keyboard = [[KeyboardButton("Начать")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    target_chat_id = chat_id_override if chat_id_override else update.effective_chat.id

    await context.bot.send_message(
        chat_id=target_chat_id,
        text="Нажмите 'Начать', чтобы запустить тест.",
        reply_markup=reply_markup
    )


# Приветствие (вызывается по /start или кнопке "Начать")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Инициализируем user_scores для всех персонажей с 0 очками
    initial_scores = {char_name: 0 for char_name in character_results.keys()}
    user_sessions[user_id] = {"current_q": 0, "scores": initial_scores}
    
    inline_keyboard = [
        [InlineKeyboardButton("Начать тест", callback_data="start_quiz")],
        [InlineKeyboardButton("Поддержать автора", callback_data="donate")],
        [InlineKeyboardButton("Об авторе", callback_data="about_author")] # Ваша кнопка "Об авторе"
    ]
    inline_reply_markup = InlineKeyboardMarkup(inline_keyboard)

    welcome_image_path = "assets/welcome.jpg"
    try:
        await update.message.reply_photo(
            photo=open(welcome_image_path, "rb"), # Открытие файла прямо здесь
            caption="🧙‍♂️ Добро пожаловать в тест: *Кто ты из Гарри Поттера?*\n\nОтветь на несколько вопросов и узнай, кем бы ты был в волшебном мире!",
            parse_mode="Markdown",
            reply_markup=inline_reply_markup
        )
    except FileNotFoundError:
        logging.error(f"⛔️ ОШИБКА: Файл '{welcome_image_path}' не найден. Убедитесь, что он находится в папке 'potter_bot/assets/'.")
        await update.message.reply_text(
            "🧙‍♂️ Добро пожаловать в тест: *Кто ты из Гарри Поттера?*\n\nОтветь на несколько вопросов и узнай, кем бы ты был в волшебном мире!",
            parse_mode="Markdown",
            reply_markup=inline_reply_markup
        )
    except Exception as e:
        logging.error(f"⛔️ ОШИБКА при отправке фото: {e}")
        await update.message.reply_text(
            "🧙‍♂️ Добро пожаловать в тест: *Кто ты из Гарри Поттера?*\n\nОтветь на несколько вопросов и узнай, кем бы ты был в волшебном мире!",
            parse_mode="Markdown",
            reply_markup=inline_reply_markup
        )
    
    await show_main_menu(update, context)


# Обработка кнопок
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id

    if query.data == "start_quiz":
        # Переинициализация очков для всех персонажей при старте теста
        initial_scores = {char_name: 0 for char_name in character_results.keys()}
        user_sessions[user_id] = {"current_q": 0, "scores": initial_scores}
        await send_question(query, context)
    elif query.data.startswith("answer_"):
        choice_index = int(query.data.split("_")[1]) # Получаем индекс выбранного ответа (0, 1, 2, 3)
        session = user_sessions.get(user_id)
        if session:
            current_q_index = session["current_q"]
            if current_q_index < len(questions):
                current_question = questions[current_q_index]
                selected_option = current_question["options"][choice_index]
                
                # Добавляем очки за выбранный ответ
                for char_name, score_value in selected_option.get("scores", {}).items():
                    # Убедимся, что персонаж существует в character_results, прежде чем добавлять очки
                    if char_name in session["scores"]:
                        session["scores"][char_name] += score_value
                    else:
                        logging.warning(f"⚠️ ПРЕДУПРЕЖДЕНИЕ: Персонаж '{char_name}' из 'questions.json' не найден в 'character_results.json'. Очки не будут добавлены.")


                session["current_q"] += 1
                if session["current_q"] < len(questions):
                    await send_question(query, context)
                else:
                    await show_result(query, context, session["scores"]) # Передаем user_scores
            else:
                await query.edit_message_text("Тест завершен. Нажмите 'Пройти ещё раз' или 'Начать'.")
        else:
            await query.edit_message_text("Кажется, ваша сессия устарела. Нажмите 'Начать тест' снова.")
    elif query.data == "donate":
        donate_qr_path = "assets/donate_qr.png"
        try:
            await query.message.reply_photo(
                photo=open(donate_qr_path, "rb"), # Открытие файла прямо здесь
                caption="💖 Спасибо за поддержку!",
            )
        except FileNotFoundError:
            logging.error(f"⛔️ ОШИБКА: Файл '{donate_qr_path}' не найден. Убедитесь, что он находится в папке 'potter_bot/assets/'.")
            await query.message.reply_text("💖 Спасибо за поддержку! (QR-код не найден)")
        except Exception as e:
            logging.error(f"⛔️ ОШИБКА при отправке QR-кода: {e}")
            await query.message.reply_text("💖 Спасибо за поддержку! (Произошла ошибка при отправке QR-кода)")
    elif query.data == "about_author":
        await query.message.reply_text(
            "Привет! Я - бот, созданный для развлечения. Мой автор очень любит Гарри Поттера и старался сделать этот тест интересным для фанатов! ✨"
            "\n\nЕсли у вас есть предложения или вы хотите связаться пишите в телеграмм\n"
            "Автор: Сергей Сергиенко\n"
            "Telegram: @space_ranger3209\n" 
            "Github: https://github.com/sergo100\n"
            "© 2025 Все права защищены" 
             
        )
    elif query.data == "restart":
        # Переинициализация очков для всех персонажей при рестарте
        initial_scores = {char_name: 0 for char_name in character_results.keys()}
        user_sessions[user_id] = {"current_q": 0, "scores": initial_scores}
        await send_question(query, context)

# Отправка вопроса
async def send_question(query, context):
    user_id = query.from_user.id
    session = user_sessions[user_id]
    q_index = session["current_q"]

    if not questions:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Извините, вопросы для теста еще не загружены. Пожалуйста, сообщите администратору.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Начать заново", callback_data="start_quiz")]])
        )
        logging.error("⛔️ ОШИБКА: Список вопросов пуст! Проверьте 'questions.json'.")
        return

    if q_index >= len(questions):
        logging.error(f"⛔️ ОШИБКА: Попытка получить вопрос с индексом {q_index}, но всего вопросов {len(questions)}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Произошла ошибка при загрузке следующего вопроса. Пожалуйста, попробуйте перезапустить тест.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Начать заново", callback_data="start_quiz")]])
        )
        return

    q = questions[q_index]

    # Создаем кнопки с текстом из options
    keyboard = []
    for i, option_data in enumerate(q["options"]):
        # option_data теперь словарь, поэтому используем option_data["text"]
        keyboard.append([InlineKeyboardButton(option_data["text"], callback_data=f"answer_{i}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.message.delete()
    except Exception as e:
        logging.warning(f"⚠️ ПРЕДУПРЕЖДЕНИЕ: Не удалось удалить сообщение: {e}")

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"❓ *Вопрос {q_index + 1} из {len(questions)}:*\n\n{q['question']}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Подведение итогов
async def show_result(query, context, user_scores):
    # Если character_results пуст, сразу сообщаем об ошибке
    if not character_results:
        logging.error("⛔️ ОШИБКА: character_results.json пуст или не загружен корректно. Невозможно определить персонажа.")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Извините, произошла внутренняя ошибка при определении персонажа. Пожалуйста, сообщите администратору.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Начать заново", callback_data="start_quiz")]])
        )
        await show_main_menu(update=None, context=context, chat_id_override=query.message.chat_id)
        return

    # Находим персонажа с наибольшим количеством очков
    dominant_character_name = None
    if not user_scores or all(score == 0 for score in user_scores.values()):
        logging.warning("⚠️ ПРЕДУПРЕЖДЕНИЕ: Все очки персонажей равны нулю или словарь пуст. Возможно, вопросы не дают очков.")
        # Дефолтный персонаж, если ни у кого нет очков.
        # Попытаемся взять Гарри Поттера, если он есть
        if "Гарри Поттер" in character_results:
            dominant_character_name = "Гарри Поттер"
        else:
            # Если Гарри нет, возьмем первого попавшегося, если character_results не пуст
            dominant_character_name = next(iter(character_results), None)
            
        if dominant_character_name is None: # Если character_results все еще пуст или не удалось найти дефолтного
            logging.error("⛔️ ОШИБКА: character_results пуст или не содержит дефолтных персонажей.")
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Извините, не удалось определить вашего персонажа. Возможно, отсутствуют данные.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Начать заново", callback_data="start_quiz")]])
            )
            await show_main_menu(update=None, context=context, chat_id_override=query.message.chat_id)
            return
    else:
        dominant_character_name = max(user_scores, key=user_scores.get)

    # Теперь character_results точно не пуст и dominant_character_name не None
    if dominant_character_name not in character_results:
        logging.error(f"⛔️ ОШИБКА: Имя персонажа '{dominant_character_name}' (найденное по очкам) не найдено в 'character_results.json'. Проверьте файл.")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Не удалось определить вашего персонажа из-за ошибки в данных результатов. Пожалуйста, попробуйте еще раз.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Начать заново", callback_data="start_quiz")]])
        )
        await show_main_menu(update=None, context=context, chat_id_override=query.message.chat_id)
        return

    character = character_results[dominant_character_name]
    # Добавленная строка 'name' для каждого персонажа в character_results.json должна решить проблему KeyError
    # Она была добавлена в предыдущем ответе при предоставлении character_results.json
    image_path = f"assets/{character['image']}" 
    
    inline_keyboard = [
        [InlineKeyboardButton("Пройти ещё раз", callback_data="restart")],
        [InlineKeyboardButton("Поддержать автора", callback_data="donate")]
    ]
    inline_reply_markup = InlineKeyboardMarkup(inline_keyboard)

    try:
        await query.message.delete()
    except Exception as e:
        logging.warning(f"⚠️ ПРЕДУПРЕЖДЕНИЕ: Не удалось удалить сообщение с вопросом: {e}")

    try:
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=open(image_path, "rb"),
            caption=f"🧙‍♀️ *Ты — {character['name']}!*\n\n_{character['description']}_",
            parse_mode="Markdown",
            reply_markup=inline_reply_markup
        )
    except FileNotFoundError:
        logging.error(f"⛔️ ОШИБКА: Файл '{image_path}' для персонажа '{character['name']}' не найден. Убедитесь, что он находится в папке 'potter_bot/assets/'.")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🧙‍♀️ *Ты — {character['name']}!*\n\n_{character['description']}_ (Изображение не найдено)",
            parse_mode="Markdown",
            reply_markup=inline_reply_markup
        )
    except Exception as e:
        logging.error(f"⛔️ ОШИБКА при отправке фото персонажа: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🧙‍♀️ *Ты — {character['name']}!*\n\n_{character['description']}_ (Произошла ошибка при отправке изображения)",
            parse_mode="Markdown",
            reply_markup=inline_reply_markup
        )
    
    await show_main_menu_after_test(query, context)

async def show_main_menu_after_test(query, context):
    keyboard = [[KeyboardButton("Начать")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Тест завершен. Вы можете пройти его снова, нажав 'Начать'.",
        reply_markup=reply_markup
    )


# Запуск бота
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.Regex("^Начать$"), start))

    print("Бот запущен.")
    app.run_polling()