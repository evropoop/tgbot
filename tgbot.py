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
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Добавьте переменную окружения BOT_TOKEN.")

OWNER_ID = 1745568601
IMAGE_URL = "https://pbt.storage.yandexcloud.net/cp_upload/3226d6315635f4e60bebd98a6421ea7a_full.jpeg"

# ================== ИНИЦИАЛИЗАЦИЯ ==================
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)


# ================== FSM СОСТОЯНИЯ ==================
class Form(StatesGroup):
    waiting_for_start = State()
    priorities = State()
    skin_type = State()
    phototype = State()
    barrier_state = State()
    visual_markers = State()
    sos_conditions = State()
    morning_face = State()
    tension_areas = State()
    jaw_tension = State()
    habits = State()
    face_numbness = State()
    contraindications = State()
    chronic_diseases = State()
    medications = State()
    allergies = State()
    procedures = State()
    home_care = State()
    active_experience = State()
    success_criteria = State()
    full_name = State()
    phone = State()
    city = State()
    climate_change = State()
    birth_date = State()
    source = State()


# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================
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


def get_priorities_keyboard():
    buttons = [
        "Морщины и потеря тонуса",
        "Тусклый цвет лица, пигментация",
        "Отечность, пастозность",
        "Расширенные поры, акне, блеск",
        "Купероз и краснота",
        "Сухость и поврежденный барьер"
    ]
    return make_keyboard_with_ready(buttons, cols=1)


def get_skin_type_keyboard():
    return make_keyboard(["Жирная", "Сухая", "Комбинированная", "Нормальная"], cols=2)


def get_phototype_keyboard():
    buttons = [
        "I — Всегда обгораю",
        "II — Часто обгораю",
        "III — Иногда обгораю, затем загораю",
        "IV — Редко обгораю",
        "V-VI — Смуглая, не обгораю"
    ]
    return make_keyboard(buttons, cols=1)


def get_barrier_state_keyboard():
    buttons = [
        "Сильная сухость и шелушение",
        "Частое жжение от косметики",
        "Стянутость после умывания",
        "Густой жирный блеск",
        "Кожа истонченная, «пергаментная»",
        "Нормальное, комфортное состояние"
    ]
    return make_keyboard_with_ready(buttons, cols=1)


def get_visual_markers_keyboard():
    buttons = [
        "Акне (воспаления)",
        "Комедоны (черные точки/бугорки)",
        "Постакне (пятна от прыщей)",
        "Пигментация",
        "Купероз (сосудистая сетка)",
        "Мелкие морщины",
        "Птоз (потеря овала)",
        "Ничего из перечисленного"
    ]
    return make_keyboard_with_ready(buttons, cols=1)


def get_sos_conditions_keyboard():
    buttons = [
        "Солнечный ожог (в последние 14 дней)",
        "Обострение дерматита или розацеа",
        "Аллергическая сыпь",
        "Ничего из перечисленного"
    ]
    return make_keyboard(buttons, cols=1)


def get_morning_face_keyboard():
    buttons = [
        "Отечное",
        "Тяжелое, «каменное»",
        "Помятое, несвежее",
        "Стянутое, сухое",
        "Нормальное, свежее"
    ]
    return make_keyboard(buttons, cols=1)


def get_tension_areas_keyboard():
    buttons = ["Лоб", "Челюсть, ВНЧС", "Скулы", "Вокруг глаз", "Шея, затылок", "Нигде"]
    return make_keyboard_with_ready(buttons, cols=1)


def get_jaw_tension_keyboard():
    return make_keyboard(["Левая", "Правая", "Одинаково"], cols=3)


def get_habits_keyboard():
    buttons = [
        "Сжимаю челюсти",
        "Подпираю лицо",
        "Щурюсь",
        "Телефон между ухом и плечом",
        "Сплю лицом в подушку",
        "Нет привычек"
    ]
    return make_keyboard_with_ready(buttons, cols=1)


def get_face_numbness_keyboard():
    return make_keyboard(["Да, часто", "Иногда", "Нет"], cols=3)


