"""
Telegram-бот «Анкета» (проект tgbot).
- 6 вопросов анкеты + система тегирования из «Роман Андреевич»
- Вопрос 7 про текущий домашний уход
- Генерация разбора кожи по тегам
- Создание ветки (топика) в закрытой супергруппе оператора
- Закрепление карточки клиента в топике
- Режим живого диалога (Топики <-> Клиент)
- Фильтрация внутренних заметок оператора (#...)
- Уведомление о блокировке бота пользователем
"""

import os
import re
import html
import asyncio
import logging
from typing import Optional, List, Dict, Any, Set

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramAPIError

import database as db
from webapp_server import WebAppServer

# ================== ЗАГРУЗКА .ENV (ЕСЛИ ЕСТЬ) ==================
def _load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k not in os.environ:
                        os.environ[k] = v

_load_env_file()

# ================== НАСТРОЙКА ЛОГОВ ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ================== КОНФИГУРАЦИЯ ==================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    logger.warning("⚠️ BOT_TOKEN не найден в переменных окружения. Укажите BOT_TOKEN для запуска бота.")
    BOT_TOKEN = "0000000000:AAPlaceholderTokenForTestingOnly0000"

# Список ID владельцев / администраторов
_owner_env = os.getenv("OWNER_IDS")
if _owner_env:
    try:
        OWNER_IDS = [int(x.strip()) for x in _owner_env.split(",") if x.strip().lstrip("-").isdigit()]
    except Exception:
        OWNER_IDS = [1745568601, 7875791813]
else:
    OWNER_IDS = [1745568601, 7875791813]

IMAGE_URL = "https://pbt.storage.yandexcloud.net/cp_upload/3226d6315635f4e60bebd98a6421ea7a_full.jpeg"

# Адрес и порт для встроенного веб-приложения (Telegram Mini App)
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip().rstrip("/")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8080"))

# Хранилище игнорируемых media_group_id для заметок оператора (#...)
IGNORED_MEDIA_GROUPS: Set[str] = set()


def format_dialog_window_text(client_id: int, operator_id: int) -> str:
    """Формирует визуальное диалоговое окно клиента с рамкой, шапкой, карточкой и историей."""
    client_info = db.get_user(client_id) or {}
    client_name = client_info.get("user_name") or f"Клиент {client_id}"
    username_display = f"@{client_info.get('username')}" if client_info.get('username') else f"ID: {client_id}"
    care_answer = client_info.get("care_answer") or "Не указан"

    history = db.get_chat_history(client_id, limit=10)
    if history:
        history_lines = []
        for m in history:
            time_str = m.get("created_at", "").split(" ")[-1] if m.get("created_at") else ""
            prefix = f"👤 <b>{html.escape(client_name)}</b>" if m["sender_type"] == "client" else "👩‍⚕️ <b>Вы</b>"
            time_label = f" <i>({time_str})</i>" if time_str else ""
            txt = html.escape(m.get("text", "")[:350])
            history_lines.append(f"{prefix}{time_label}:\n«{txt}»")
        history_block = "\n\n".join(history_lines)
    else:
        history_block = "<i>(Предыдущих сообщений в переписке пока нет)</i>"

    window_text = (
        "╔══════════════════════════════════════╗\n"
        f"💬 <b>ДИАЛОГОВОЕ ОКНО: {html.escape(client_name)}</b>\n"
        f"👤 <b>Клиент:</b> {html.escape(client_name)} ({username_display})\n"
        f"🆔 <code>{client_id}</code> | 🟢 <b>В ДИАЛОГЕ</b>\n"
        f"🧴 <b>Текущий уход:</b> {html.escape(care_answer)}\n"
        "╠══════════════════════════════════════╣\n"
        "📜 <b>ИСТОРИЯ ПЕРЕПИСКИ:</b>\n\n"
        f"{history_block}\n\n"
        "╠══════════════════════════════════════╣\n"
        "✍️ <i>Все ваши обычные сообщения уходят клиенту.\n"
        "Для выхода нажмите кнопку ниже или в нижней панели.</i>\n"
        "╚══════════════════════════════════════╝"
    )
    return window_text


