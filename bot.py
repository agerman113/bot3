import os
import sys
import json
import requests
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

# ---------- Получение токена и ID группы ----------
VK_GROUP_TOKEN = os.getenv("VK_GROUP_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")

if not VK_GROUP_TOKEN:
    print("ОШИБКА: Не найден VK_GROUP_TOKEN в переменных окружения.", file=sys.stderr)
    sys.exit(1)

if not VK_GROUP_ID:
    print("ОШИБКА: Не найден VK_GROUP_ID в переменных окружения.", file=sys.stderr)
    sys.exit(1)

# Убедимся, что GROUP_ID — целое число
try:
    VK_GROUP_ID = int(VK_GROUP_ID)
except ValueError:
    print("ОШИБКА: VK_GROUP_ID должен быть числом.", file=sys.stderr)
    sys.exit(1)

# ---------- Конфигурация OpenRouter ----------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("ОШИБКА: Не найден OPENROUTER_API_KEY", file=sys.stderr)
    sys.exit(1)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

# ---------- Данные о партнёрских сервисах (без изменений) ----------
OFFERS = {
    "foxford": {
        "name": "Фоксфорд",
        "description": (
            "Онлайн-школа для дошкольников, школьников и учителей. "
            "Курсы по школьной программе, подготовка к ОГЭ/ЕГЭ, олимпиадам, "
            "программирование, английский, логопед. Преподаватели из МГУ, ВШЭ, МФТИ. "
            "Домашняя школа, индивидуальные занятия и мини-группы."
        ),
        "link": "https://vk.cc/cWHs9c"
    },
    "100ballov": {
        "name": "100балльный репетитор",
        "description": (
            "Подготовка к ОГЭ и ЕГЭ с медийными преподавателями. "
            "Понятные объяснения, курсы с нуля, все материалы в одном месте. "
            "Поддержка психолога, цена от 2690 ₽/мес."
        ),
        "link": "https://vk.cc/cWHswz"
    },
    "logopotam": {
        "name": "Онлайн Школа Логопотам",
        "description": (
            "Логопедические занятия онлайн по всему миру. "
            "Помощь детям с речью, бесплатное пробное занятие."
        ),
        "link": "https://vk.cc/cWHumr"
    },
    "advance_kids": {
        "name": "Advance – курсы для детей",
        "description": (
            "Развитие памяти, внимания, скорочтения и когнитивных способностей. "
            "Бесплатный марафон для родителей, курсы от 15 900 ₽."
        ),
        "link": "https://vk.cc/cWHvkJ"
    },
    "advance_english": {
        "name": "Advance – английский за 3 месяца",
        "description": (
            "Марафон по ускоренному изучению английского языка. "
            "Курсы от 17 900 ₽."
        ),
        "link": "https://vk.cc/cWHvvI"
    },
    "vikium": {
        "name": "Викиум",
        "description": (
            "Тренажёры для мозга: развитие внимания, памяти, мышления. "
            "Научно обоснованные методики, профилактика возрастных изменений."
        ),
        "link": "https://vk.cc/cWHvIp"
    },
    "vsesdal": {
        "name": "Всё сдал!",
        "description": (
            "Сервис помощи студентам: написание работ, консультации. "
            "Гарантия возврата, проверенные эксперты. Промокод SALE200 на 200 ₽."
        ),
        "link": "https://vk.cc/cWHvU2"
    }
}

# Категории для кнопок меню
CATEGORIES = {
    "repetitor": {
        "button": "🧑‍🏫 Репетитор / Подготовка к экзаменам",
        "offers": ["foxford", "100ballov"],
        "prompt_intro": "Пользователь ищет репетитора или курсы подготовки к ОГЭ/ЕГЭ."
    },
    "logoped": {
        "button": "🗣️ Логопед для ребёнка",
        "offers": ["logopotam"],
        "prompt_intro": "Пользователю нужен логопед онлайн."
    },
    "development": {
        "button": "🧠 Развитие памяти и внимания",
        "offers": ["advance_kids", "vikium"],
        "prompt_intro": "Пользователь хочет улучшить когнитивные способности или помочь ребёнку учиться эффективнее."
    },
    "english": {
        "button": "🇬🇧 Английский язык",
        "offers": ["advance_english"],
        "prompt_intro": "Пользователь интересуется изучением английского языка."
    },
    "student_help": {
        "button": "📚 Помощь студентам",
        "offers": ["vsesdal"],
        "prompt_intro": "Пользователю нужна помощь с учебными работами."
    }
}

# Хранилище состояний пользователей (в памяти)
user_sessions = {}

# ---------- Вспомогательные функции (без изменений) ----------

def get_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    cat_items = list(CATEGORIES.items())
    for i, (cat_id, cat_data) in enumerate(cat_items):
        keyboard.add_button(cat_data["button"], color=VkKeyboardColor.PRIMARY)
        if i < len(cat_items) - 1:
            keyboard.add_line()
    return keyboard.get_keyboard()