def get_contraindications_keyboard():
    buttons = [
        "Беременность/Лактация",
        "Прием изотретиноина",
        "Онкология",
        "Кардиостимулятор",
        "Нет ни одного из вышеперечисленного"
    ]
    return make_keyboard(buttons, cols=1)


def get_chronic_diseases_keyboard():
    buttons = [
        "Диабет",
        "Аутоиммунные",
        "Эпилепсия",
        "Гипертония",
        "Щитовидная железа",
        "ЖКТ",
        "Нет"
    ]
    return make_keyboard_with_ready(buttons, cols=1)


def get_medications_keyboard():
    buttons = [
        "Антикоагулянты",
        "Гормональные (КОК, ЗГТ)",
        "Антидепрессанты",
        "Антибиотики",
        "БАДы",
        "Нет"
    ]
    return make_keyboard_with_ready(buttons, cols=1)


def get_allergies_keyboard():
    buttons = [
        "Келоидные рубцы",
        "Витилиго",
        "Пищевая аллергия",
        "На металлы или косметику",
        "Нет"
    ]
    return make_keyboard_with_ready(buttons, cols=1)


def get_procedures_keyboard():
    return make_keyboard(["Не проходил(а)"], cols=1)


def get_home_care_keyboard():
    return make_keyboard(["Уход отсутствует"], cols=1)


def get_active_experience_keyboard():
    return make_keyboard(["Не пробовал(а)"], cols=1)


def get_success_criteria_keyboard():
    buttons = [
        "Визуальный: Ушла «серость», появился ровный тон, ткани стали плотнее.",
        "Тактильный: Кожа перестала «болеть», ушли стянутость и шелушения.",
        "Функциональный: Лицо больше не требует тонального крема.",
        "Эмоциональный: С удовольствием смотрю в зеркало по утрам без тревоги.",
        "Разрыв шаблона: Хочу увидеть реальную работу химии после десятков бесполезных баночек."
    ]
    return make_keyboard(buttons, cols=1)


def get_climate_change_keyboard():
    return make_keyboard(["Не планирую"], cols=1)


def get_source_keyboard():
    buttons = [
        "Instagram", "ВК", "Телеграмм", "Авито",
        "Поиск", "Рекомендация", "Эвамед", "Другое"
    ]
    return make_keyboard(buttons, cols=2)


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
        
        clean_selected = [item.strip() for item in selected if item.strip()]
        await state.update_data({field_name: ", ".join(clean_selected)})
        await state.set_state(next_state)
        
        if next_keyboard_func:
            await message.answer(next_question, reply_markup=next_keyboard_func())
        else:
            await message.answer(next_question, reply_markup=ReplyKeyboardRemove())
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
    
    if message.text and message.text.strip():
        if "," in message.text:
            new_options = [opt.strip() for opt in message.text.split(",") if opt.strip()]
            for opt in new_options:
                if opt not in selected and opt not in options_list:
                    selected.append(opt)
            await state.update_data({field_name: selected})
            await message.answer(
                f"✅ Добавлено: {', '.join(new_options)}\n"
                f"Всего выбрано: {len(selected)} вариантов.\n\n"
                "Выберите еще вариант или нажмите 'Готово' для завершения.",
                reply_markup=keyboard_func()
            )
        else:
            if message.text not in selected:
                selected.append(message.text)
                await state.update_data({field_name: selected})
                await message.answer(
                    f"✅ Добавлено: {message.text}\nВыбрано: {len(selected)} вариантов.\n\n"
                    "Выберите еще вариант или нажмите 'Готово' для завершения.",
                    reply_markup=keyboard_func()
                )
            else:
                await message.answer(
                    f"⚠️ Вы уже выбрали '{message.text}'. Выберите другой вариант или нажмите 'Готово'.",
                    reply_markup=keyboard_func()
                )
        return
    
    await message.answer(
        "Пожалуйста, выберите вариант из кнопок, введите свой вариант или нажмите 'Готово'.",
        reply_markup=keyboard_func()
    )


