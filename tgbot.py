import os
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# ================== НАСТРОЙКА ЛОГОВ ==================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================== КОНФИГУРАЦИЯ ==================
# Токен берётся из переменной окружения BOT_TOKEN (на хостинге)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Для локального запуска можно раскомментировать строку ниже и вставить токен
# BOT_TOKEN = "8548303676:AAEqidzHcX_L2boj8oyZLfo_cspdP_Bw-4U"

# Проверка: если токен не найден — бот не запустится
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Добавьте переменную окружения BOT_TOKEN или вставьте токен в код.")

OWNER_ID = 1745568601  # Твой Telegram ID

IMAGE_URL = "https://pbt.storage.yandexcloud.net/cp_upload/3226d6315635f4e60bebd98a6421ea7a_full.jpeg"

# ================== ИНИЦИАЛИЗАЦИЯ ==================
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)


# ================== FSM СОСТОЯНИЯ ==================
class Form(StatesGroup):
    waiting_for_start = State()
    full_name = State()
    phone = State()
    birth_date = State()
    source = State()
    contraindications = State()
    jaw_tension = State()
    tension_areas = State()
    morning_face = State()
    habits = State()
    face_numbness = State()
    chronic_diseases = State()
    medications = State()
    skin_reactions = State()
    skin_conditions = State()
    main_concerns = State()
    pigmentation = State()
    phototype = State()
    skin_type = State()
    skin_condition = State()
    skin_texture = State()
    skin_issues = State()
    skin_sensitivity = State()
    priorities = State()
    city = State()
    departure_date = State()
    procedures = State()
    home_care = State()
    success_criteria = State()