def get_back_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("🏠 Вернуться в меню", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def send_message(vk, user_id, text, keyboard=None):
    vk.method("messages.send", {
        "user_id": user_id,
        "message": text,
        "random_id": get_random_id(),
        "keyboard": keyboard
    })

def build_offers_text(category_id):
    offer_ids = CATEGORIES[category_id]["offers"]
    lines = ["**Рекомендованные сервисы:**\n"]
    for oid in offer_ids:
        offer = OFFERS[oid]
        lines.append(f"🔹 **{offer['name']}**")
        lines.append(f"{offer['description'][:200]}...")
        lines.append(f"🔗 Ссылка: {offer['link']}\n")
    return "\n".join(lines)

def call_openrouter(messages):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }
    response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print(f"OpenRouter error: {response.status_code} {response.text}", file=sys.stderr)
        return "Извините, произошла ошибка при обращении к ИИ. Попробуйте позже."

def start_dialog(user_id, category_id):
    offers_desc = build_offers_text(category_id)
    system_prompt = (
        "Ты — Учебный Навигатор, дружелюбный помощник в выборе образовательных услуг. "
        "Твоя задача: помочь пользователю, дать полезный совет и мягко подвести к переходу "
        "по партнёрской ссылке на подходящий сервис. Не будь навязчивым, сначала прояви участие, "
        "ответь на вопросы, а затем предложи конкретный сервис. "
        "Используй только те сервисы, которые указаны в информации. "
        "Не выдумывай ссылки.\n\n"
        f"Информация о доступных сервисах:\n{offers_desc}"
    )
    user_sessions[user_id] = {
        "state": "dialog",
        "category": category_id,
        "history": [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": "Здравствуйте! Я помогу вам найти подходящий образовательный сервис. Расскажите, что именно вас интересует?"}
        ]
    }
    return user_sessions[user_id]["history"][-1]["content"]

def continue_dialog(user_id, user_message):
    session = user_sessions.get(user_id)
    if not session or session["state"] != "dialog":
        return None
    session["history"].append({"role": "user", "content": user_message})
    reply = call_openrouter(session["history"])
    session["history"].append({"role": "assistant", "content": reply})
    if len(session["history"]) > 21:
        session["history"] = [session["history"][0]] + session["history"][-20:]
    return reply

def reset_to_menu(user_id):
    user_sessions[user_id] = {"state": "menu"}

# ---------- Основной обработчик ----------

def main():
    # Создаём сессию с токеном группы
    vk_session = vk_api.VkApi(token=VK_GROUP_TOKEN)

    try:
        vk = vk_session.get_api()
        # Проверка токена
        vk.groups.getById(group_id=VK_GROUP_ID)
        print("Токен VK действителен, группа найдена.")
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка токена VK или ID группы: {e}", file=sys.stderr)
        sys.exit(1)

    # Инициализация Long Poll для группы
    try:
        longpoll = VkLongPoll(vk_session, group_id=VK_GROUP_ID)
    except vk_api.exceptions.ApiError as e:
        print(f"Не удалось инициализировать LongPoll: {e}", file=sys.stderr)
        print("Убедитесь, что у токена есть доступ к сообщениям группы и Long Poll API включён.", file=sys.stderr)
        sys.exit(1)

    print("Бот запущен и ожидает сообщений...")

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
            user_id = event.user_id
            text = event.text.strip()

            if user_id not in user_sessions:
                user_sessions[user_id] = {"state": "menu"}

            state = user_sessions[user_id]["state"]

            # Возврат в меню
            if text.lower() in ["меню", "вернуться в меню", "🏠 вернуться в меню", "/start", "начать"]:
                reset_to_menu(user_id)
                send_message(
                    vk, user_id,
                    "👋 Привет! Я Учебный Навигатор — помогу выбрать лучший образовательный сервис.\n"
                    "Выберите, что вас интересует:",
                    keyboard=get_main_keyboard()
                )
                continue

            if state == "menu":
                selected_cat = None
                for cat_id, cat_data in CATEGORIES.items():
                    if cat_data["button"].lower() == text.lower():
                        selected_cat = cat_id
                        break

                if selected_cat:
                    first_reply = start_dialog(user_id, selected_cat)
                    send_message(
                        vk, user_id,
                        first_reply,
                        keyboard=get_back_keyboard()
                    )
                else:
                    send_message(
                        vk, user_id,
                        "Пожалуйста, выберите одну из кнопок ниже:",
                        keyboard=get_main_keyboard()
                    )
                continue

            elif state == "dialog":
                vk.method("messages.setActivity", {
                    "user_id": user_id,
                    "type": "typing"
                })
                reply = continue_dialog(user_id, text)
                if reply:
                    send_message(
                        vk, user_id,
                        reply,
                        keyboard=get_back_keyboard()
                    )
                else:
                    reset_to_menu(user_id)
                    send_message(
                        vk, user_id,
                        "Что-то пошло не так. Давайте начнём заново.",
                        keyboard=get_main_keyboard()
                    )
                continue

if __name__ == "__main__":
    main()