# ================== ОБРАБОТЧИК /START ==================
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} запустил бота")
    
    await message.answer_photo(
        photo=IMAGE_URL,
        caption=(
            "Привет. Я — Мария Мирославская.\n"
            "Здесь мы заканчиваем с хаосом в уходе. Только точная биохимия и доказательная космецевтика.\n\n"
            "Сейчас мы соберем твой анамнез. Этот алгоритм полностью заменяет мою очную консультацию, "
            "поэтому отвечай максимально честно. Именно на базе этих данных я лично соберу твой Skin Protokol.\n\n"
            "Готова выстроить правильную физиологию кожи?\n"
            "👇 Жми кнопку ниже."
        )
    )

    await state.set_state(Form.waiting_for_start)
    await message.answer(
        "⬇️ *Для начала заполнения анкеты нажми кнопку «СТАРТ»* ⬇️",
        parse_mode="Markdown",
        reply_markup=get_start_keyboard()
    )


@dp.message(StateFilter(Form.waiting_for_start), F.text == "▶️ СТАРТ")
async def process_start_button(message: types.Message, state: FSMContext):
    await state.set_state(Form.priorities)
    await message.answer(
        "📋 *ШАГ 1: ПЕРВИЧНЫЙ СБОР АНАМНЕЗА*\n\n"
        "Выберите до 3-х главных задач, которые необходимо решить:\n\n"
        "Нажмите на кнопку с задачей, чтобы добавить её в список.\n"
        "Когда выберете все задачи, нажмите 'Готово'.",
        parse_mode="Markdown",
        reply_markup=get_priorities_keyboard()
    )


