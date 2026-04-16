import os
import sys
import json
import time
import requests
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

# ---------- Переменные окружения ----------
VK_GROUP_TOKEN = os.getenv("VK_GROUP_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not VK_GROUP_TOKEN or not VK_GROUP_ID or not OPENROUTER_API_KEY:
    print("ОШИБКА: Не заданы VK_GROUP_TOKEN, VK_GROUP_ID или OPENROUTER_API_KEY", file=sys.stderr)
    sys.exit(1)

try:
    VK_GROUP_ID = int(VK_GROUP_ID)
except ValueError:
    print("ОШИБКА: VK_GROUP_ID должен быть числом", file=sys.stderr)
    sys.exit(1)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-oss-120b:free"

# ---------- Данные о партнёрских сервисах ----------
OFFERS = {
    "foxford": {
        "name": "Фоксфорд",
        "full_description": (
            "🦊 Фоксфорд — онлайн-школа для детей и подростков.\n\n"
            "✅ Дошкольники: развивающие курсы, подготовка к школе, английский, логопед.\n"
            "✅ 1–11 классы: школьная программа, программирование, подготовка к ОГЭ/ЕГЭ и олимпиадам.\n"
            "✅ Преподаватели из МГУ, ВШЭ, МФТИ.\n"
            "✅ Домашняя школа с аттестатом, индивидуальные занятия и мини-группы.\n\n"
            "🔗 Ссылка: https://vk.cc/cWHs9c"
        ),
        "short_description": "Онлайн-школа для всех возрастов: подготовка к ЕГЭ, программирование, домашняя школа.",
        "link": "https://vk.cc/cWHs9c"
    },
    "100ballov": {
        "name": "100балльный репетитор",
        "full_description": (
            "💯 100балльный репетитор — подготовка к ОГЭ и ЕГЭ.\n\n"
            "✅ Медийные преподаватели, которые объясняют сложное простым языком.\n"
            "✅ Подходит даже с нулевым уровнем, материалы в одном месте.\n"
            "✅ Поддержка психолога, закрытые чаты.\n"
            "✅ Цена от 2690 ₽/мес.\n\n"
            "🔗 Ссылка: https://vk.cc/cWHswz"
        ),
        "short_description": "Подготовка к ОГЭ/ЕГЭ с топовыми преподавателями, от 2690 ₽/мес.",
        "link": "https://vk.cc/cWHswz"
    },
    "logopotam": {
        "name": "Онлайн Школа Логопотам",
        "full_description": (
            "🗣️ Логопотам — логопедические занятия онлайн по всему миру.\n\n"
            "✅ Помощь детям с дефектами речи.\n"
            "✅ Бесплатное пробное занятие.\n"
            "✅ Индивидуальный подход.\n\n"
            "🔗 Ссылка: https://vk.cc/cWHumr"
        ),
        "short_description": "Логопед онлайн для детей, бесплатное пробное занятие.",
        "link": "https://vk.cc/cWHumr"
    },
    "advance_kids": {
        "name": "Advance – курсы для детей",
        "full_description": (
            "🧠 Advance — развитие памяти, внимания, скорочтения.\n\n"
            "✅ Бесплатный марафон для родителей.\n"
            "✅ Курсы от 15 900 ₽.\n"
            "✅ Учим детей учиться эффективно и с удовольствием.\n\n"
            "🔗 Ссылка: https://vk.cc/cWHvkJ"
        ),
        "short_description": "Развитие когнитивных способностей у детей, марафон для родителей.",
        "link": "https://vk.cc/cWHvkJ"
    },
    "advance_english": {
        "name": "Advance – английский за 3 месяца",
        "full_description": (
            "🇬🇧 Advance English — ускоренное изучение английского.\n\n"
            "✅ Марафон «Как выучить английский за 3 месяца».\n"
            "✅ Подходит тем, кто учил годами, но не заговорил.\n"
            "✅ Курсы от 17 900 ₽.\n\n"
            "🔗 Ссылка: https://vk.cc/cWHvvI"
        ),
        "short_description": "Марафон и курсы для быстрого изучения английского языка.",
        "link": "https://vk.cc/cWHvvI"
    },
    "vikium": {
        "name": "Викиум",
        "full_description": (
            "🧩 Викиум — онлайн-тренажёры для мозга.\n\n"
            "✅ Развитие внимания, памяти, мышления.\n"
            "✅ Научные методики нейропсихологов.\n"
            "✅ Помогает в учёбе, работе и повседневной жизни.\n\n"
            "🔗 Ссылка: https://vk.cc/cWHvIp"
        ),
        "short_description": "Тренажёры для развития мозга на основе нейропсихологии.",
        "link": "https://vk.cc/cWHvIp"
    },
    "vsesdal": {
        "name": "Всё сдал!",
        "full_description": (
            "📝 Всё сдал! — помощь студентам с учебными работами.\n\n"
            "✅ Прямая связь с экспертами, гарантия возврата.\n"
            "✅ Цены в 2-3 раза ниже, бесплатные доработки.\n"
            "✅ Промокод SALE200 на 200 ₽.\n\n"
            "🔗 Ссылка: https://vk.cc/cWHvU2"
        ),
        "short_description": "Сервис помощи студентам: курсовые, рефераты, онлайн-помощь.",
        "link": "https://vk.cc/cWHvU2"
    },
    "online_school_1": {
        "name": "Онлайн-школа №1",
        "full_description": (
            "🏫 Онлайн-школа №1 — полноценное дистанционное обучение с 1 по 11 класс.\n\n"
            "✅ Живые уроки в мини-классах.\n"
            "✅ Аттестат государственного образца.\n"
            "✅ 2–5 уроков с учителями в день.\n"
            "✅ Доступно из любой точки мира.\n\n"
            "🔗 Ссылка: https://vk.cc/cWK3cR"
        ),
        "short_description": "Онлайн-школа с 1 по 11 класс с аттестатом гос. образца.",
        "link": "https://vk.cc/cWK3cR"
    }
}

# Категории для кнопок меню
CATEGORIES = {
    "repetitor": {
        "button": "🧑‍🏫 Репетитор / Подготовка к экзаменам",
        "offers": ["foxford", "100ballov"],
    },
    "online_school": {
        "button": "🏫 Онлайн-школа с 1 по 11 класс",
        "offers": ["online_school_1"],
    },
    "logoped": {
        "button": "🗣️ Логопед для ребёнка",
        "offers": ["logopotam"],
    },
    "development": {
        "button": "🧠 Развитие памяти и внимания",
        "offers": ["advance_kids", "vikium"],
    },
    "english": {
        "button": "🇬🇧 Обучение английскому языку",
        "offers": ["advance_english"],
    },
    "student_help": {
        "button": "📚 Помощь студентам",
        "offers": ["vsesdal"],
    }
}

# Кэш имён пользователей и сессии
user_names = {}
user_sessions = {}

# ---------- Вспомогательные функции ----------

def get_user_name(vk, user_id):
    """Получить имя пользователя VK (кэшируется)."""
    if user_id in user_names:
        return user_names[user_id]
    try:
        resp = vk.users.get(user_ids=[user_id], fields=['first_name'])
        if resp:
            name = resp[0]['first_name']
            user_names[user_id] = name
            return name
    except Exception as e:
        print(f"Ошибка получения имени: {e}", file=sys.stderr)
    return "друг"

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
    try:
        params = {
            "user_id": user_id,
            "message": text,
            "random_id": get_random_id()
        }
        if keyboard:
            params["keyboard"] = keyboard
        vk.messages.send(**params)
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка отправки сообщения: {e}", file=sys.stderr)

def build_offers_context(category_id):
    """Создаёт краткое описание сервисов категории для промпта."""
    offer_ids = CATEGORIES[category_id]["offers"]
    lines = []
    for oid in offer_ids:
        offer = OFFERS[oid]
        lines.append(f"- {offer['name']}: {offer['short_description']} Ссылка: {offer['link']}")
    return "\n".join(lines)

def find_mentioned_offer(text):
    """Ищет, упомянут ли какой-то сервис в тексте (по названию)."""
    text_lower = text.lower()
    for oid, offer in OFFERS.items():
        if offer['name'].lower() in text_lower:
            return oid
    return None

def call_openrouter(messages, retries=3):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 400
    }
    for attempt in range(retries):
        try:
            response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            elif response.status_code == 429:
                wait_time = 5 * (attempt + 1)
                print(f"Rate limit (429). Ожидание {wait_time} сек...", file=sys.stderr)
                time.sleep(wait_time)
                continue
            else:
                print(f"OpenRouter error {response.status_code}: {response.text}", file=sys.stderr)
                if attempt < retries - 1:
                    time.sleep(3)
                    continue
                return "Извините, сервис ИИ временно недоступен. Попробуйте позже."
        except Exception as e:
            print(f"OpenRouter exception: {e}", file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(3)
                continue
            return "Извините, произошла ошибка при обращении к ИИ. Попробуйте позже."
    return "Извините, сервис перегружен. Пожалуйста, повторите попытку через минуту."

def start_dialog(user_id, category_id):
    offers_context = build_offers_context(category_id)
    system_prompt = (
        "Ты — Учебный Навигатор, заботливый и понимающий помощник. Твоя задача — проявить участие, "
        "задать 1-2 коротких вопроса, показать, что ты действительно хочешь помочь. Отвечай кратко "
        "(1-2 предложения), дружелюбно, без рекламных фраз. Через 3-4 сообщения, когда почувствуешь доверие, "
        "ненавязчиво предложи подходящий сервис как решение проблемы. Ссылку дай один раз. "
        "Если пользователь просит рассказать подробнее о сервисе, используй готовое описание из информации ниже. "
        f"Доступные сервисы в этой категории:\n{offers_context}"
    )
    first_message = (
        "Здравствуйте! 💫 Я здесь, чтобы помочь вам найти хорошее решение в мире образования. "
        "Расскажите, что вас беспокоит или какую задачу вы сейчас решаете?"
    )
    user_sessions[user_id] = {
        "state": "dialog",
        "category": category_id,
        "history": [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": first_message}
        ],
        "last_offer_sent": None
    }
    return first_message

def continue_dialog(user_id, user_message, vk=None):
    session = user_sessions.get(user_id)
    if not session or session["state"] != "dialog":
        return None

    # Проверка: не просит ли пользователь подробнее о сервисе?
    # Ключевые фразы для локального ответа без ИИ
    detail_keywords = ["подробнее", "расскажи подробнее", "что за", "что такое", "как работает"]
    if any(kw in user_message.lower() for kw in detail_keywords):
        # Ищем, какой сервис упоминался последним в ответах ассистента
        last_offer = session.get("last_offer_sent")
        if not last_offer:
            # Попробуем найти упоминание в самом сообщении пользователя
            last_offer = find_mentioned_offer(user_message)
        if last_offer and last_offer in OFFERS:
            offer = OFFERS[last_offer]
            reply = offer["full_description"]
            session["history"].append({"role": "user", "content": user_message})
            session["history"].append({"role": "assistant", "content": reply})
            return reply

    # Если не запрос подробностей, отправляем в ИИ
    session["history"].append({"role": "user", "content": user_message})
    reply = call_openrouter(session["history"])
    session["history"].append({"role": "assistant", "content": reply})

    # Проверяем, содержит ли ответ ссылку на какой-либо сервис, чтобы запомнить
    for oid, offer in OFFERS.items():
        if offer["link"] in reply or offer["name"].lower() in reply.lower():
            session["last_offer_sent"] = oid
            break

    # Ограничение длины истории
    if len(session["history"]) > 21:
        session["history"] = [session["history"][0]] + session["history"][-20:]

    return reply

def reset_to_menu(user_id):
    user_sessions[user_id] = {"state": "menu"}

# ---------- Основной цикл ----------
def main():
    vk_session = vk_api.VkApi(token=VK_GROUP_TOKEN)
    vk = vk_session.get_api()

    try:
        group_info = vk.groups.getById(group_id=VK_GROUP_ID)
        print(f"Токен VK действителен, группа: {group_info[0]['name']}")
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка токена VK или ID группы: {e}", file=sys.stderr)
        sys.exit(1)

    longpoll = VkLongPoll(vk_session, group_id=VK_GROUP_ID, wait=25)
    print("Бот запущен и ожидает сообщений...")

    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
                    user_id = event.user_id
                    text = event.text.strip()

                    # Получаем имя пользователя (один раз)
                    user_name = get_user_name(vk, user_id)

                    if user_id not in user_sessions:
                        user_sessions[user_id] = {"state": "menu"}

                    state = user_sessions[user_id]["state"]

                    # Возврат в меню
                    if text.lower() in ["меню", "вернуться в меню", "🏠 вернуться в меню", "/start", "начать"]:
                        reset_to_menu(user_id)
                        send_message(
                            vk, user_id,
                            f"👋 Рад(а) вас видеть, {user_name}! Я Учебный Навигатор. Выберите, что вас интересует:",
                            keyboard=get_main_keyboard()
                        )
                        continue

                    # Главное меню
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
                                f"{user_name}, {first_reply}",
                                keyboard=get_back_keyboard()
                            )
                        else:
                            send_message(
                                vk, user_id,
                                f"{user_name}, пожалуйста, выберите одну из кнопок ниже:",
                                keyboard=get_main_keyboard()
                            )
                        continue

                    # Диалог с ИИ
                    elif state == "dialog":
                        vk.messages.setActivity(user_id=user_id, type="typing")
                        reply = continue_dialog(user_id, text, vk)
                        if reply:
                            # Не добавляем имя каждый раз, чтобы не перегружать
                            send_message(
                                vk, user_id,
                                reply,
                                keyboard=get_back_keyboard()
                            )
                        else:
                            reset_to_menu(user_id)
                            send_message(
                                vk, user_id,
                                f"{user_name}, что-то пошло не так. Давайте начнём заново.",
                                keyboard=get_main_keyboard()
                            )
                        continue

        except requests.exceptions.ReadTimeout:
            print("Таймаут Long Poll, переподключаюсь...", file=sys.stderr)
            time.sleep(1)
            continue
        except requests.exceptions.ConnectionError as e:
            print(f"Ошибка соединения: {e}, переподключаюсь...", file=sys.stderr)
            time.sleep(5)
            continue
        except Exception as e:
            print(f"Неизвестная ошибка в цикле: {e}", file=sys.stderr)
            time.sleep(5)
            continue

if __name__ == "__main__":
    main()