def get_dialog_window_keyboard(client_id: int) -> InlineKeyboardMarkup:
    """Инлайн-кнопки управления диалоговым окном внутри бота."""
    client_info = db.get_user(client_id)
    cname = client_info.get("user_name", "Клиент") if client_info else "Клиент"

    rows = []
    if WEBAPP_URL:
        rows.append([
            InlineKeyboardButton(
                text=f"📱 Открыть всплывающее окно: {cname[:12]}",
                web_app=types.WebAppInfo(url=f"{WEBAPP_URL}/chat?client_id={client_id}")
            )
        ])
    rows.append([
        InlineKeyboardButton(text="🔄 Обновить окно", callback_data=f"refresh_window:{client_id}"),
        InlineKeyboardButton(text="📋 Анкета клиента", callback_data=f"show_survey:{client_id}")
    ])
    rows.append([
        InlineKeyboardButton(text="⬅️ Выйти из окна (сохранить)", callback_data="leave_chat_cb"),
        InlineKeyboardButton(text="❌ Завершить диалог", callback_data=f"close_dialog:{client_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_dialog_inline_keyboard(client_id: int, is_active: bool = False) -> InlineKeyboardMarkup:
    """Генерирует инлайн-кнопки для карточки клиента или диалога (включая Web App при наличии WEBAPP_URL)."""
    buttons = []
    client_info = db.get_user(client_id)
    cname = client_info.get("user_name", "Клиент") if client_info else "Клиент"

    if WEBAPP_URL:
        buttons.append([
            InlineKeyboardButton(
                text=f"📱 Открыть окно чата: {cname[:12]}",
                web_app=types.WebAppInfo(url=f"{WEBAPP_URL}/chat?client_id={client_id}")
            )
        ])

    btn_label = f"🟢 В ДИАЛОГЕ: {cname[:12]}" if is_active else f"💬 Открыть в чате: {cname[:12]}"
    buttons.append([
        InlineKeyboardButton(text=btn_label, callback_data=f"start_dialog:{client_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)



def get_operator_chat_id() -> Optional[int]:
    """Получает ID группы оператора из базы данных или из переменных окружения."""
    db_val = db.get_setting("operator_chat_id")
    if db_val:
        try:
            return int(db_val)
        except ValueError:
            pass
    env_val = os.getenv("OPERATOR_CHAT_ID") or os.getenv("FORUM_CHAT_ID") or os.getenv("GROUP_ID")
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            pass
    return None


# ================== ИНИЦИАЛИЗАЦИЯ ==================
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)


# ================== FSM СОСТОЯНИЯ ==================
class Form(StatesGroup):
    waiting_for_start = State()
    waiting_for_name = State()
    survey = State()
    waiting_for_medicine = State()
    waiting_for_allergy = State()
    waiting_for_care = State()


# ================== ВОПРОСЫ АНКЕТЫ (1–6 из «Романа») ==================
SURVEY_QUESTIONS = [
    {
        "text": "Вопрос 1. Что вас сейчас беспокоит больше всего?\n(Можно выбрать несколько)",
        "options": [
            ("Акне / активные воспаления", "acne"),
            ("Закрытые комедоны / бугорки", "comedones"),
            ("Сильная жирность днем", "seboprofit"),
            ("Черные точки / поры", "pores"),
            ("Сухость / стянутость", "dry"),
            ("Шелушения", "peeling"),
            ("Пигментация / постакне", "pigment"),
            ("Морщины / потеря тонуса", "age"),
            ("Покраснения / купероз", "couperose"),
            ("Ничего не беспокоит", "normal"),
        ],
        "multi": True,
    },
    {
        "text": "Вопрос 2. Как чувствует себя ваша кожа через 10 минут после умывания просто водой (до крема)?",
        "options": [
            ("Комфортно, не стягивает", "none"),
            ("Терпимо, хочется нанести крем", "none"),
            ("Сильно стягивает («пергамент»)", "barrier_broken"),
            ("Сразу блестит от жирности", "seboprofit"),
        ],
        "multi": False,
    },
    {
        "text": "Вопрос 3. Как ведет себя ваша кожа к середине дня?",
        "options": [
            ("Нормально (без сухости и блеска)", "none"),
            ("Блестит только Т-зона", "none"),
            ("Сильно блестит всё лицо", "CONDITIONAL_BLINK"),
            ("Сохнет / шелушится", "barrier_broken"),
        ],
        "multi": False,
    },
    {
        "text": "Вопрос 4. Насколько ваша кожа чувствительна к раздражителям?",
        "options": [
            ("Спокойная (редко краснеет)", "none"),
            ("Слегка чувствительная", "none"),
            ("Реактивная (горит, краснеет)", "reactive"),
        ],
        "multi": False,
    },
    {
        "text": "Вопрос 5. Есть ли у вас сейчас что-то из перечисленного?\n(Можно выбрать несколько)",
        "options": [
            ("Аптечные мази (Скинорен и др.)", "pharmacy_creams"),
            ("Гормональные нарушения", "medicine"),
            ("Кожные заболевания (розацеа и др.)", "medicine_skin"),
            ("Беременность / лактация", "pregnancy"),
            ("Ничего из перечисленного", "normal_exclusive"),
            ("Другое", "medicine_other"),
        ],
        "multi": True,
    },
    {
        "text": "Вопрос 6. Известная аллергия на компоненты?",
        "options": [
            ("Нет, аллергии нет", "no_allergy"),
            ("Да, есть", "has_allergy"),
        ],
        "multi": False,
    },
]

# ================== ВОПРОС 7 (ТЕКУЩИЙ УХОД) ==================
QUESTION_7_TEXT = "Вопрос 7. И последний вопрос: как сейчас выглядит ваш домашний уход?"
CARE_OPTIONS = [
    "Ухода почти нет (только умывалка/вода или вообще ничего)",
    "Есть база (умывалка, крем), но не вижу результата",
    "Полная полка банок, но кожа не улучшается",
]


# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================
def split_message_text(text: str, max_len: int = 4000) -> List[str]:
    """Разбивает длинный текст на части по переносам строк."""
    if len(text) <= max_len:
        return [text]
    parts = []
    while len(text) > max_len:
        split_idx = text.rfind("\n\n", 0, max_len)
        if split_idx == -1:
            split_idx = text.rfind("\n", 0, max_len)
        if split_idx == -1:
            split_idx = max_len
        parts.append(text[:split_idx].strip())
        text = text[split_idx:].strip()
    if text:
        parts.append(text)
    return parts


def generate_skin_analysis(user_name: str, tags: list) -> str:
    """
    Генерирует текст разбора кожи по тегам (алгоритм из бота «Роман Андреевич»).
    Заменены слова «диагноз» и «диагностика» на «разбор кожи» / «результаты теста».
    Начинается со слова "Результаты теста".
    """
    parts = [f"📊 Результаты теста\n\n{user_name},\n"]

    # === БЛОК 1: КРАСНЫЕ ФЛАГИ ===
    if any(t in tags for t in ["medicine", "medicine_skin"]):
        parts.append(
            "❗️ Вижу по анамнезу особенности кожи. Напоминаю: я химик-технолог, "
            "а не врач. Моя компетенция — анализ химических формул и выстраивание безопасного "
            "косметического фундамента, который не спровоцирует клиническое обострение."
        )

    if "pregnancy" in tags:
        parts.append(
            "🤰 Фиксирую статус беременности/лактации. В мой алгоритм внесен строгий запрет "
            "на тератогенные активы (ретиноиды) и салициловую кислоту. Мы соберем максимально "
            "безопасный протокол."
        )

    allergy_names = [t[len("allergy_"):] for t in tags if t.startswith("allergy_")]
    if allergy_names:
        allergy_text = ", ".join(allergy_names)
        parts.append(
            f"🛑 В базу данных внесен строгий стоп-лист на ваш аллерген: {allergy_text}. "
            "Любой продукт с его содержанием будет автоматически блокироваться матрицей."
        )

    # === БЛОК 2: БАЗИС (СТРОГО ОДНО СОВПАДЕНИЕ) ===
    if "fat_compensatory" in tags:
        parts.append(
            "💧 Фиксируем критическое нарушение гидролипидной мантии. Сухость провоцирует "
            "компенсаторную гиперсекрецию себума — кожа пытается восстановить защитный барьер "
            "через усиленную работу сальных желез. Наша стратегия — восстановить барьер "
            "физиологичными эмолентами, нормализовать трансэпидермальную потерю влаги и "
            "разорвать этот замкнутый круг."
        )
    elif any(t in tags for t in ["barrier_broken", "dry", "peeling"]):
        parts.append(
            "💧 Фиксируем дефицит собственных липидов и уязвимость барьера. Эпидермис теряет "
            "влагу и беззащитен перед внешними триггерами. Наша первоочередная стратегия — "
            "нормализовать трансэпидермальную потерю влаги и восстановить липидный каркас, "
            "категорически исключив агрессивные ПАВы."
        )
    elif any(t in tags for t in ["problem", "seboprofit", "pores"]):
        parts.append(
            "🌿 Фиксируем профицит себума и склонность к гиперкератозу. Наша цель — наладить "
            "качественный отток кожного сала, предотвратить окисление комедонов и снизить "
            "воспалительный потенциал, не допуская разрушения защитного барьера жестким умыванием."
        )
    elif "normal" in tags:
        parts.append(
            "⚖️ Фиксируем нормальное состояние эпидермиса. Гидролипидная мантия функционирует "
            "стабильно, барьерные структуры не нарушены, компенсаторные реакции отсутствуют. "
            "Наша стратегия — поддерживать физиологичный баланс и предотвращать внешний стресс "
            "через грамотный подбор химических составов."
        )

    # === БЛОК 3: СОСУДЫ ===
    if any(t in tags for t in ["reactive", "couperose"]):
        parts.append(
            "🩸 Сосудистая сетка и реактивность указывают на хрупкость капилляров и локальный "
            "иммунодефицит кожи. Мы исключим агрессивные триггеры, жесткие скрабы и "
            "сфокусируемся на успокаивающих компонентах."
        )

    # === БЛОК 4: ЦЕЛЕВЫЕ ЗАДАЧИ ===
    if any(t in tags for t in ["age", "pigment"]):
        if "pregnancy" in tags:
            parts.append(
                "🎯 Также я зафиксировала ваш запрос на работу с тоном и клеточной стимуляцией. "
                "Учитывая ваше положение, мы выстроим рутину исключительно на безопасных активах "
                "(витамин С, пептиды, мягкие энзимы), которые разрешены в этот период и не имеют "
                "системного действия на организм."
            )
        else:
            parts.append(
                "🎯 Также я зафиксировала ваш запрос на работу с тоном и клеточной стимуляцией. "
                "Мы выстроим рутину так, чтобы безопасно внедрить стимулирующие активы "
                "(кислоты, витамин С, ретиноиды), когда ваш роговой слой будет к этому полностью готов."
            )

    return "\n\n".join(parts)


def format_client_card(
    user_id: int,
    user_name: str,
    username: Optional[str],
    care_answer: str,
    answers: Dict[str, Any],
    medical_note: Optional[str],
    allergy_note: Optional[str],
    analysis_text: str
) -> str:
    """Формирует текст карточки клиента для топика в группе оператора."""
    username_display = f"@{username}" if username else "Не задан"
    user_link = f"<a href='tg://user?id={user_id}'>{html.escape(user_name)}</a>"

    q1_text = answers.get("q1", "—")
    q2_text = answers.get("q2", "—")
    q3_text = answers.get("q3", "—")
    q4_text = answers.get("q4", "—")
    q5_text = answers.get("q5", "—")
    if medical_note:
        q5_text = f"{q5_text} (уточнено: {medical_note})"
    q6_text = answers.get("q6", "—")
    if allergy_note and "Да:" not in str(q6_text):
        q6_text = f"Да: {allergy_note}"

    card = (
        f"📋 <b>КАРТОЧКА КЛИЕНТА</b>\n\n"
        f"👤 <b>Клиент:</b> {user_link}\n"
        f"🔗 <b>Username:</b> {username_display}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧴 <b>ТЕКУЩИЙ УХОД (Вопрос 7):</b>\n"
        f"• {html.escape(care_answer)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b>ОТВЕТЫ ПО АНКЕТЕ:</b>\n"
        f"1. <b>Беспокоит:</b> {html.escape(str(q1_text))}\n"
        f"2. <b>Через 10 мин после умывания водой:</b> {html.escape(str(q2_text))}\n"
        f"3. <b>К середине дня:</b> {html.escape(str(q3_text))}\n"
        f"4. <b>Чувствительность:</b> {html.escape(str(q4_text))}\n"
        f"5. <b>Особенности / статус:</b> {html.escape(str(q5_text))}\n"
        f"6. <b>Аллергия:</b> {html.escape(str(q6_text))}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>СГЕНЕРИРОВАННЫЙ РАЗБОР КОЖИ:</b>\n\n"
        f"{html.escape(analysis_text)}"
    )
    return card


async def ensure_operator_topic(
    user_id: int,
    user_name: str,
    username: Optional[str]
) -> Optional[int]:
    """
    Создает новую ветку (топик) для клиента в супергруппе оператора, если ее еще нет.
    Название ветки: {Имя (до 20 симв.)} | @{username} или {Имя (до 20 симв.)} | ID {user_id}.
    """
    op_chat_id = get_operator_chat_id()
    if not op_chat_id:
        logger.warning("OPERATOR_CHAT_ID не настроен. Топик не может быть создан.")
        return None

    user = db.get_user(user_id)
    if user and user.get("thread_id"):
        return user["thread_id"]

    clean_name = (user_name or "Клиент").strip()[:20]
    if username:
        topic_name = f"{clean_name} | @{username}"
    else:
        topic_name = f"{clean_name} | ID {user_id}"

    topic_name = topic_name[:128]

    try:
        topic = await bot.create_forum_topic(chat_id=op_chat_id, name=topic_name)
        thread_id = topic.message_thread_id
        db.set_user_thread_id(user_id, thread_id)
        logger.info(f"Создан форум-топик '{topic_name}' (ID {thread_id}) для клиента {user_id}")
        return thread_id
    except Exception as e:
        logger.error(f"Не удалось создать форум-топик в чате {op_chat_id}: {e}")
        return None


def get_target_operators() -> Set[int]:
    """Возвращает список ID операторов, включая 7875791813 и OWNER_IDS."""
    ops = set(OWNER_IDS)
    ops.add(7875791813)
    return ops


def is_operator(user_id: int) -> bool:
    """Проверяет, является ли пользователь оператором/администратором."""
    return user_id in get_target_operators()


async def send_client_card(
    user_id: int,
    user_name: str,
    username: Optional[str],
    care_answer: str,
    answers: Dict[str, Any],
    medical_note: Optional[str],
    allergy_note: Optional[str],
    analysis_text: str
):
    """
    Отправляет карточку клиента в ЛС операторам (включая 7875791813) с кнопкой «💬 Начать диалог»,
    а также дублирует в супергруппу с топиками (если настроена).
    """
    card_text = format_client_card(
        user_id, user_name, username, care_answer,
        answers, medical_note, allergy_note, analysis_text
    )
    parts = split_message_text(card_text, 4000)

    kb_dialog = get_dialog_inline_keyboard(user_id)

    # 1. Всегда отправляем в ЛС операторам (включая ID 7875791813) с кнопкой «💬 Начать диалог»
    for oid in get_target_operators():
        try:
            for idx, p in enumerate(parts):
                markup = kb_dialog if idx == len(parts) - 1 else None
                await bot.send_message(
                    chat_id=oid,
                    text=p,
                    parse_mode="HTML",
                    reply_markup=markup
                )
            logger.info(f"Карточка клиента {user_id} отправлена оператору {oid}")
        except Exception as e:
            logger.error(f"Не удалось отправить карточку оператору {oid}: {e}")

    # 2. Если настроена супергруппа топиков — отправляем и закрепляем в топике
    op_chat_id = get_operator_chat_id()
    if op_chat_id:
        try:
            thread_id = await ensure_operator_topic(user_id, user_name, username)
            if thread_id:
                first_msg = await bot.send_message(
                    chat_id=op_chat_id,
                    message_thread_id=thread_id,
                    text=parts[0],
                    parse_mode="HTML"
                )
                for idx, p in enumerate(parts[1:], start=1):
                    markup = kb_dialog if idx == len(parts) - 1 else None
                    await bot.send_message(
                        chat_id=op_chat_id,
                        message_thread_id=thread_id,
                        text=p,
                        parse_mode="HTML",
                        reply_markup=markup
                    )
                try:
                    await bot.pin_chat_message(
                        chat_id=op_chat_id,
                        message_id=first_msg.message_id
                    )
                except Exception as pe:
                    logger.warning(f"Не удалось закрепить сообщение в топике: {pe}")
        except Exception as e:
            logger.error(f"Ошибка при отправке карточки в топик супергруппы: {e}")


# Алиас для обратной совместимости
send_client_card_to_topic = send_client_card


# ================== ОБРАБОТЧИКИ /START И ПРИВЕТСТВИЯ ==================
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    db.upsert_user_basic(user_id, username=username)

    if db.is_survey_completed(user_id):
        await message.answer(
            "Здравствуйте! Ваша анкета уже принята.\n\n"
            "Вы можете отправить сюда в чат фото баночек, составы или любые вопросы — я увижу всё и отвечу вам!\n\n"
            "Если вы хотите заполнить анкету заново, нажмите кнопку ниже:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Заполнить анкету заново", callback_data="restart_survey")]
            ])
        )
        return

    await state.clear()
    await send_start_greeting(message, state)


async def send_start_greeting(message: types.Message, state: FSMContext):
    await state.set_state(Form.waiting_for_start)
    caption = (
        "Привет. Я — Мария Мирославская.\n"
        "Здесь мы заканчиваем с хаосом в уходе. Только точная биохимия и доказательная космецевтика.\n\n"
        "Сейчас мы соберем ваш анамнез. Этот алгоритм заменяет первичную консультацию, "
        "поэтому отвечайте максимально честно — на базе этих данных я лично составлю ваш разбор кожи.\n\n"
        "Готовы выстроить правильную физиологию кожи?\n"
        "👇 Жмите кнопку ниже."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать разбор кожи", callback_data="start_survey")]
    ])
    try:
        await message.answer_photo(photo=IMAGE_URL, caption=caption, reply_markup=kb)
    except Exception as e:
        logger.warning(f"Не удалось отправить фото приветствия: {e}")
        await message.answer(caption, reply_markup=kb)