# ================== ШАГ 1 ==================
@dp.message(StateFilter(Form.priorities))
async def process_priorities(message: types.Message, state: FSMContext):
    if 'priorities_list' not in await state.get_data():
        await state.update_data(priorities_list=[])
    
    data = await state.get_data()
    priorities_list = data.get('priorities_list', [])
    
    options_list = [
        "Морщины и потеря тонуса",
        "Тусклый цвет лица, пигментация",
        "Отечность, пастозность",
        "Расширенные поры, акне, блеск",
        "Купероз и краснота",
        "Сухость и поврежденный барьер"
    ]
    
    if message.text and message.text.lower() == "готово":
        if len(priorities_list) == 0:
            await message.answer(
                "⚠️ Вы не выбрали ни одной задачи. Выберите хотя бы одну:",
                reply_markup=get_priorities_keyboard()
            )
            return
        
        await state.update_data(priorities=", ".join(priorities_list))
        await state.set_state(Form.skin_type)
        await message.answer(
            "Какой генетический тип вашей кожи?",
            reply_markup=get_skin_type_keyboard()
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
            await state.set_state(Form.skin_type)
            await message.answer(
                "Какой генетический тип вашей кожи?",
                reply_markup=get_skin_type_keyboard()
            )
        return
    
    await message.answer(
        "Нажмите на кнопку с задачей или нажмите 'Готово'",
        reply_markup=get_priorities_keyboard()
    )


@dp.message(StateFilter(Form.skin_type))
async def process_skin_type(message: types.Message, state: FSMContext):
    await state.update_data(skin_type=message.text.strip())
    await state.set_state(Form.phototype)
    await message.answer(
        "Как ваша кожа реагирует на 30 минут пребывания на солнце без защиты?",
        reply_markup=get_phototype_keyboard()
    )


@dp.message(StateFilter(Form.phototype))
async def process_phototype(message: types.Message, state: FSMContext):
    await state.update_data(phototype=message.text.strip())
    await state.set_state(Form.barrier_state)
    await message.answer(
        "Что вы ТАКТИЛЬНО ощущаете на коже в последние месяцы? (Выберите несколько)\n\n"
        "Выберите варианты из кнопок. Когда закончите, нажмите 'Готово'.",
        reply_markup=get_barrier_state_keyboard()
    )


@dp.message(StateFilter(Form.barrier_state))
async def process_barrier_state(message: types.Message, state: FSMContext):
    await handle_multiple_choice(
        message, state,
        field_name="barrier_state",
        keyboard_func=get_barrier_state_keyboard,
        next_state=Form.visual_markers,
        next_question="Что вы ВИДИТЕ в зеркале (какие маркеры присутствуют)? (Выберите несколько)\n\nВыберите варианты из кнопок. Когда закончите, нажмите 'Готово'.",
        next_keyboard_func=get_visual_markers_keyboard
    )


@dp.message(StateFilter(Form.visual_markers))
async def process_visual_markers(message: types.Message, state: FSMContext):
    await handle_multiple_choice(
        message, state,
        field_name="visual_markers",
        keyboard_func=get_visual_markers_keyboard,
        next_state=Form.sos_conditions,
        next_question="Есть ли у вас прямо сейчас острые состояния, требующие срочной реабилитации?",
        next_keyboard_func=get_sos_conditions_keyboard
    )


@dp.message(StateFilter(Form.sos_conditions))
async def process_sos_conditions(message: types.Message, state: FSMContext):
    await state.update_data(sos_conditions=message.text.strip())
    await state.set_state(Form.morning_face)
    await message.answer(
        "📋 *ШАГ 2: ФУНКЦИОНАЛЬНЫЙ И МИОФАСЦИАЛЬНЫЙ ТЕСТ*\n\n"
        "Опишите привычное утреннее состояние вашего лица:",
        parse_mode="Markdown",
        reply_markup=get_morning_face_keyboard()
    )


# ================== ШАГ 2 ==================
@dp.message(StateFilter(Form.morning_face))
async def process_morning_face(message: types.Message, state: FSMContext):
    await state.update_data(morning_face=message.text.strip())
    await state.set_state(Form.tension_areas)
    await message.answer(
        "Где вы чаще всего ощущаете напряжение, даже в покое? (Выберите несколько)\n\n"
        "Выберите варианты из кнопок. Когда закончите, нажмите 'Готово'.",
        reply_markup=get_tension_areas_keyboard()
    )


@dp.message(StateFilter(Form.tension_areas))
async def process_tension_areas(message: types.Message, state: FSMContext):
    await handle_multiple_choice(
        message, state,
        field_name="tension_areas",
        keyboard_func=get_tension_areas_keyboard,
        next_state=Form.jaw_tension,
        next_question="Тест: Сожмите челюсти, положив пальцы на виски. Какая сторона ощущается более напряженной?",
        next_keyboard_func=get_jaw_tension_keyboard
    )


@dp.message(StateFilter(Form.jaw_tension))
async def process_jaw_tension(message: types.Message, state: FSMContext):
    await state.update_data(jaw_tension=message.text.strip())
    await state.set_state(Form.habits)
    await message.answer(
        "Отметьте привычки, которые замечаете за собой: (Выберите несколько)\n\n"
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
    await state.set_state(Form.contraindications)
    await message.answer(
        "📋 *ШАГ 3: КЛИНИЧЕСКИЙ СКРИНИНГ*\n\n"
        "Есть ли у вас следующие абсолютные противопоказания?",
        parse_mode="Markdown",
        reply_markup=get_contraindications_keyboard()
    )


# ================== ШАГ 3 ==================
@dp.message(StateFilter(Form.contraindications))
async def process_contraindications(message: types.Message, state: FSMContext):
    await state.update_data(contraindications=message.text.strip())
    
    has_contraindications = message.text.strip() != "Нет ни одного из вышеперечисленного"
    await state.update_data(has_contraindications=has_contraindications)
    
    await state.set_state(Form.chronic_diseases)
    await message.answer(
        "Есть ли у вас хронические заболевания? (Выберите несколько)\n\n"
        "Выберите варианты из кнопок. Когда закончите, нажмите 'Готово'.",
        reply_markup=get_chronic_diseases_keyboard()
    )


@dp.message(StateFilter(Form.chronic_diseases))
async def process_chronic_diseases(message: types.Message, state: FSMContext):
    await handle_multiple_choice(
        message, state,
        field_name="chronic_diseases",
        keyboard_func=get_chronic_diseases_keyboard,
        next_state=Form.medications,
        next_question="Принимаете ли вы в настоящее время: (Выберите несколько)\n\nВыберите варианты из кнопок. Когда закончите, нажмите 'Готово'.",
        next_keyboard_func=get_medications_keyboard
    )


@dp.message(StateFilter(Form.medications))
async def process_medications(message: types.Message, state: FSMContext):
    await handle_multiple_choice(
        message, state,
        field_name="medications",
        keyboard_func=get_medications_keyboard,
        next_state=Form.allergies,
        next_question="Отмечалась ли у вас склонность к следующим реакциям? (Выберите несколько)\n\nВыберите варианты из кнопок. Когда закончите, нажмите 'Готово'.",
        next_keyboard_func=get_allergies_keyboard
    )


@dp.message(StateFilter(Form.allergies))
async def process_allergies(message: types.Message, state: FSMContext):
    await handle_multiple_choice(
        message, state,
        field_name="allergies",
        keyboard_func=get_allergies_keyboard,
        next_state=Form.procedures,
        next_question="📋 *ШАГ 4: АУДИТ ТЕКУЩЕГО УХОДА*\n\n"
        "Какие косметологические процедуры вы проходили за последние 12 месяцев? "
        "(Чистки, пилинги, инъекции, лазер, нити).\n\n"
        "Напишите подробно или нажмите кнопку:",
        next_keyboard_func=get_procedures_keyboard
    )


# ================== ШАГ 4 ==================
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
        "Сыворотки: ...\n"
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
    
    await state.set_state(Form.active_experience)
    await message.answer(
        "Пробовали ли вы вводить в уход активные компоненты (кислоты, ретинол, витамин С)?\n\n"
        "Если да, какой была реакция кожи?\n\n"
        "Напишите подробно или нажмите кнопку:",
        reply_markup=get_active_experience_keyboard()
    )


@dp.message(StateFilter(Form.active_experience))
async def process_active_experience(message: types.Message, state: FSMContext):
    if message.text == "Не пробовал(а)":
        await state.update_data(active_experience="Не пробовал(а)")
    else:
        await state.update_data(active_experience=message.text.strip())
    
    await state.set_state(Form.success_criteria)
    await message.answer(
        "📋 *ШАГ 5: РЕГИСТРАЦИЯ ДАННЫХ И ОФОРМЛЕНИЕ SKIN PROTOKOL*\n\n"
        "Сформулируйте главный критерий успеха спустя первый месяц использования MIROSLAVSKAYA Skin Protokol:\n\n"
        "Выберите один вариант:",
        parse_mode="Markdown",
        reply_markup=get_success_criteria_keyboard()
    )


# ================== ШАГ 5 ==================
@dp.message(StateFilter(Form.success_criteria))
async def process_success_criteria(message: types.Message, state: FSMContext):
    await state.update_data(success_criteria=message.text.strip())
    await state.set_state(Form.full_name)
    await message.answer(
        "Анамнез собран. Алгоритм готов сформировать персональный Skin Protokol.\n\n"
        "Оставьте данные для закрепления результатов за вами и связи со специалистом.\n\n"
        "Введите ваши *Фамилию, Имя и Отчество*:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(StateFilter(Form.full_name))
async def process_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await state.set_state(Form.phone)
    await message.answer(
        "Введите *контактный телефон* (мессенджер) для связи:",
        parse_mode="Markdown"
    )


@dp.message(StateFilter(Form.phone))
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(Form.city)
    await message.answer(
        "Из какого Вы города? (Важно для понимания жесткости воды и климата)"
    )


@dp.message(StateFilter(Form.city))
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    await state.set_state(Form.climate_change)
    await message.answer(
        "Планируются ли у вас поездки в другой климат или активный отдых на солнце в ближайший месяц?\n\n"
        "Напишите подробно или нажмите кнопку:",
        reply_markup=get_climate_change_keyboard()
    )


@dp.message(StateFilter(Form.climate_change))
async def process_climate_change(message: types.Message, state: FSMContext):
    if message.text == "Не планирую":
        await state.update_data(climate_change="Не планирую")
    else:
        await state.update_data(climate_change=message.text.strip())
    
    await state.set_state(Form.birth_date)
    await message.answer(
        "Введите свою *дату рождения* в формате *ДД.ММ.ГГГГ*:\n"
        "(например, 25.12.1990)",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
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


# ================== ОТПРАВКА ОТЧЁТА В КОНСОЛЬ ==================
@dp.message(StateFilter(Form.source))
async def process_source(message: types.Message, state: FSMContext):
    await state.update_data(source=message.text.strip())
    
    data = await state.get_data()
    
    report = (
        "📋 ПОЛНАЯ АНКЕТА КЛИЕНТА\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "ШАГ 1: ПЕРВИЧНЫЙ СБОР АНАМНЕЗА\n"
        f"Приоритеты: {data.get('priorities', '—')}\n"
        f"Тип кожи: {data.get('skin_type', '—')}\n"
        f"Фототип: {data.get('phototype', '—')}\n"
        f"Состояние барьера: {data.get('barrier_state', '—')}\n"
        f"Визуальные маркеры: {data.get('visual_markers', '—')}\n"
        f"SOS состояния: {data.get('sos_conditions', '—')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "ШАГ 2: ФУНКЦИОНАЛЬНЫЙ И МИОФАСЦИАЛЬНЫЙ ТЕСТ\n"
        f"Утреннее состояние: {data.get('morning_face', '—')}\n"
        f"Зоны напряжения: {data.get('tension_areas', '—')}\n"
        f"Напряжение челюстей: {data.get('jaw_tension', '—')}\n"
        f"Привычки: {data.get('habits', '—')}\n"
        f"Онемение лица: {data.get('face_numbness', '—')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "ШАГ 3: КЛИНИЧЕСКИЙ СКРИНИНГ\n"
        f"Противопоказания: {data.get('contraindications', '—')}\n"
        f"Хронические заболевания: {data.get('chronic_diseases', '—')}\n"
        f"Препараты: {data.get('medications', '—')}\n"
        f"Аллергии: {data.get('allergies', '—')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "ШАГ 4: АУДИТ ТЕКУЩЕГО УХОДА\n"
        f"Процедуры: {data.get('procedures', '—')}\n"
        f"Домашний уход: {data.get('home_care', '—')}\n"
        f"Опыт с активами: {data.get('active_experience', '—')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "ШАГ 5: РЕГИСТРАЦИЯ ДАННЫХ И ОФОРМЛЕНИЕ SKIN PROTOKOL\n"
        f"Критерий успеха: {data.get('success_criteria', '—')}\n"
        f"ФИО: {data.get('full_name', '—')}\n"
        f"Телефон: {data.get('phone', '—')}\n"
        f"Город: {data.get('city', '—')}\n"
        f"Смена климата: {data.get('climate_change', '—')}\n"
        f"Дата рождения: {data.get('birth_date', '—')}\n"
        f"Откуда узнали: {data.get('source', '—')}\n\n"
        f"👤 Username: @{message.from_user.username if message.from_user.username else 'Не указан'}"
    )
    
    if data.get('has_contraindications', False):
        report += "\n\n⚠️ ВНИМАНИЕ: У КЛИЕНТА ЕСТЬ ПРОТИВОПОКАЗАНИЯ!"
    
    # ======= ВЫВОД В КОНСОЛЬ =======
    print("\n" + "="*70)
    print("📋 НОВАЯ АНКЕТА")
    print("="*70)
    print(report)
    print("="*70 + "\n")
    
    # ======= ОТПРАВКА В TELEGRAM (владельцу) =======
    try:
        if len(report) > 4096:
            await bot.send_message(
                chat_id=OWNER_ID,
                text=report[:4000] + "\n\n... (текст обрезан)",
                parse_mode=None
            )
            logger.warning(f"Отчёт обрезан, длина {len(report)} символов")
        else:
            await bot.send_message(chat_id=OWNER_ID, text=report, parse_mode=None)
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
        "Анамнез успешно оцифрован и передан в работу. 🧬\n\n"
        "Я сохранил твои данные и передал их лично Марии. Сейчас мы анализируем биохимию твоих ответов, чтобы собрать точную формулу твоего Skin Protokol.\n\n"
        "⏱ Время обработки алгоритма: до 24 часов.\n\n"
        "Мы свяжемся с тобой по указанному номеру, чтобы презентовать состав твоей персональной капсулы космецевтики.\n\n"
        "До связи🤍",
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