# ================== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ КЛАВИАТУР ==================
def make_keyboard(buttons_list, cols=1):
    keyboard = []
    for i in range(0, len(buttons_list), cols):
        row = buttons_list[i:i+cols]
        keyboard.append([KeyboardButton(text=btn) for btn in row])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def make_keyboard_with_ready(buttons_list, cols=1):
    keyboard = []
    for i in range(0, len(buttons_list), cols):
        row = buttons_list[i:i+cols]
        keyboard.append([KeyboardButton(text=btn) for btn in row])
    keyboard.append([KeyboardButton(text="Готово")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# ================== КЛАВИАТУРЫ ==================
def get_start_keyboard():
    return make_keyboard(["▶️ СТАРТ"], cols=1)


def get_source_keyboard():
    buttons = [
        "Instagram", "ВК", "Телеграмм", "Авито",
        "Поиск в интернете (Google, Яндекс)",
        "Рекомендация от друга/подруги", "Эвамед", "Другое"
    ]
    return make_keyboard(buttons, cols=2)


def get_contraindications_keyboard():
    buttons = [
        "Беременность (в т.ч. планирование в текущем цикле)",
        "Кормление грудью (лактация)",
        "Прием препаратов изотретиноина (Роаккутан, Акнекутан) в последние 6 месяцев",
        "Онкологическое заболевание в анамнезе (менее 5 лет ремиссии)",
        "Установленный кардиостимулятор, дефибриллятор или другие электронные импланты",
        "Нет ни одного из вышеперечисленного"
    ]
    return make_keyboard(buttons, cols=1)


def get_jaw_tension_keyboard():
    return make_keyboard(["Левая", "Правая", "Одинаково"], cols=3)


def get_tension_areas_keyboard():
    buttons = ["Лоб", "Челюсть, ВНЧС", "Скулы, жевательные мышцы", "Вокруг глаз, переносица", "Шея, затылок"]
    return make_keyboard_with_ready(buttons, cols=2)


def get_morning_face_keyboard():
    buttons = [
        "Отечное, одутловатое", "Тяжелое, зажатое, «каменное»",
        "Помятое, уставшее, несвежее", "Стянутое, сухое, шелушащееся",
        "Нормальное, свежее", "Другое"
    ]
    return make_keyboard(buttons, cols=2)


def get_habits_keyboard():
    buttons = [
        "Сжимаю челюсти, скриплю зубами (бруксизм)",
        "Подпираю щеку или подбородок рукой",
        "Щурюсь, тру глаза, хмурю брови",
        "Кладу телефонную трубку между ухом и плечом",
        "Сплю на животе или на боку, уткнувшись лицом в подушку",
        "Не замечаю таких привычек"
    ]
    return make_keyboard_with_ready(buttons, cols=1)


def get_face_numbness_keyboard():
    return make_keyboard(["Да, часто", "Иногда", "Нет"], cols=3)


def get_phototype_keyboard():
    buttons = [
        "I — Всегда обгораю, почти не загораю",
        "II — Часто обгораю, загар ложится с трудом",
        "III — Иногда обгораю, затем загораю",
        "IV — Редко обгораю, загораю хорошо",
        "V-VI — Практически не обгораю, кожа смуглая/темная"
    ]
    return make_keyboard(buttons, cols=1)


def get_skin_type_keyboard():
    return make_keyboard(["Жирная", "Сухая", "Комбинированная", "Нормальная"], cols=2)


def get_skin_condition_keyboard():
    return make_keyboard(["Обезвоженная", "Чувствительная/Реактивная", "Резистентная (устойчивая)"], cols=1)


def get_skin_texture_keyboard():
    buttons = ["Гладкая, ровная", "Шероховатая, с мелкими бугорками", "Истонченная, 'пергаментная'", "Утолщенная, плотная"]
    return make_keyboard(buttons, cols=2)


def get_skin_issues_keyboard():
    buttons = ["Пигментные пятна, веснушки", "Глубокие морщины в покое", "Сильная сухость и шелушение", "Ничего из перечисленного"]
    return make_keyboard_with_ready(buttons, cols=2)


def get_skin_sensitivity_keyboard():
    buttons = [
        "Нормальная, почти не реагирует", "Легкое покраснение после процедур",
        "Частое жжение, шелушение от косметики", "Диагностированная розацеа/купероз"
    ]
    return make_keyboard(buttons, cols=2)


def get_success_criteria_keyboard():
    buttons = [
        "Визуальный (Архитектоника): Ушла «серость», появился ровный здоровый тон, ткани лица стали визуально плотнее.",
        "Тактильный (Физиология барьера): Кожа перестала «болеть» и реагировать на всё подряд, ушли стянутость и шелушения.",
        "Функциональный (Свобода): Лицо больше не требует слоя тонального крема для маскировки, а сам уход занимает пару минут.",
        "Эмоциональный (Самоощущение): Я снова с удовольствием смотрю на себя в зеркало по утрам без чувства тревоги.",
        "Разрыв шаблона (Доверие): Хочу наконец-то увидеть реальную работу химии на своем лице после десятков бесполезных баночек."
    ]
    return make_keyboard(buttons, cols=1)


def get_medications_keyboard():
    buttons = [
        "Антикоагулянты (Варфарин, Ксарелто, Эликвис и т.д.)",
        "Гормональные препараты (оральные контрацептивы, ЗГТ, терапия для щитовидной железы)",
        "Антибиотики длительным курсом",
        "БАДы с разжижающим эффектом (рыбий жир, витамин Е >400 МЕ, гинкго билоба, чеснок)",
        "Нет"
    ]
    return make_keyboard_with_ready(buttons, cols=1)


def get_chronic_diseases_keyboard():
    buttons = [
        "Сахарный диабет",
        "Аутоиммунные заболевания (ревматоидный артрит, волчанка, склеродермия и т.д.)",
        "Эпилепсия",
        "Гипертония (повышенное артериальное давление)",
        "Заболевания щитовидной железы",
        "Нет ничего из перечисленного"
    ]
    return make_keyboard_with_ready(buttons, cols=1)


def get_skin_reactions_keyboard():
    buttons = [
        "Склонность к образованию келоидных или гипертрофических рубцов",
        "Витилиго",
        "Аллергические реакции (укажите на что именно)",
        "Нет"
    ]
    return make_keyboard_with_ready(buttons, cols=1)


def get_skin_conditions_keyboard():
    buttons = [
        "Розацеа, стойкий купероз (сосудистые звездочки)",
        "Акне в воспалительной стадии (гнойнички, папулы)",
        "Дерматит (атопический, себорейный)",
        "Солнечный ожог, полученный в последние 14 дней",
        "Склонность к образованию пигментных пятен",
        "Герпетические высыпания (герпес)",
        "Нет"
    ]
    return make_keyboard_with_ready(buttons, cols=1)


def get_main_concerns_keyboard():
    buttons = ["Мелкие морщинки при мимике", "Глубокие складки, видные в покое", "Обвисшая кожа, 'поплывший' овал", "Общая дряблость, потеря объема"]
    return make_keyboard_with_ready(buttons, cols=2)


def get_pigmentation_keyboard():
    buttons = [
        "Красные/коричневые следы после прыщей",
        "Коричневые пятна на скулах/лбу (как веснушки)",
        "Неравномерный загар, пятна от солнца",
        "Нет пигментации"
    ]
    return make_keyboard_with_ready(buttons, cols=2)


def get_priorities_keyboard():
    buttons = [
        "Морщины, потеря тонуса и упругости (птоз)",
        "Тусклый, неровный цвет лица, гиперпигментация",
        "Отечность, пастозность, нечеткость контура овала",
        "Расширенные поры, жирный блеск, акне/постакне",
        "Купероз, стойкое покраснение, чувствительность",
        "Сухость, шелушение, ощущение поврежденного барьера",
        "Восстановление после инвазивных процедур"
    ]
    return make_keyboard_with_ready(buttons, cols=1)


def get_departure_keyboard():
    return make_keyboard(["Не отдыхаю"], cols=1)


def get_procedures_keyboard():
    return make_keyboard(["Не проходил(а)"], cols=1)


def get_home_care_keyboard():
    return make_keyboard(["Уход отсутствует"], cols=1)


# ================== ОБРАБОТЧИК МНОЖЕСТВЕННОГО ВЫБОРА ==================
async def handle_multiple_choice(message: types.Message, state: FSMContext, field_name: str, keyboard_func, next_state, next_question, next_keyboard_func=None):
    data = await state.get_data()
    selected = data.get(field_name, [])
    
    if message.text and message.text.lower() == "готово":
        if not selected:
            await message.answer(
                "⚠️ Вы не выбрали ни одного варианта. Пожалуйста, выберите хотя бы один вариант:",
                reply_markup=keyboard_func()
            )
            return
        
        await state.update_data({field_name: ", ".join(selected)})
        await state.set_state(next_state)
        
        if next_keyboard_func:
            await message.answer(
                next_question,
                reply_markup=next_keyboard_func()
            )
        else:
            await message.answer(
                next_question,
                reply_markup=ReplyKeyboardRemove()
            )
        return
    
    options_list = []
    for row in keyboard_func().keyboard:
        for btn in row:
            if btn.text != "Готово":
                options_list.append(btn.text)
    
    if message.text in options_list:
        if message.text in selected:
            await message.answer(
                f"⚠️ Вы уже выбрали '{message.text}'. Выберите другой вариант или нажмите 'Готово'.",
                reply_markup=keyboard_func()
            )
            return
        
        selected.append(message.text)
        await state.update_data({field_name: selected})
        
        await message.answer(
            f"✅ Добавлено: {message.text}\nВыбрано: {len(selected)} вариантов.\n\n"
            "Выберите еще вариант или нажмите 'Готово' для завершения.",
            reply_markup=keyboard_func()
        )
        return
    
    await message.answer(
        "Пожалуйста, выберите вариант из кнопок или нажмите 'Готово'.",
        reply_markup=keyboard_func()
    )


# ================== ОБРАБОТЧИК /START ==================
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} запустил бота")
    
    await message.answer_photo(
        photo=IMAGE_URL,
        caption=(
            "Привет! Я Мария Мирославская, косметолог. Рада, что ты здесь.\n\n"
            "Ты сейчас в одном шаге от того, чтобы перестать играть в лотерею со своей кожей "
            "и начать пользоваться работающими активами.\n"
            "Мой подход — это фармакология и химия в действии, а не маркетинговые сказки. "
            "Чтобы я поняла, какие концентрации и компоненты нужны именно тебе, пройди, "
            "пожалуйста, цифровую анкету, которая мне даст полную картину твоего состояния.\n\n"
            "📝 Анкета состоит из 7 разделов. Пожалуйста, отвечайте честно."
        )
    )

    await state.set_state(Form.waiting_for_start)
    await message.answer(
        "⬇️ *Для начала заполнения анкеты нажми кнопку «СТАРТ»* ⬇️",
        parse_mode="Markdown",
        reply_markup=get_start_keyboard()
    )


# ================== ОБРАБОТЧИК КНОПКИ "СТАРТ" ==================
@dp.message(StateFilter(Form.waiting_for_start), F.text == "▶️ СТАРТ")
async def process_start_button(message: types.Message, state: FSMContext):
    await state.set_state(Form.full_name)
    await message.answer(
        "📋 *РАЗДЕЛ 1: ЛИЧНЫЕ ДАННЫЕ*\n\n"
        "Введи свои *Фамилию, Имя и Отчество*:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )


# ================== РАЗДЕЛ 1: ЛИЧНЫЕ ДАННЫЕ ==================
@dp.message(StateFilter(Form.full_name))
async def process_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await state.set_state(Form.phone)
    await message.answer(
        "Введи *контактный телефон* для связи:",
        parse_mode="Markdown"
    )


@dp.message(StateFilter(Form.phone))
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(Form.birth_date)
    await message.answer(
        "Введи свою *дату рождения* в формате *ДД.ММ.ГГГГ*:\n"
        "(например, 25.12.1990)",
        parse_mode="Markdown"
    )


@dp.message(StateFilter(Form.birth_date))
async def process_birth_date(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except ValueError:
        await message.answer(
            "❌ Неверный формат! Введи дату в формате *ДД.ММ.ГГГГ*:\n"
            "(например, 25.12.1990)",
            parse_mode="Markdown"
        )
        return

    await state.update_data(birth_date=message.text.strip())
    await state.set_state(Form.source)
    await message.answer(
        "Как вы о нас узнали?",
        reply_markup=get_source_keyboard()
    )


@dp.message(StateFilter(Form.source))
async def process_source(message: types.Message, state: FSMContext):
    await state.update_data(source=message.text.strip())
    await state.set_state(Form.contraindications)
    await message.answer(
        "📋 *РАЗДЕЛ 2: МЕДИЦИНСКИЙ СКРИНИНГ*\n\n"
        "⚠️ *Критически важный блок для вашей безопасности*\n\n"
        "Есть ли у вас следующие абсолютные противопоказания?",
        parse_mode="Markdown",
        reply_markup=get_contraindications_keyboard()
    )


# ================== РАЗДЕЛ 2: ПРОТИВОПОКАЗАНИЯ ==================
@dp.message(StateFilter(Form.contraindications))
async def process_contraindications(message: types.Message, state: FSMContext):
    await state.update_data(contraindications=message.text.strip())
    
    has_contraindications = message.text.strip() != "Нет ни одного из вышеперечисленного"
    await state.update_data(has_contraindications=has_contraindications)
    
    await state.set_state(Form.jaw_tension)
    await message.answer(
        "📋 *РАЗДЕЛ 3: МИОФАСЦИАЛЬНАЯ ДИАГНОСТИКА*\n\n"
        "💆‍♀️ *Тест: Сожмите челюсти, положив пальцы на виски.*\n\n"
        "Какая сторона ощущается более напряженной?",
        parse_mode="Markdown",
        reply_markup=get_jaw_tension_keyboard()
    )


# ================== РАЗДЕЛ 3: МИОФАСЦИАЛЬНАЯ ДИАГНОСТИКА ==================
@dp.message(StateFilter(Form.jaw_tension))
async def process_jaw_tension(message: types.Message, state: FSMContext):
    await state.update_data(jaw_tension=message.text.strip())
    await state.set_state(Form.tension_areas)
    await message.answer(
        "Где вы чаще всего ощущаете напряжение, даже в покое? (Выберите несколько вариантов)\n\n"
        "Выберите варианты из кнопок. Когда закончите, нажмите 'Готово'.",
        reply_markup=get_tension_areas_keyboard()
    )


@dp.message(StateFilter(Form.tension_areas))
async def process_tension_areas(message: types.Message, state: FSMContext):
    await handle_multiple_choice(
        message, state,
        field_name="tension_areas",
        keyboard_func=get_tension_areas_keyboard,
        next_state=Form.morning_face,
        next_question="Опишите привычное утреннее состояние вашего лица:",
        next_keyboard_func=get_morning_face_keyboard
    )


@dp.message(StateFilter(Form.morning_face))
async def process_morning_face(message: types.Message, state: FSMContext):
    await state.update_data(morning_face=message.text.strip())
    await state.set_state(Form.habits)
    await message.answer(
        "Отметьте привычки, которые замечаете за собой: (Выберите несколько вариантов)\n\n"
        "Выберите варианты из кнопок. Когда закончите, нажмите 'Готово'.",
        reply_markup=get_habits_keyboard()
    )


@dp.message(StateFilter(Form.habits))
async def process_habits(message: types.Message, state: FSMContext):
    await handle_multiple_choice(
        message, state,
        field_name="habits",
        keyboard_func=get_habits_keyboard,
        next_state=Form.face_numbness,
        next_question="Бывает ли у вас чувство онемения, «маски» или покалывания на лице?",
        next_keyboard_func=get_face_numbness_keyboard
    )


@dp.message(StateFilter(Form.face_numbness))
async def process_face_numbness(message: types.Message, state: FSMContext):
    await state.update_data(face_numbness=message.text.strip())
    await state.set_state(Form.chronic_diseases)
    await message.answer(
        "📋 *РАЗДЕЛ 4: ДИАГНОСТИКА КОЖИ И ЦЕЛИ*\n\n"
        "🔍 *Пожалуйста, опишите состояние вашей кожи*\n\n"
        "Есть ли у вас хронические заболевания? (Выберите несколько вариантов)\n\n"
        "Выберите варианты из кнопок. Когда закончите, нажмите 'Готово'.",
        parse_mode="Markdown",
        reply_markup=get_chronic_diseases_keyboard()
    )


# ================== РАЗДЕЛ 4: ДИАГНОСТИКА КОЖИ ==================
@dp.message(StateFilter(Form.chronic_diseases))
async def process_chronic_diseases(message: types.Message, state: FSMContext):
    await handle_multiple_choice(
        message, state,
        field_name="chronic_diseases",
        keyboard_func=get_chronic_diseases_keyboard,
        next_state=Form.medications,
        next_question="Принимаете ли вы в настоящее время или принимали курсом в последние 3 месяца: (Выберите несколько вариантов)\n\nВыберите варианты из кнопок. Когда закончите, нажмите 'Готово'.",
        next_keyboard_func=get_medications_keyboard
    )


@dp.message(StateFilter(Form.medications))
async def process_medications(message: types.Message, state: FSMContext):
    await handle_multiple_choice(
        message, state,
        field_name="medications",
        keyboard_func=get_medications_keyboard,
        next_state=Form.skin_reactions,
        next_question="Отмечалась ли у вас склонность к следующим реакциям? (Выберите несколько вариантов)\n\nВыберите варианты из кнопок. Когда закончите, нажмите 'Готово'.",
        next_keyboard_func=get_skin_reactions_keyboard
    )


@dp.message(StateFilter(Form.skin_reactions))
async def process_skin_reactions(message: types.Message, state: FSMContext):
    await handle_multiple_choice(
        message, state,
        field_name="skin_reactions",
        keyboard_func=get_skin_reactions_keyboard,
        next_state=Form.skin_conditions,
        next_question="Имеются ли у вас в настоящее время или часто рецидивируют? (Выберите несколько вариантов)\n\nВыберите варианты из кнопок. Когда закончите, нажмите 'Готово'.",
        next_keyboard_func=get_skin_conditions_keyboard
    )


@dp.message(StateFilter(Form.skin_conditions))
async def process_skin_conditions(message: types.Message, state: FSMContext):
    await handle_multiple_choice(
        message, state,
        field_name="skin_conditions",
        keyboard_func=get_skin_conditions_keyboard,
        next_state=Form.main_concerns,
        next_question="Какие изменения беспокоят больше всего? (Выберите несколько вариантов)\n\nВыберите варианты из кнопок. Когда закончите, нажмите 'Готово'.",
        next_keyboard_func=get_main_concerns_keyboard
    )


@dp.message(StateFilter(Form.main_concerns))
async def process_main_concerns(message: types.Message, state: FSMContext):
    await handle_multiple_choice(
        message, state,
        field_name="main_concerns",
        keyboard_func=get_main_concerns_keyboard,
        next_state=Form.pigmentation,
        next_question="Если есть пятна на коже, они: (Выберите несколько вариантов)\n\nВыберите варианты из кнопок. Когда закончите, нажмите 'Готово'.",
        next_keyboard_func=get_pigmentation_keyboard
    )


@dp.message(StateFilter(Form.pigmentation))
async def process_pigmentation(message: types.Message, state: FSMContext):
    await handle_multiple_choice(
        message, state,
        field_name="pigmentation",
        keyboard_func=get_pigmentation_keyboard,
        next_state=Form.phototype,
        next_question="Как ваша кожа реагирует на 30 минут пребывания на активном солнце без защиты?\n(Определение фототипа)",
        next_keyboard_func=get_phototype_keyboard
    )


@dp.message(StateFilter(Form.phototype))
async def process_phototype(message: types.Message, state: FSMContext):
    await state.update_data(phototype=message.text.strip())
    await state.set_state(Form.skin_type)
    await message.answer(
        "Какой у вас тип кожи в последние 3 месяца?",
        reply_markup=get_skin_type_keyboard()
    )


@dp.message(StateFilter(Form.skin_type))
async def process_skin_type(message: types.Message, state: FSMContext):
    await state.update_data(skin_type=message.text.strip())
    await state.set_state(Form.skin_condition)
    await message.answer(
        "Как бы вы охарактеризовали состояние своей кожи в последние 3 месяца?",
        reply_markup=get_skin_condition_keyboard()
    )


@dp.message(StateFilter(Form.skin_condition))
async def process_skin_condition(message: types.Message, state: FSMContext):
    await state.update_data(skin_condition=message.text.strip())
    await state.set_state(Form.skin_texture)
    await message.answer(
        "Какова ТЕКСТУРА вашей кожи?",
        reply_markup=get_skin_texture_keyboard()
    )


@dp.message(StateFilter(Form.skin_texture))
async def process_skin_texture(message: types.Message, state: FSMContext):
    await state.update_data(skin_texture=message.text.strip())
    await state.set_state(Form.skin_issues)
    await message.answer(
        "ДОБАВЬТЕ варианты: (Выберите несколько вариантов)\n\n"
        "Выберите варианты из кнопок. Когда закончите, нажмите 'Готово'.",
        reply_markup=get_skin_issues_keyboard()
    )


@dp.message(StateFilter(Form.skin_issues))
async def process_skin_issues(message: types.Message, state: FSMContext):
    await handle_multiple_choice(
        message, state,
        field_name="skin_issues",
        keyboard_func=get_skin_issues_keyboard,
        next_state=Form.skin_sensitivity,
        next_question="Оцените ЧУВСТВИТЕЛЬНОСТЬ вашей кожи:",
        next_keyboard_func=get_skin_sensitivity_keyboard
    )


@dp.message(StateFilter(Form.skin_sensitivity))
async def process_skin_sensitivity(message: types.Message, state: FSMContext):
    await state.update_data(skin_sensitivity=message.text.strip())
    await state.set_state(Form.priorities)
    await message.answer(
        "📋 *РАЗДЕЛ 4: ДИАГНОСТИКА КОЖИ И ЦЕЛИ (продолжение)*\n\n"
        "Выберите до 3-х главных задач, которые необходимо решить\n\n"
        "Нажмите на кнопку с задачей, чтобы добавить её в список.\n"
        "Когда выберете все задачи, нажмите 'Готово'.",
        parse_mode="Markdown",
        reply_markup=get_priorities_keyboard()
    )


@dp.message(StateFilter(Form.priorities))
async def process_priorities(message: types.Message, state: FSMContext):
    if 'priorities_list' not in await state.get_data():
        await state.update_data(priorities_list=[])
    
    data = await state.get_data()
    priorities_list = data.get('priorities_list', [])
    
    options_list = [
        "Морщины, потеря тонуса и упругости (птоз)",
        "Тусклый, неровный цвет лица, гиперпигментация",
        "Отечность, пастозность, нечеткость контура овала",
        "Расширенные поры, жирный блеск, акне/постакне",
        "Купероз, стойкое покраснение, чувствительность",
        "Сухость, шелушение, ощущение поврежденного барьера",
        "Восстановление после инвазивных процедур"
    ]
    
    if message.text and message.text.lower() == "готово":
        if len(priorities_list) == 0:
            await message.answer(
                "⚠️ Вы не выбрали ни одной задачи. Выберите хотя бы одну:",
                reply_markup=get_priorities_keyboard()
            )
            return
        
        await state.update_data(priorities=", ".join(priorities_list))
        await state.set_state(Form.city)
        await message.answer(
            "Из какого Вы города?",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    if message.text in options_list:
        if message.text in priorities_list:
            await message.answer(
                f"⚠️ Вы уже выбрали '{message.text}'. Выберите другую задачу или нажмите 'Готово'.",
                reply_markup=get_priorities_keyboard()
            )
            return
        
        priorities_list.append(message.text)
        await state.update_data(priorities_list=priorities_list)
        
        if len(priorities_list) < 3:
            await message.answer(
                f"✅ Добавлено: {message.text}\n"
                f"Выбрано {len(priorities_list)} из 3.\n\n"
                "Выберите следующую задачу или нажмите 'Готово' для завершения.",
                reply_markup=get_priorities_keyboard()
            )
        else:
            await message.answer(
                "✅ Выбрано 3 задачи. Завершаем выбор.",
                reply_markup=ReplyKeyboardRemove()
            )
            await state.update_data(priorities=", ".join(priorities_list))
            await state.set_state(Form.city)
            await message.answer(
                "Из какого Вы города?",
                reply_markup=ReplyKeyboardRemove()
            )
        return
    
    await message.answer(
        "Нажмите на кнопку с задачей или нажмите 'Готово'",
        reply_markup=get_priorities_keyboard()
    )


@dp.message(StateFilter(Form.city))
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    await state.set_state(Form.departure_date)
    await message.answer(
        "Если вы отдыхающий, укажите примерную дату отъезда\n"
        "(например, 15.08.2026)\n\n"
        "Или нажмите кнопку:",
        reply_markup=get_departure_keyboard()
    )


@dp.message(StateFilter(Form.departure_date))
async def process_departure_date(message: types.Message, state: FSMContext):
    if message.text == "Не отдыхаю":
        await state.update_data(departure_date="Не отдыхаю")
    else:
        await state.update_data(departure_date=message.text.strip())
    
    await state.set_state(Form.procedures)
    await message.answer(
        "📋 *РАЗДЕЛ 5: АНАМНЕЗ И ОЖИДАНИЯ*\n\n"
        "Какие профессиональные косметологические процедуры вы проходили за последние 12 месяцев?\n"
        "(Чистки, пилинги, инъекции, лазер, RF, нити и т.д.)\n\n"
        "Если были нитевые методики (мезонити, лигатурные нити), укажите дату\n\n"
        "Напишите подробно или нажмите кнопку:",
        parse_mode="Markdown",
        reply_markup=get_procedures_keyboard()
    )


@dp.message(StateFilter(Form.procedures))
async def process_procedures(message: types.Message, state: FSMContext):
    if message.text == "Не проходил(а)":
        await state.update_data(procedures="Не проходил(а)")
    else:
        await state.update_data(procedures=message.text.strip())
    
    await state.set_state(Form.home_care)
    await message.answer(
        "Опишите ваш текущий домашний уход:\n\n"
        "Очищение: ...\n"
        "Активные сыворотки: ...\n"
        "Крем: ...\n"
        "SPF: ...\n\n"
        "Напишите подробно или нажмите кнопку:",
        reply_markup=get_home_care_keyboard()
    )


@dp.message(StateFilter(Form.home_care))
async def process_home_care(message: types.Message, state: FSMContext):
    if message.text == "Уход отсутствует":
        await state.update_data(home_care="Уход отсутствует")
    else:
        await state.update_data(home_care=message.text.strip())
    
    await state.set_state(Form.success_criteria)
    await message.answer(
        "Сформулируйте главный критерий успеха спустя первый месяц использования Индивидуального Протокола:\n\n"
        "Выберите один вариант:",
        reply_markup=get_success_criteria_keyboard()
    )


@dp.message(StateFilter(Form.success_criteria))
async def process_success_criteria(message: types.Message, state: FSMContext):
    await state.update_data(success_criteria=message.text.strip())
    
    data = await state.get_data()
    
    report = (
        "📋 *ПОЛНАЯ АНКЕТА КЛИЕНТА*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "*📌 РАЗДЕЛ 1: ЛИЧНЫЕ ДАННЫЕ*\n"
        f"👤 ФИО: {data.get('full_name', '—')}\n"
        f"📞 Телефон: {data.get('phone', '—')}\n"
        f"🎂 Дата рождения: {data.get('birth_date', '—')}\n"
        f"🔍 Откуда узнали: {data.get('source', '—')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "*⚠️ РАЗДЕЛ 2: ПРОТИВОПОКАЗАНИЯ*\n"
        f"Противопоказания: {data.get('contraindications', '—')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "*💆‍♀️ РАЗДЕЛ 3: МИОФАСЦИАЛЬНАЯ ДИАГНОСТИКА*\n"
        f"Напряжение челюстей: {data.get('jaw_tension', '—')}\n"
        f"Зоны напряжения: {data.get('tension_areas', '—')}\n"
        f"Утреннее состояние: {data.get('morning_face', '—')}\n"
        f"Привычки: {data.get('habits', '—')}\n"
        f"Онемение/покалывание: {data.get('face_numbness', '—')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "*🔍 РАЗДЕЛ 4: ДИАГНОСТИКА КОЖИ*\n"
        f"Хронические заболевания: {data.get('chronic_diseases', '—')}\n"
        f"Принимаемые препараты: {data.get('medications', '—')}\n"
        f"Кожные реакции: {data.get('skin_reactions', '—')}\n"
        f"Состояния кожи: {data.get('skin_conditions', '—')}\n"
        f"Основные изменения: {data.get('main_concerns', '—')}\n"
        f"Пигментация: {data.get('pigmentation', '—')}\n"
        f"Фототип: {data.get('phototype', '—')}\n"
        f"Тип кожи: {data.get('skin_type', '—')}\n"
        f"Состояние кожи: {data.get('skin_condition', '—')}\n"
        f"Текстура кожи: {data.get('skin_texture', '—')}\n"
        f"Проблемы кожи: {data.get('skin_issues', '—')}\n"
        f"Чувствительность: {data.get('skin_sensitivity', '—')}\n"
        f"Приоритеты: {data.get('priorities', '—')}\n"
        f"Город: {data.get('city', '—')}\n"
        f"Дата отъезда: {data.get('departure_date', '—')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "*📖 РАЗДЕЛ 5: АНАМНЕЗ И ОЖИДАНИЯ*\n"
        f"Процедуры: {data.get('procedures', '—')}\n"
        f"Домашний уход: {data.get('home_care', '—')}\n"
        f"Критерий успеха: {data.get('success_criteria', '—')}\n\n"
        f"👤 Username: `{message.from_user.username if message.from_user.username else 'Не указан'}`"
    )
    
    if data.get('has_contraindications', False):
        report += "\n\n⚠️ *ВНИМАНИЕ: У КЛИЕНТА ЕСТЬ ПРОТИВОПОКАЗАНИЯ!*"
    
    try:
        await bot.send_message(chat_id=OWNER_ID, text=report, parse_mode="Markdown")
        logger.info(f"Анкета отправлена владельцу {OWNER_ID}")
    except Exception as e:
        logger.error(f"Не удалось отправить владельцу: {e}")
    
    if data.get('has_contraindications', False):
        await message.answer(
            "⚠️ *Важно!*\n\n"
            "На основании ваших ответов выявлены временные или постоянные противопоказания.\n\n"
            "Пожалуйста, свяжитесь с нами по телефону *+7913 126 4511* для обсуждения возможных вариантов.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
    
    await message.answer(
        "✅ *Спасибо! Анкета успешно отправлена.*\n\n"
        "На основании этих данных для вас будет подготовлен предварительный протокол.\n\n"
        "Специалист свяжется с вами для согласования времени консультации.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await state.clear()


# ================== ОБРАБОТКА ДРУГИХ СООБЩЕНИЙ ==================
@dp.message()
async def handle_other_messages(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    logger.info(f"Получено сообщение от {message.from_user.id}: {message.text}, состояние: {current_state}")
    
    if current_state == Form.waiting_for_start:
        await message.answer(
            "⬇️ *Для начала заполнения анкеты нажми кнопку «СТАРТ»* ⬇️",
            parse_mode="Markdown",
            reply_markup=get_start_keyboard()
        )
    else:
        await message.answer(
            "Пожалуйста, нажми /start, чтобы начать заполнение анкеты."
        )


# ================== ЗАПУСК БОТА ==================
async def main():
    logger.info("🚀 Бот запущен и готов к работе!")
    print("Бот запущен! Нажми Ctrl+C для остановки.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