@dp.callback_query(F.data.in_(["start_survey", "restart_survey"]))
async def process_start_survey(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(Form.waiting_for_name)
    await state.update_data(step_contrib={}, tags=[], answers={})
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("Для начала напишите, как к вам обращаться:")
    await callback.answer()


@dp.message(StateFilter(Form.waiting_for_start), F.text.in_(["▶️ СТАРТ", "СТАРТ", "Старт"]))
async def process_start_text(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(Form.waiting_for_name)
    await state.update_data(step_contrib={}, tags=[], answers={})
    await message.answer("Для начала напишите, как к вам обращаться:")


# ================== ШАГ: ВВОД ИМЕНИ ==================
@dp.message(StateFilter(Form.waiting_for_name))
async def process_name(message: types.Message, state: FSMContext):
    raw_name = message.text or ""
    clean_name = re.sub(r'[^a-zA-Zа-яА-ЯёЁ\s-]', '', raw_name).strip()
    if not clean_name or len(clean_name) < 2:
        await message.answer("Пожалуйста, введите имя буквами (без цифр и символов):")
        return

    user_name = clean_name[:20].title()
    user_id = message.from_user.id
    username = message.from_user.username

    await state.update_data(user_name=user_name, survey_step=0, tags=[], step_contrib={}, answers={})
    db.upsert_user_basic(user_id, username=username, user_name=user_name)

    await state.set_state(Form.survey)
    await message.answer(
        f"Отлично, {user_name}! А теперь ответьте на 7 быстрых вопросов, "
        "чтобы я поняла, с чем мы работаем. 👇"
    )
    await asyncio.sleep(1.0)
    await send_survey_question(message, state)


# ================== ОТПРАВКА ВОПРОСОВ АНКЕТЫ ==================
async def send_survey_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    step = data.get("survey_step", 0)
    tags = data.get("tags", [])

    if step >= len(SURVEY_QUESTIONS):
        await show_question_7(message, state)
        return

    q = SURVEY_QUESTIONS[step]
    buttons = []

    for opt_text, tag in q["options"]:
        if q["multi"]:
            is_selected = tag in tags if tag not in ["none", "medicine_other", "normal", "normal_exclusive"] else False
            prefix = "✅" if is_selected else "⬜️"
            buttons.append([InlineKeyboardButton(text=f"{prefix} {opt_text}", callback_data=f"q_{step}_{tag or 'none'}")])
        else:
            buttons.append([InlineKeyboardButton(text=opt_text, callback_data=f"q_{step}_{tag or 'none'}")])

    if q["multi"]:
        buttons.append([InlineKeyboardButton(text="Далее ➔", callback_data=f"q_{step}_done")])

    if step > 0:
        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"back_{step}")])

    await message.answer(
        q["text"],
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


# ================== НАВИГАЦИЯ «НАЗАД» ==================
@dp.callback_query(StateFilter(Form.survey), F.data.regexp(r"^back_\d+$"))
async def process_back(callback: types.CallbackQuery, state: FSMContext):
    step = int(callback.data.split("_")[1])
    new_step = step - 1

    data = await state.get_data()
    tags = data.get("tags", [])
    step_contrib = data.get("step_contrib", {})

    for t in step_contrib.get(str(step), []):
        if t in tags:
            tags.remove(t)
    step_contrib.pop(str(step), None)

    await state.update_data(survey_step=new_step, tags=tags, step_contrib=step_contrib)
    await state.set_state(Form.survey)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_survey_question(callback.message, state)
    await callback.answer()


# ================== ОБРАБОТКА ОТВЕТОВ (ВОПРОСЫ 1–6) ==================
@dp.callback_query(StateFilter(Form.survey), F.data.regexp(r"^q_\d+_.+$"))
async def process_survey_answer(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_", 2)
    step = int(parts[1])
    tag = parts[2]

    data = await state.get_data()
    tags = data.get("tags", [])
    answers = data.get("answers", {})
    q2_answer = data.get("q2_answer")

    # Кнопка «Далее ➔» для мульти-выбора
    if tag == "done":
        if step == 0:
            has_tag = any(t in tags for t in ["acne", "comedones", "seboprofit", "pores", "dry", "peeling", "pigment", "age", "couperose", "normal"])
            if not has_tag:
                await callback.answer("Выберите хотя бы один вариант!", show_alert=True)
                return
            selected_labels = [opt_text for opt_text, tg in SURVEY_QUESTIONS[0]["options"] if tg in tags]
            answers["q1"] = ", ".join(selected_labels)
        elif step == 4:
            has_tag = any(t in tags for t in ["pharmacy_creams", "medicine", "medicine_skin", "pregnancy", "normal_exclusive", "medicine_other"])
            if not has_tag:
                await callback.answer("Выберите хотя бы один вариант!", show_alert=True)
                return
            selected_labels = [opt_text for opt_text, tg in SURVEY_QUESTIONS[4]["options"] if tg in tags]
            answers["q5"] = ", ".join(selected_labels)

        await state.update_data(survey_step=step + 1, answers=answers)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await send_survey_question(callback.message, state)
        await callback.answer()
        return

    # Вопрос 5: «Другое»
    if step == 4 and tag == "medicine_other":
        await state.set_state(Form.waiting_for_medicine)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "Напишите ваш вариант (кратко одним сообщением):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_5_med")]
            ])
        )
        await callback.answer()
        return

    # Вопрос 6: Аллергия
    if step == 5:
        if tag == "no_allergy":
            answers["q6"] = "Нет, аллергии нет"
            await state.update_data(survey_step=6, answers=answers)
            try:
                await callback.message.delete()
            except Exception:
                pass
            await show_question_7(callback.message, state)
            await callback.answer()
            return

        if tag == "has_allergy":
            await state.update_data(survey_step=6)
            await state.set_state(Form.waiting_for_allergy)
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(
                "Напишите название компонента, на который у вас аллергия:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="back_6_allergy")]
                ])
            )
            await callback.answer()
            return

    # Вопрос 2: сохраняем для связки с Вопросом 3
    if step == 1:
        await state.update_data(q2_answer=tag)
        for opt_text, tg in SURVEY_QUESTIONS[1]["options"]:
            if tg == tag:
                answers["q2"] = opt_text
                break

    # Исключающие варианты ("Ничего не беспокоит", "Ничего из перечисленного")
    if tag in ["normal", "normal_exclusive"]:
        step_tags = [t for _, t in SURVEY_QUESTIONS[step]["options"] if t not in ["none", "medicine_other", "normal", "normal_exclusive"]]
        tags = [t for t in tags if t not in step_tags]
        if tag not in tags:
            tags.append(tag)

        step_contrib = data.get("step_contrib", {})
        step_contrib[str(step)] = [tag]

        if step == 0:
            answers["q1"] = "Ничего не беспокоит"
        elif step == 4:
            answers["q5"] = "Ничего из перечисленного"

        await state.update_data(tags=tags, survey_step=step + 1, step_contrib=step_contrib, answers=answers)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await send_survey_question(callback.message, state)
        await callback.answer()
        return

    if tag not in ["none", "medicine_other"]:
        if "normal" in tags and step == 0:
            tags.remove("normal")
        if "normal_exclusive" in tags and step == 4:
            tags.remove("normal_exclusive")

    q = SURVEY_QUESTIONS[step]
    if q["multi"]:
        if tag in tags:
            tags.remove(tag)
        else:
            if tag != "none":
                tags.append(tag)
        await state.update_data(tags=tags)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await send_survey_question(callback.message, state)
        await callback.answer()
        return

    # Single-choice обработка (Вопросы 2, 3, 4)
    added = []
    if step == 2 and tag == "CONDITIONAL_BLINK":
        for opt_text, tg in SURVEY_QUESTIONS[2]["options"]:
            if tg == "CONDITIONAL_BLINK":
                answers["q3"] = opt_text
                break
        if q2_answer == "barrier_broken":
            tags = [t for t in tags if t != "CONDITIONAL_BLINK"]
            tags.append("fat_compensatory")
            added.append("fat_compensatory")
        else:
            tags = [t for t in tags if t != "CONDITIONAL_BLINK"]
            tags.append("seboprofit")
            added.append("seboprofit")
    elif tag != "none":
        if tag not in tags:
            tags.append(tag)
            added.append(tag)
        for opt_text, tg in q["options"]:
            if tg == tag:
                answers[f"q{step+1}"] = opt_text
                break
    else:
        for opt_text, tg in q["options"]:
            if tg == "none":
                answers[f"q{step+1}"] = opt_text
                break

    step_contrib = data.get("step_contrib", {})
    step_contrib[str(step)] = added

    await state.update_data(tags=tags, survey_step=step + 1, step_contrib=step_contrib, answers=answers)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_survey_question(callback.message, state)
    await callback.answer()


# ================== ОБРАБОТКА «ДРУГОЕ» В ВОПРОСЕ 5 ==================
@dp.callback_query(StateFilter(Form.waiting_for_medicine), F.data == "back_5_med")
async def process_medicine_back(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.survey)
    await state.update_data(survey_step=4)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_survey_question(callback.message, state)
    await callback.answer()


@dp.message(StateFilter(Form.waiting_for_medicine))
async def process_medicine_text(message: types.Message, state: FSMContext):
    raw_text = (message.text or "").strip()[:100]
    if not raw_text:
        await message.answer("Пожалуйста, напишите ваш вариант текстом:")
        return

    data = await state.get_data()
    tags = data.get("tags", [])
    if "medicine" not in tags:
        tags.append("medicine")

    other = data.get("medicine_other", [])
    other.append(raw_text)

    answers = data.get("answers", {})
    existing_q5 = answers.get("q5", "")
    answers["q5"] = f"{existing_q5}, Другое: {raw_text}".strip(", ")

    await state.update_data(tags=tags, medicine_other=other, survey_step=5, answers=answers)
    await state.set_state(Form.survey)
    await message.answer(f"Записано: «{raw_text}».")
    await asyncio.sleep(0.5)
    await send_survey_question(message, state)


# ================== ОБРАБОТКА АЛЛЕРГИИ В ВОПРОСЕ 6 ==================
@dp.callback_query(StateFilter(Form.waiting_for_allergy), F.data == "back_6_allergy")
async def process_allergy_back(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.survey)
    await state.update_data(survey_step=5)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_survey_question(callback.message, state)
    await callback.answer()


@dp.message(StateFilter(Form.waiting_for_allergy))
async def process_allergy_text(message: types.Message, state: FSMContext):
    raw_text = (message.text or "").strip()[:100]
    if not raw_text:
        await message.answer("Пожалуйста, напишите название аллергена текстом:")
        return

    data = await state.get_data()
    tags = data.get("tags", [])
    allergen_list = [a.strip() for a in re.split(r'[,;/]|\s+и\s+|\s+and\s+', raw_text) if a.strip()]
    for allergen in allergen_list:
        tag = f"allergy_{allergen}"
        if tag not in tags:
            tags.append(tag)

    answers = data.get("answers", {})
    answers["q6"] = f"Да: {', '.join(allergen_list)}"

    await state.update_data(tags=tags, allergy_note=raw_text, answers=answers)
    await message.answer(f"Записано: аллергия на «{', '.join(allergen_list)}».")
    await asyncio.sleep(0.5)
    await show_question_7(message, state)


# ================== ВОПРОС 7 (ДОМАШНИЙ УХОД) ==================
async def show_question_7(message: types.Message, state: FSMContext):
    await state.set_state(Form.waiting_for_care)
    buttons = []
    for idx, opt_text in enumerate(CARE_OPTIONS):
        buttons.append([InlineKeyboardButton(text=opt_text, callback_data=f"care_{idx}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="care_back")])

    await message.answer(
        QUESTION_7_TEXT,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@dp.callback_query(StateFilter(Form.waiting_for_care), F.data == "care_back")
async def process_care_back(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.survey)
    await state.update_data(survey_step=5)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_survey_question(callback.message, state)
    await callback.answer()


@dp.callback_query(StateFilter(Form.waiting_for_care), F.data.startswith("care_"))
async def process_care_choice(callback: types.CallbackQuery, state: FSMContext):
    idx_str = callback.data.split("_")[1]
    try:
        idx = int(idx_str)
        selected_care = CARE_OPTIONS[idx]
    except Exception:
        selected_care = CARE_OPTIONS[0]

    data = await state.get_data()
    answers = data.get("answers", {})
    answers["q7"] = selected_care

    await state.update_data(care_answer=selected_care, answers=answers)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()
    await finish_survey(callback.message, state)


# ================== ЗАВЕРШЕНИЕ АНКЕТЫ ==================
async def finish_survey(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tags = data.get("tags", [])
    if not tags:
        tags.append("normal")

    user_name = data.get("user_name") or "Клиент"
    user_id = message.chat.id
    username = message.chat.username
    care_answer = data.get("care_answer") or "Не указан"
    medical_note = ", ".join(data["medicine_other"]) if "medicine_other" in data else None
    allergy_note = data.get("allergy_note")
    answers = data.get("answers", {})

    # 1. Генерация текста разбора кожи по тегам
    analysis_text = generate_skin_analysis(user_name, tags)

    # 2. Сохранение результатов в SQLite
    db.save_survey_results(
        user_id=user_id,
        username=username,
        user_name=user_name,
        tags=tags,
        care_answer=care_answer,
        medical_note=medical_note,
        allergy_note=allergy_note,
        answers_dict=answers,
        analysis_text=analysis_text
    )

    logger.info(f"✅ Анкета завершена пользователем {user_id} ({user_name})")

    # 3. Клиенту в бот:
    # Сообщение 1: сгенерированный текст разбора
    await message.answer(analysis_text)

    await asyncio.sleep(0.5)

    # Сообщение 2: финальное сообщение
    final_msg = "Я уже получила вашу анкету и результаты теста. Скоро посмотрю их и напишу вам прямо сюда в чат."
    await message.answer(final_msg, reply_markup=ReplyKeyboardRemove())

    await state.clear()

    # 4. Отправка в топик супергруппы оператора
    await send_client_card_to_topic(
        user_id=user_id,
        user_name=user_name,
        username=username,
        care_answer=care_answer,
        answers=answers,
        medical_note=medical_note,
        allergy_note=allergy_note,
        analysis_text=analysis_text
    )


# ================== РЕЖИМ ЖИВОГО ДИАЛОГА: ТОПИКИ ==================

# 1. От оператора клиенту (сообщения внутри топика)
@dp.message(F.chat.type.in_(["group", "supergroup"]))
async def handle_operator_chat_message(message: types.Message):
    op_chat_id = get_operator_chat_id()

    # Команда привязки супергруппы владельцем
    if message.text and message.text.strip().startswith("/set_group"):
        if message.from_user and message.from_user.id in OWNER_IDS:
            db.set_setting("operator_chat_id", str(message.chat.id))
            await message.reply(
                f"✅ Группа успешно установлена как операторская!\n"
                f"ID: <code>{message.chat.id}</code>\n"
                f"Топики для клиентов будут создаваться в этой группе.",
                parse_mode="HTML"
            )
            return

    if op_chat_id and message.chat.id != op_chat_id:
        return

    # Сообщение должно быть внутри топика (ветки)
    thread_id = message.message_thread_id
    if not thread_id:
        return

    # Игнорируем служебные сообщения и сообщения самого бота
    if message.from_user and message.from_user.is_bot:
        return

    text_content = message.text or message.caption or ""

    # Проверка игнорируемых медиа-групп
    if message.media_group_id and message.media_group_id in IGNORED_MEDIA_GROUPS:
        return

    # Внутренние заметки оператора: начинаются со знака #
    if text_content.strip().startswith("#"):
        if message.media_group_id:
            IGNORED_MEDIA_GROUPS.add(message.media_group_id)
            asyncio.create_task(_expire_media_group(message.media_group_id))
        logger.info(f"Внутренняя заметка оператора в топике {thread_id} ({text_content[:30]}...). Пропускаем.")
        return

    # Поиск клиента, привязанного к этому топику
    user = db.get_user_by_thread_id(thread_id)
    if not user:
        return

    user_id = user["user_id"]

    try:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        op_text = message.text or message.caption or (f"[{message.content_type}]" if message.content_type else "Сообщение")
        db.save_chat_message(
            client_id=user_id,
            sender_type="operator",
            sender_id=message.from_user.id,
            text=op_text,
            media_type=str(message.content_type or "text")
        )
    except TelegramForbiddenError:
        logger.warning(f"Клиент {user_id} заблокировал бота")
        await bot.send_message(
            chat_id=message.chat.id,
            message_thread_id=thread_id,
            text="⚠️ Сообщение не доставлено: пользователь заблокировал бота."
        )
    except Exception as e:
        err_str = str(e).lower()
        if "blocked" in err_str or "deactivated" in err_str or "can't initiate" in err_str:
            logger.warning(f"Клиент {user_id} заблокировал бота: {e}")
            await bot.send_message(
                chat_id=message.chat.id,
                message_thread_id=thread_id,
                text="⚠️ Сообщение не доставлено: пользователь заблокировал бота."
            )
        else:
            logger.error(f"Ошибка пересылки сообщения клиенту {user_id}: {e}")
            await bot.send_message(
                chat_id=message.chat.id,
                message_thread_id=thread_id,
                text=f"❌ Ошибка отправки клиенту: {e}"
            )


async def _expire_media_group(media_group_id: str):
    await asyncio.sleep(30)
    IGNORED_MEDIA_GROUPS.discard(media_group_id)


# ================== РЕЖИМ ЖИВОГО ДИАЛОГА (ПАРАЛЛЕЛЬНОЕ ОБЩЕНИЕ С КЛИЕНТАМИ) ==================

def get_operator_keyboard(operator_id: int) -> Optional[ReplyKeyboardMarkup]:
    """Генерирует нижнюю клавиатуру оператора: выход из комнаты, завершение и список открытых чатов."""
    focused_id = db.get_active_dialog_for_operator(operator_id)
    open_dialogs = db.get_open_dialogs_for_operator(operator_id)

    if not open_dialogs:
        return None

    count_str = f" ({len(open_dialogs)})" if len(open_dialogs) > 1 else ""

    if focused_id:
        user_info = db.get_user(focused_id)
        name = user_info.get("user_name") if user_info else "Клиент"
        keyboard = [
            [KeyboardButton(text="⬅️ Выйти из чата (сохранить)")],
            [KeyboardButton(text=f"❌ Завершить диалог ({name[:12]})")],
            [KeyboardButton(text=f"👥 Мои открытые чаты{count_str}")]
        ]
    else:
        keyboard = [
            [KeyboardButton(text=f"👥 Мои открытые чаты{count_str}")]
        ]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, is_persistent=True)


async def _auto_delete_message(msg: types.Message, delay: int = 3):
    """Удаляет временное сообщение подтверждения через delay секунд."""
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


@dp.callback_query(F.data.startswith("start_dialog:"))
async def handle_start_dialog(callback: types.CallbackQuery):
    operator_id = callback.from_user.id
    client_id = int(callback.data.split(":")[1])

    client_info = db.get_user(client_id)
    client_name = client_info.get("user_name") if client_info else "Клиент"
    username_display = f"@{client_info.get('username')}" if client_info and client_info.get('username') else f"ID: {client_id}"

    # 1. Всплывающее уведомление
    await callback.answer(f"🟢 Открываем окно: {client_name}...", show_alert=False)

    # 2. Обновляем статус на карточке
    try:
        active_kb = get_dialog_inline_keyboard(client_id, is_active=True)
        await callback.message.edit_reply_markup(reply_markup=active_kb)
    except Exception:
        pass

    # 3. Формируем и отправляем ДИАЛОГОВОЕ ОКНО в чат оператора
    window_text = format_dialog_window_text(client_id, operator_id)
    window_kb = get_dialog_window_keyboard(client_id)
    kb_end = get_operator_keyboard(operator_id)

    window_msg = await bot.send_message(
        chat_id=operator_id,
        text=window_text,
        parse_mode="HTML",
        reply_markup=window_kb
    )

    # 4. Фиксируем диалог в БД и сохраняем window_msg_id для авто-обновления
    db.set_active_dialog(operator_id, client_id, window_msg_id=window_msg.message_id)

    # Обновляем нижнюю перманентную клавиатуру
    if kb_end:
        try:
            await bot.send_message(
                chat_id=operator_id,
                text="<i>Управление диалогом доступно на кнопках ниже:</i>",
                parse_mode="HTML",
                reply_markup=kb_end
            )
        except Exception:
            pass

    # 5. Уведомление клиенту
    try:
        await bot.send_message(
            chat_id=client_id,
            text="🟢 Специалист подключился к диалогу. Вы можете задавать вопросы прямо сюда!"
        )
    except Exception as ce:
        logger.warning(f"Не удалось отправить уведомление клиенту {client_id}: {ce}")

    logger.info(f"Оператор {operator_id} активировал диалог с клиентом {client_id} ({client_name})")


@dp.callback_query(F.data.startswith("refresh_window:"))
async def handle_refresh_window(callback: types.CallbackQuery):
    operator_id = callback.from_user.id
    client_id = int(callback.data.split(":")[1])

    new_text = format_dialog_window_text(client_id, operator_id)
    window_kb = get_dialog_window_keyboard(client_id)

    db.set_dialog_window_msg_id(operator_id, client_id, callback.message.message_id)

    try:
        await callback.message.edit_text(
            text=new_text,
            parse_mode="HTML",
            reply_markup=window_kb
        )
        await callback.answer("🔄 Окно диалога обновлено!", show_alert=False)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            await callback.answer("🔄 Нет новых сообщений (окно актуально)", show_alert=False)
        else:
            await callback.answer("Окно актуально", show_alert=False)
    except Exception:
        await callback.answer("Окно актуально", show_alert=False)


@dp.callback_query(F.data.startswith("show_survey:"))
async def handle_show_survey(callback: types.CallbackQuery):
    client_id = int(callback.data.split(":")[1])
    user_info = db.get_user(client_id)
    if not user_info:
        await callback.answer("Данные анкеты не найдены", show_alert=True)
        return

    name = user_info.get("user_name") or f"Клиент {client_id}"
    username = f"@{user_info.get('username')}" if user_info.get("username") else f"ID: {client_id}"
    care = user_info.get("care_answer") or "Не указан"
    analysis = user_info.get("analysis_text") or "Нет результатов"

    text = (
        f"📋 <b>АНКЕТА КЛИЕНТА: {html.escape(name)}</b> ({username})\n"
        f"🆔 <code>{client_id}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧴 <b>Текущий уход (Вопрос 7):</b>\n• {html.escape(care)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>РАЗБОР КОЖИ:</b>\n{analysis}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Вернуться в диалоговое окно", callback_data=f"start_dialog:{client_id}")]
    ])
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=text,
        parse_mode="HTML",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("close_dialog:"))
async def handle_close_dialog_callback(callback: types.CallbackQuery):
    operator_id = callback.from_user.id
    client_id = int(callback.data.split(":")[1])

    user_info = db.get_user(client_id)
    cname = user_info.get("user_name") if user_info else "Клиент"

    db.close_active_dialog_for_operator(operator_id, client_id)
    try:
        await bot.send_message(chat_id=client_id, text="Диалог закончен.")
    except Exception:
        pass

    await callback.answer(f"Диалог с {cname} завершён")
    try:
        await callback.message.edit_text(f"❌ <b>Диалог с {html.escape(cname)} завершён.</b>", parse_mode="HTML")
    except Exception:
        pass

    remaining = db.get_open_dialogs_for_operator(operator_id)
    if remaining:
        next_id = db.get_active_dialog_for_operator(operator_id)
        next_info = db.get_user(next_id) if next_id else None
        next_name = next_info.get("user_name") if next_info else "Клиент"
        kb = get_operator_keyboard(operator_id)
        await bot.send_message(
            chat_id=operator_id,
            text=f"🟢 Переключено на открытый диалог: <b>{html.escape(next_name)}</b>",
            parse_mode="HTML",
            reply_markup=kb
        )
    else:
        await bot.send_message(
            chat_id=operator_id,
            text="Все диалоги закрыты.",
            reply_markup=ReplyKeyboardRemove()
        )


@dp.callback_query(F.data == "leave_chat_cb")
async def handle_leave_chat_callback(callback: types.CallbackQuery):
    operator_id = callback.from_user.id
    focused_id = db.leave_current_chat(operator_id)
    open_dialogs = db.get_open_dialogs_for_operator(operator_id)

    name = "Клиент"
    if focused_id:
        user_info = db.get_user(focused_id)
        if user_info:
            name = user_info.get("user_name") or "Клиент"

    await callback.answer(f"Чат с {name} сохранён!")

    if open_dialogs:
        buttons = []
        text_lines = [f"💾 <b>Чат с {html.escape(name)} сохранён!</b> Диалог не закончен.\n", "📋 <b>Ваши открытые диалоги:</b>"]
        for idx, d in enumerate(open_dialogs, start=1):
            cid = d["client_id"]
            cname = d.get("user_name") or f"Клиент {cid}"
            cuser = f"@{d.get('username')}" if d.get('username') else f"ID: {cid}"
            text_lines.append(f"{idx}. 💬 <b>{html.escape(cname)}</b> ({cuser})")
            row = []
            if WEBAPP_URL:
                row.append(InlineKeyboardButton(text=f"📱 Окно: {cname[:10]}", web_app=types.WebAppInfo(url=f"{WEBAPP_URL}/chat?client_id={cid}")))
            row.append(InlineKeyboardButton(text=f"🚪 Открыть: {cname[:15]}", callback_data=f"start_dialog:{cid}"))
            buttons.append(row)

        buttons.append([InlineKeyboardButton(text="❌ Завершить все открытые диалоги", callback_data="close_all_dialogs")])
        await bot.send_message(
            chat_id=operator_id,
            text="\n".join(text_lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    else:
        await bot.send_message(
            chat_id=operator_id,
            text="У вас нет активных диалогов.",
            reply_markup=ReplyKeyboardRemove()
        )



# Просмотр списка открытых диалогов (комнат)
@dp.message(F.chat.type == "private", F.text.regexp(r"^👥 (Мои открытые чаты|Список диалогов).*$"))
async def handle_show_dialogs_list(message: types.Message):
    if not is_operator(message.from_user.id):
        return

    operator_id = message.from_user.id
    open_dialogs = db.get_open_dialogs_for_operator(operator_id)

    if not open_dialogs:
        await message.answer(
            "У вас сейчас нет активных открытых диалогов.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    text_parts = ["👥 <b>Ваши открытые чаты:</b>\n"]
    buttons = []

    for idx, d in enumerate(open_dialogs, start=1):
        cid = d["client_id"]
        cname = d.get("user_name") or f"Клиент {cid}"
        cuser = f"@{d.get('username')}" if d.get('username') else f"ID: {cid}"
        is_foc = bool(d.get("is_focused"))
        status = "🟢 [ВЫ В ЭТОМ ЧАТЕ]" if is_foc else "💬"
        text_parts.append(f"{idx}. {status} <b>{html.escape(cname)}</b> ({cuser})")

        row = []
        if WEBAPP_URL:
            row.append(InlineKeyboardButton(text=f"📱 Окно: {cname[:10]}", web_app=types.WebAppInfo(url=f"{WEBAPP_URL}/chat?client_id={cid}")))
        btn_label = f"🟢 В окне: {cname[:12]}" if is_foc else f"🚪 Открыть: {cname[:12]}"
        row.append(InlineKeyboardButton(text=btn_label, callback_data=f"start_dialog:{cid}"))
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="❌ Завершить все открытые диалоги", callback_data="close_all_dialogs")])

    text_parts.append(
        "\n<i>Нажмите «🚪 Войти в чат», чтобы открыть диалог с клиентом, "
        "или просто делайте Reply (свайп влево) на его сообщения.</i>"
    )

    await message.answer(
        "\n".join(text_parts),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


# Выход из комнаты чата с сохранением диалога
@dp.message(F.chat.type == "private", F.text.regexp(r"^⬅️ Выйти из чата.*$"))
async def handle_leave_chat(message: types.Message):
    if not is_operator(message.from_user.id):
        return

    operator_id = message.from_user.id
    focused_id = db.leave_current_chat(operator_id)
    open_dialogs = db.get_open_dialogs_for_operator(operator_id)

    if focused_id:
        user_info = db.get_user(focused_id)
        name = user_info.get("user_name") if user_info else "Клиент"
        status_msg = f"💾 <b>Чат с {html.escape(name)} сохранён!</b> Диалог не закончен, вы вышли в список чатов."
    else:
        status_msg = "Вы находитесь вне активных чатов."

    kb_reply = get_operator_keyboard(operator_id)

    if open_dialogs:
        buttons = []
        text_lines = [status_msg, "\n📋 <b>Ваши открытые чаты:</b>"]
        for idx, d in enumerate(open_dialogs, start=1):
            cid = d["client_id"]
            cname = d.get("user_name") or f"Клиент {cid}"
            cuser = f"@{d.get('username')}" if d.get('username') else f"ID: {cid}"
            text_lines.append(f"{idx}. 💬 <b>{html.escape(cname)}</b> ({cuser})")
            row = []
            if WEBAPP_URL:
                row.append(InlineKeyboardButton(text=f"📱 Окно: {cname[:10]}", web_app=types.WebAppInfo(url=f"{WEBAPP_URL}/chat?client_id={cid}")))
            row.append(InlineKeyboardButton(text=f"🚪 Открыть: {cname[:15]}", callback_data=f"start_dialog:{cid}"))
            buttons.append(row)

        buttons.append([InlineKeyboardButton(text="❌ Завершить все открытые диалоги", callback_data="close_all_dialogs")])
        await message.answer(
            "\n".join(text_lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        if kb_reply:
            await message.answer("Для входа нажмите кнопку выше или выберите чат в панели:", reply_markup=kb_reply)
    else:
        await message.answer(status_msg, reply_markup=ReplyKeyboardRemove())


@dp.callback_query(F.data == "close_all_dialogs")
async def handle_close_all_dialogs_callback(callback: types.CallbackQuery):
    operator_id = callback.from_user.id
    clients = db.close_all_dialogs_for_operator(operator_id)
    await callback.answer("Все диалоги завершены.")
    for cid in clients:
        try:
            await bot.send_message(chat_id=cid, text="Диалог закончен.")
        except Exception:
            pass
    try:
        await callback.message.edit_text("✅ Все активные диалоги завершены.")
    except Exception:
        pass
    await bot.send_message(
        chat_id=operator_id,
        text="Диалог закончен.",
        reply_markup=ReplyKeyboardRemove()
    )


# Обработка личных сообщений (ЛС с ботом)
@dp.message(F.chat.type == "private")
async def handle_private_message(message: types.Message, state: FSMContext):
    # Если пользователь находится в процессе прохождения анкеты — не перехватываем
    current_state = await state.get_state()
    if current_state is not None:
        return

    sender_id = message.from_user.id

    # -------------------------------------------------------------
    # ВЕТКА ОПЕРАТОРА (7875791813 и OWNER_IDS)
    # -------------------------------------------------------------
    if is_operator(sender_id):
        # 1. Завершение диалога (кнопка в нижней панели)
        if message.text and (
            message.text.strip().startswith("❌ Завершить диалог")
            or message.text.strip().startswith("❌ Закончить диалог")
            or message.text.strip() in ["Закончить диалог", "Завершить диалог"]
        ):
            focused_id = db.get_active_dialog_for_operator(sender_id)
            if not focused_id:
                open_dialogs = db.get_open_dialogs_for_operator(sender_id)
                if open_dialogs:
                    await handle_show_dialogs_list(message)
                else:
                    await message.answer("У вас нет активного диалога.", reply_markup=ReplyKeyboardRemove())
                return

            client_info = db.get_user(focused_id)
            client_name = client_info.get("user_name") if client_info else "Клиент"

            # Закрываем диалог с этим клиентом
            db.close_active_dialog_for_operator(sender_id, focused_id)
            try:
                await bot.send_message(chat_id=focused_id, text="Диалог закончен.")
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление клиенту {focused_id}: {e}")

            # Проверяем оставшиеся открытые диалоги оператора
            remaining = db.get_open_dialogs_for_operator(sender_id)
            if remaining:
                next_id = db.get_active_dialog_for_operator(sender_id)
                next_info = db.get_user(next_id) if next_id else None
                next_name = next_info.get("user_name") if next_info else "Клиент"
                kb = get_operator_keyboard(sender_id)
                await message.answer(
                    f"Диалог с <b>{html.escape(client_name)}</b> завершён.\n\n"
                    f"🟢 Вы автоматически переключены в чат с: <b>{html.escape(next_name)}</b>.",
                    parse_mode="HTML",
                    reply_markup=kb
                )
            else:
                await message.answer(
                    f"Диалог с <b>{html.escape(client_name)}</b> завершён.\nВсе диалоги закрыты.",
                    parse_mode="HTML",
                    reply_markup=ReplyKeyboardRemove()
                )
            return

        # 2. Определение целевого клиента: через Reply или текущий фокус
        target_client_id = None
        is_reply = False

        # Проверяем, ответил ли оператор через Reply на конкретное сообщение клиента
        if message.reply_to_message:
            target_client_id = db.get_client_by_operator_msg_id(
                message.reply_to_message.message_id,
                message.from_user.id
            )
            if target_client_id:
                is_reply = True

        # Если не Reply — отправляем клиенту в текущем фокусе
        if not target_client_id:
            target_client_id = db.get_active_dialog_for_operator(sender_id)

        if target_client_id:
            text_content = message.text or message.caption or ""
            # Внутренние заметки оператора, начинающиеся с #, клиенту не отправляем
            if text_content.strip().startswith("#"):
                logger.info(f"Внутренняя заметка оператора #{text_content[:30]} (клиенту не отправляется).")
                return

            try:
                await bot.copy_message(
                    chat_id=target_client_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id
                )
                op_text = message.text or message.caption or (f"[{message.content_type}]" if message.content_type else "Сообщение")
                db.save_chat_message(
                    client_id=target_client_id,
                    sender_type="operator",
                    sender_id=sender_id,
                    text=op_text,
                    media_type=str(message.content_type or "text")
                )
                # Авто-обновление открытого диалогового окна на экране оператора
                w_msg_id = db.get_dialog_window_msg_id(sender_id, target_client_id)
                if w_msg_id:
                    try:
                        new_win_text = format_dialog_window_text(target_client_id, sender_id)
                        await bot.edit_message_text(
                            chat_id=sender_id,
                            message_id=w_msg_id,
                            text=new_win_text,
                            parse_mode="HTML",
                            reply_markup=get_dialog_window_keyboard(target_client_id)
                        )
                    except Exception:
                        pass

                target_info = db.get_user(target_client_id)
                t_name = target_info.get("user_name") if target_info else "Клиент"
                try:
                    confirm = await message.reply(f"✓ Доставлено: <b>{html.escape(t_name)}</b>", parse_mode="HTML")
                    asyncio.create_task(_auto_delete_message(confirm, delay=3))
                except Exception:
                    pass
            except TelegramForbiddenError:
                await message.answer("⚠️ Сообщение не доставлено: пользователь заблокировал бота.")
            except Exception as e:
                err_str = str(e).lower()
                if "blocked" in err_str or "deactivated" in err_str or "can't initiate" in err_str:
                    await message.answer("⚠️ Сообщение не доставлено: пользователь заблокировал бота.")
                else:
                    logger.error(f"Ошибка отправки клиенту {target_client_id}: {e}")
                    await message.answer(f"❌ Ошибка отправки клиенту: {e}")
            return
        else:
            # У оператора нет сфокусированного диалога в данный момент
            open_dialogs = db.get_open_dialogs_for_operator(sender_id)
            if open_dialogs:
                buttons = [
                    [InlineKeyboardButton(text=f"🚪 Открыть окно: {d.get('user_name', 'Клиент')[:15]}", callback_data=f"start_dialog:{d['client_id']}")]
                    for d in open_dialogs
                ]
                await message.answer(
                    "Вы сейчас находитесь вне конкретного чата (диалоги сохранены).\n"
                    "Выберите, чьё диалоговое окно открыть, или ответьте на сообщение через Reply:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
                )
            else:
                await message.answer(
                    "У вас сейчас нет активного диалога.\n\n"
                    "Нажмите кнопку «💬 Открыть окно диалога» под карточкой клиента или ответьте на его сообщение через Reply.",
                    reply_markup=ReplyKeyboardRemove()
                )
            return

    # -------------------------------------------------------------
    # ВЕТКА КЛИЕНТА (Обычный пользователь)
    # -------------------------------------------------------------
    client_id = sender_id

    # Если анкета ещё не завершена
    if not db.is_survey_completed(client_id):
        await message.answer(
            "Чтобы начать, пожалуйста, нажмите /start для прохождения разбора кожи."
        )
        return

    user_info = db.get_user(client_id)
    client_name = user_info.get("user_name") if user_info else (message.from_user.first_name or "Клиент")
    username_display = f"@{message.from_user.username}" if message.from_user.username else f"ID: {client_id}"

    # Сохраняем сообщение клиента в историю переписки
    c_text = message.text or message.caption or (f"[{message.content_type}]" if message.content_type else "Сообщение")
    db.save_chat_message(
        client_id=client_id,
        sender_type="client",
        sender_id=client_id,
        text=c_text,
        media_type=str(message.content_type or "text")
    )

    # Проверяем, есть ли активный диалог с оператором
    active_operator_id = db.get_active_dialog_for_client(client_id)
    if active_operator_id:
        # Кнопка под сообщением для быстрого переключения фокуса оператора
        focused_now = db.get_active_dialog_for_operator(active_operator_id)
        kb_reply = get_dialog_inline_keyboard(client_id, is_active=(focused_now == client_id))

        try:
            # 1. Заголовок с именем клиента
            header_msg = await bot.send_message(
                chat_id=active_operator_id,
                text=f"📩 <b>{html.escape(client_name)}</b> ({username_display}):",
                parse_mode="HTML"
            )
            db.save_message_routing(
                operator_msg_id=header_msg.message_id,
                operator_id=active_operator_id,
                client_id=client_id
            )

            # 2. Само сообщение
            copied = await bot.copy_message(
                chat_id=active_operator_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                reply_markup=kb_reply
            )
            # 3. Сохраняем в таблицу маршрутизации для точного ответа через Reply
            db.save_message_routing(
                operator_msg_id=copied.message_id,
                operator_id=active_operator_id,
                client_id=client_id
            )

            # 4. Авто-обновление диалогового окна на экране оператора
            w_msg_id = db.get_dialog_window_msg_id(active_operator_id, client_id)
            if w_msg_id:
                try:
                    new_win_text = format_dialog_window_text(client_id, active_operator_id)
                    await bot.edit_message_text(
                        chat_id=active_operator_id,
                        message_id=w_msg_id,
                        text=new_win_text,
                        parse_mode="HTML",
                        reply_markup=get_dialog_window_keyboard(client_id)
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Не удалось доставить сообщение оператору {active_operator_id}: {e}")

        # Также дублируем в топик супергруппы, если настроена
        op_chat_id = get_operator_chat_id()
        if op_chat_id and user_info and user_info.get("thread_id"):
            try:
                await bot.copy_message(
                    chat_id=op_chat_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                    message_thread_id=user_info["thread_id"]
                )
            except Exception:
                pass
        return

    # Диалог сейчас НЕ активен, но клиент отправил сообщение после прохождения анкеты
    await message.answer("Ваше сообщение получено. Скоро я отвечу вам прямо сюда.")

    kb_dialog = get_dialog_inline_keyboard(client_id)

    for oid in get_target_operators():
        try:
            header_msg = await bot.send_message(
                chat_id=oid,
                text=f"📩 <b>Новое сообщение от клиента {html.escape(client_name)} ({username_display}):</b>",
                parse_mode="HTML"
            )
            db.save_message_routing(
                operator_msg_id=header_msg.message_id,
                operator_id=oid,
                client_id=client_id
            )
            copied = await bot.copy_message(
                chat_id=oid,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                reply_markup=kb_dialog
            )
            db.save_message_routing(
                operator_msg_id=copied.message_id,
                operator_id=oid,
                client_id=client_id
            )
        except Exception as e:
            logger.error(f"Не удалось переслать сообщение оператору {oid}: {e}")

    # Если настроена супергруппа с топиками
    op_chat_id = get_operator_chat_id()
    if op_chat_id:
        thread_id = user_info.get("thread_id") if user_info else None
        if not thread_id:
            thread_id = await ensure_operator_topic(client_id, client_name, message.from_user.username)
        if thread_id:
            try:
                await bot.copy_message(
                    chat_id=op_chat_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                    message_thread_id=thread_id
                )
            except Exception:
                pass


# ================== СТАРТ ПРИЛОЖЕНИЯ ==================
async def main():
    if BOT_TOKEN.startswith("0000000000:"):
        logger.error("❌ Невозможно запустить бота без настоящего BOT_TOKEN! Добавьте BOT_TOKEN в .env или переменные окружения.")
        return
    db.init_db()
    op_chat_id = get_operator_chat_id()
    logger.info("🚀 Бот «Анкета» запущен.")
    if op_chat_id:
        logger.info(f"Операторский чат топиков: {op_chat_id}")
    else:
        logger.warning("⚠️ Внимание: OPERATOR_CHAT_ID не настроен! Установите его в .env или командой /set_group в группе.")

    # Запуск встроенного веб-сервера для Telegram Mini App (Web App)
    webapp_server = WebAppServer(bot=bot, port=WEBAPP_PORT)
    await webapp_server.start()

    try:
        await dp.start_polling(bot)
    finally:
        await webapp_server.stop()


if __name__ == "__main__":
    asyncio.run(main())
