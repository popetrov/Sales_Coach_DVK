import asyncio
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from openai import OpenAI

from prompts import (
    COMMON_SALES_RULES,
    BAD_MANAGER_PHRASES,
    CLIENT_BEHAVIOR_RULES,
    BG_PRODUCT_CONTEXT,
    BG_STRONG_QUESTIONS,
    CREDIT_PRODUCT_CONTEXT,
    CREDIT_STRONG_QUESTIONS,
    TRAINING_MODE_RULES,
    EVALUATION_RULES,
    BG_CLIENT_EYES_CONTEXT,
    BG_CLIENT_PAIN_REACTIONS,
    BG_CLIENT_STYLE_REACTIONS,
    BG_CLIENT_IDEAL_PHRASES,
    BG_CLIENT_SITUATIONS,
    BG_CLIENT_EVALUATION_RULES,
    BG_CLIENT_ALGORITHM,
    CLIENT_ARCHETYPES,
    ARCHETYPE_BEHAVIOR_MATRIX,
)


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = OpenAI(api_key=OPENAI_API_KEY)

user_data = {}


SCENARIO_STEPS = [
    {"key": "product", "question": "Выбери продукт для тренировки:", "options": ["БГ", "Кредит"]},
    {"key": "difficulty", "question": "Выбери уровень сложности:", "options": ["Лёгкий", "Средний", "Сложный"]},
    {
        "key": "client_type",
        "question": "Выбери тип клиента:",
        "options": [
            "Холодный клиент",
            "Действующий клиент",
            "Бывший клиент",
            "Клиент конкурента",
            "Клиент с проблемной историей",
            "Крупный контрактник",
        ],
    },
    
    {
        "key": "client_archetype",
        "question": "Выбери архетип клиента:",
        "options": [
            "Жёсткий собственник",
            "Уставший тендерщик",
            "Токсичный бухгалтер",
            "Клиент после отказов",
            "Клиент с короной",
            "Клиент в панике перед сроком",
            "Всё знаю сам",
            "Скиньте на почту",
            "У нас свой агент",
            "Денег нет, контракт горит",
        ],
    },

    {"key": "company", "question": "Введи название компании:", "options": None},
    {
        "key": "role",
        "question": "Выбери роль собеседника:",
        "options": [
            "Собственник",
            "Директор",
            "Финансовый директор",
            "Бухгалтер",
            "Тендерный специалист",
            "Жена-директор",
            "Муж-учредитель",
            "Другое",
        ],
    },
    {"key": "niche", "question": "Введи нишу / деятельность компании:", "options": None},
    {"key": "revenue", "question": "Введи примерную выручку компании:", "options": None},
    {
        "key": "financial_situation",
        "question": "Опиши финансовую ситуацию клиента: прибыль, убытки, просрочки, суды, ФНС, кредиты, гарантии и т.д.",
        "options": None,
    },
    {
        "key": "contract_situation",
        "question": "Опиши контрактную ситуацию: 44-ФЗ, 223-ФЗ, коммерческие контракты, Россети, Транснефть, стройка, крупные заказчики и т.д.",
        "options": None,
    },
    {
        "key": "current_channels",
        "question": "Что клиент уже использует?",
        "options": [
            "Банк напрямую",
            "Свой агент / брокер",
            "Несколько каналов",
            "Кредитная линия",
            "Только один банк",
            "Неизвестно",
            "Ничего не использует",
        ],
    },
    {
        "key": "objection",
        "question": "Выбери главное возражение клиента:",
        "options": [
            "Уже есть агент",
            "Уже есть банк",
            "Всё устраивает",
            "Не доверяю новым",
            "Пришлите информацию",
            "Давайте потом",
            "Не хочу отправлять документы",
            "Банки уже отказали",
            "Не хочу тратить время",
        ],
    },
    {
        "key": "training_goal",
        "question": "Выбери цель тренировки:",
        "options": [
            "Получить вводные",
            "Выйти на созвон",
            "Получить документы",
            "Продать резервный канал",
            "Забрать БГ в постоянную работу",
            "Продать кредит",
            "Вскрыть потребность",
            "Отработать отказ",
        ],
    },
    {"key": "game_mode", "question": "Выбери режим игры:", "options": ["Боевой режим", "Учебный режим"]},
]


def make_keyboard(options):
    if not options:
        return ReplyKeyboardRemove()

    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=option)] for option in options],
        resize_keyboard=True,
    )


def get_current_step(user_id):
    index = user_data[user_id].get("step_index", 0)
    if index >= len(SCENARIO_STEPS):
        return None
    return SCENARIO_STEPS[index]


def get_product_prompt(data):

    if data.get("product") == "БГ":

        return f"""
{BG_PRODUCT_CONTEXT}

{BG_STRONG_QUESTIONS}

{BG_CLIENT_EYES_CONTEXT}

{BG_CLIENT_PAIN_REACTIONS}

{BG_CLIENT_STYLE_REACTIONS}

{BG_CLIENT_IDEAL_PHRASES}

{BG_CLIENT_SITUATIONS}

{BG_CLIENT_EVALUATION_RULES}

{BG_CLIENT_ALGORITHM}
"""

    return f"""
{CREDIT_PRODUCT_CONTEXT}

{CREDIT_STRONG_QUESTIONS}
"""


def format_intro(data):
    mode_text = (
        "Боевой режим: подсказок во время игры не будет. Разбор только после финала."
        if data.get("game_mode") == "Боевой режим"
        else "Учебный режим: после каждого сообщения ты будешь получать подсказку тренера, куда вести диалог."
    )

    return f"""
🎭 Я — клиент

Компания: {data.get("company")}
Тип клиента: {data.get("client_type")}
Архетип клиента: {data.get("client_archetype")}
Роль собеседника: {data.get("role")}
Ниша: {data.get("niche")}
Выручка: {data.get("revenue")}

Финансовая ситуация:
{data.get("financial_situation")}

Контрактная ситуация:
{data.get("contract_situation")}

Что уже использует:
{data.get("current_channels")}

Главное возражение:
{data.get("objection")}

Уровень сложности:
{data.get("difficulty")}

Режим:
{data.get("game_mode")}
{mode_text}

🎯 Задача менеджера:
{data.get("training_goal")}

Правило:
Не продавай в лоб. Сначала пойми контекст, попади в боль, задай точный вопрос и выведи клиента на безопасный следующий шаг.

🎭 Поехали.

Жду первое сообщение менеджера.
"""


def build_context_rules(data):
    return f"""
ОБЯЗАТЕЛЬНО играй именно этого клиента, а не абстрактного.

Вводные клиента:
- Компания: {data.get("company")}
- Ниша: {data.get("niche")}
- Выручка: {data.get("revenue")}
- Финансовая ситуация: {data.get("financial_situation")}
- Контрактная ситуация: {data.get("contract_situation")}
- Что уже использует: {data.get("current_channels")}
- Главное возражение: {data.get("objection")}
- Роль собеседника: {data.get("role")}
- Архетип клиента: {data.get("client_archetype")}

Как учитывать вводные:
- Если есть просрочки, суды, отказы банков, слабая прибыль или падение выручки — клиент осторожный, не хочет зря отправлять документы и боится очередного отказа.
- Если выручка высокая — клиент не реагирует на общие обещания и требует конкретики.
- Если есть банк, агент или несколько каналов — клиент не видит смысла менять схему без понятной выгоды.
- Если клиент работает с тендерами — ему важны сроки, лимиты, макет гарантии, подтверждение, план Б и отсутствие срыва контракта.
- Если цель менеджера “Получить документы” — клиент не должен отдавать документы рано. Сначала он должен увидеть смысл и безопасность.
- Если цель “Получить вводные” — клиент может дать минимум данных, только если менеджер задал точный вопрос.
- Если цель “Выйти на созвон” — клиент согласится только если увидит конкретную пользу созвона.
"""


async def gpt_training_hint(data, manager_message, history):
    prompt = f"""
Ты — тренер по продажам ДВК Финанс в учебном режиме.

Твоя задача:
1. Коротко оценить сообщение менеджера.
2. Сказать, что в нём хорошо.
3. Сказать, что ослабляет позицию.
4. Дать лучший следующий ход.
5. Дать пример фразы, которую менеджер мог бы использовать дальше.

Не пиши длинную лекцию. Максимум 8-10 строк.

{COMMON_SALES_RULES}

{BAD_MANAGER_PHRASES}

{TRAINING_MODE_RULES}
{CLIENT_ARCHETYPES}
{ARCHETYPE_BEHAVIOR_MATRIX}

{get_product_prompt(data)}

{build_context_rules(data)}

Продукт: {data.get("product")}
Цель тренировки: {data.get("training_goal")}
Сложность клиента: {data.get("difficulty")}

Диалог:
{history}

Последнее сообщение менеджера:
{manager_message}

Формат ответа:

🧠 Подсказка тренера:
...
Лучший следующий ход:
...
Фраза:
"..."

Архетип клиента обязателен к отыгрышу.
Если выбран архетип, клиент должен говорить, сопротивляться и принимать решения в стиле этого архетипа.
Нельзя игнорировать архетип.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "system", "content": prompt}],
    )

    return response.choices[0].message.content


async def gpt_client_reply(data, manager_message, history):
    difficulty_rules = {
        "Лёгкий": """
Клиент отвечает подробнее, даёт шанс, не сливает сразу.
Если менеджер попал в смысл — можно дать вводные.
Но даже лёгкий клиент не должен соглашаться без причины.
""",
        "Средний": """
Клиент отвечает коротко, сомневается, требует конкретики.
Если менеджер говорит общими словами — сопротивляется.
Даёт 2–3 шанса, потом начинает закрывать разговор.
""",
        "Сложный": """
Клиент жёсткий, короткий, быстро сливает.
Не верит словам. Требует конкретики за 1–2 сообщения.
Если менеджер говорит воду — отказывает.
Если менеджер рано просит документы — резко сопротивляется.
""",
    }

    prompt = f"""
Ты играешь роль клиента в тренировке продаж для менеджера ДВК Финанс.

ВАЖНО:
- Ты клиент, а не тренер.
- Не объясняй ошибки.
- Не подсказывай.
- Не соглашайся легко.
- Отвечай реалистично, коротко и по-человечески.
- Не раскрывай все вводные без причины.
- Всегда держи контекст компании.
- Всегда держи продуктовую кухню.
- Если менеджер говорит общими фразами — сомневайся, дави или отказывай.
- Если менеджер задал точный вопрос и попал в боль — дай немного конкретики.
- Не начинай продавать сам себя менеджеру.
- Не веди менеджера за руку в боевом режиме.

{COMMON_SALES_RULES}

{BAD_MANAGER_PHRASES}

{CLIENT_BEHAVIOR_RULES}
{CLIENT_ARCHETYPES}
{ARCHETYPE_BEHAVIOR_MATRIX}

{get_product_prompt(data)}

{build_context_rules(data)}

Сценарий:
Продукт: {data.get("product")}
Тип клиента: {data.get("client_type")}
Сложность: {data.get("difficulty")}
Цель менеджера: {data.get("training_goal")}

Поведение по сложности:
{difficulty_rules.get(data.get("difficulty"), "")}

История диалога:
{history}

Последнее сообщение менеджера:
{manager_message}

Ответь только как клиент. 1-3 короткие фразы.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "system", "content": prompt}],
    )

    return response.choices[0].message.content


async def gpt_judge(data, history):
    prompt = f"""
Ты строгий тренер по продажам ДВК Финанс.

Твоя задача — определить, надо продолжать игру или завершить её.

Возможные статусы:
CONTINUE — диалог можно продолжать.
SUCCESS — клиент согласился на следующий шаг: вводные, созвон, документы, тестовая БГ, кредит, следующий контакт.
REFUSAL — клиент явно отказал и дальше не хочет общаться.
LOST — менеджер потерял диалог: вода, круги, не отвечает на запрос клиента, рано просит документы, не ведёт к шагу.

Правила:
- Не завершай слишком рано.
- В учебном режиме будь мягче: дай менеджеру больше шансов.
- В боевом режиме оцени строже.
- На лёгкой сложности дай больше шансов.
- На сложной сложности завершай быстрее, если менеджер говорит воду.
- Если клиент согласился на следующий шаг — SUCCESS.
- Если клиент жёстко отказал — REFUSAL.
- Если менеджер 2 раза подряд не отвечает на смысл клиента — LOST.

{COMMON_SALES_RULES}

{CLIENT_BEHAVIOR_RULES}
{CLIENT_ARCHETYPES}
{ARCHETYPE_BEHAVIOR_MATRIX}

{get_product_prompt(data)}

{build_context_rules(data)}

Режим: {data.get("game_mode")}
Продукт: {data.get("product")}
Цель тренировки: {data.get("training_goal")}
Сложность: {data.get("difficulty")}
Возражение: {data.get("objection")}

Диалог:
{history}

Ответь строго в формате:
STATUS: CONTINUE / SUCCESS / REFUSAL / LOST
REASON: короткая причина
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "system", "content": prompt}],
    )

    return response.choices[0].message.content


async def gpt_feedback(data, history, final_status):
    prompt = f"""
Ты тренер по продажам ДВК Финанс.

Дай подробный, но понятный разбор игры.

{EVALUATION_RULES}

{COMMON_SALES_RULES}

{BAD_MANAGER_PHRASES}
{CLIENT_ARCHETYPES}
{ARCHETYPE_BEHAVIOR_MATRIX}

{get_product_prompt(data)}

{build_context_rules(data)}

Финал игры: {final_status}

Сценарий:
Продукт: {data.get("product")}
Компания: {data.get("company")}
Тип клиента: {data.get("client_type")}
Роль: {data.get("role")}
Ниша: {data.get("niche")}
Выручка: {data.get("revenue")}
Финансовая ситуация: {data.get("financial_situation")}
Контрактная ситуация: {data.get("contract_situation")}
Что уже использует: {data.get("current_channels")}
Возражение: {data.get("objection")}
Цель: {data.get("training_goal")}
Сложность: {data.get("difficulty")}
Режим: {data.get("game_mode")}

Диалог:
{history}

Формат ответа:

🏁 Итог:
Оценка: X/10

✅ Что менеджер сделал хорошо:

❌ Главная ошибка:

⚠️ Какие фразы ослабили позицию:

💪 Какие фразы сработали:

🔁 Как надо было ответить лучше:

⭐ Идеальный вариант ответа:

🧠 Главный урок:

🎯 Что тренировать дальше:
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "system", "content": prompt}],
    )

    return response.choices[0].message.content


def extract_status(judge_text):
    upper = judge_text.upper()

    if "SUCCESS" in upper:
        return "SUCCESS"
    if "REFUSAL" in upper:
        return "REFUSAL"
    if "LOST" in upper:
        return "LOST"

    return "CONTINUE"


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id

    user_data[user_id] = {
        "step_index": 0,
        "in_game": False,
        "history": "",
    }

    step = get_current_step(user_id)

    await message.answer(
        step["question"],
        reply_markup=make_keyboard(step["options"]),
    )


@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text

    if user_id not in user_data:
        user_data[user_id] = {
            "step_index": 0,
            "in_game": False,
            "history": "",
        }

    step = get_current_step(user_id)

    if step is None:
        if not user_data[user_id].get("in_game"):
            await message.answer("Игра завершена. Чтобы начать новую, введи /start")
            return

        user_data[user_id]["history"] += f"\nМенеджер: {text}"

        if user_data[user_id].get("game_mode") == "Учебный режим":
            hint = await gpt_training_hint(
                user_data[user_id],
                text,
                user_data[user_id]["history"],
            )
            await message.answer(hint)

        judge_before = await gpt_judge(user_data[user_id], user_data[user_id]["history"])
        status_before = extract_status(judge_before)

        if status_before != "CONTINUE":
            feedback = await gpt_feedback(
                user_data[user_id],
                user_data[user_id]["history"],
                status_before,
            )

            await message.answer("🏁 Диалог завершён")
            await message.answer(judge_before)
            await message.answer(feedback)
            await message.answer("Чтобы сыграть ещё раз, введи /start")

            user_data[user_id]["in_game"] = False
            return

        client_answer = await gpt_client_reply(
            user_data[user_id],
            text,
            user_data[user_id]["history"],
        )

        user_data[user_id]["history"] += f"\nКлиент: {client_answer}"

        await message.answer(f"🎭 Клиент:\n{client_answer}")

        judge_after = await gpt_judge(user_data[user_id], user_data[user_id]["history"])
        status_after = extract_status(judge_after)

        if status_after != "CONTINUE":
            feedback = await gpt_feedback(
                user_data[user_id],
                user_data[user_id]["history"],
                status_after,
            )

            await message.answer("🏁 Диалог завершён")
            await message.answer(judge_after)
            await message.answer(feedback)
            await message.answer("Чтобы сыграть ещё раз, введи /start")

            user_data[user_id]["in_game"] = False

        return

    key = step["key"]
    options = step["options"]

    if options and text not in options:
        await message.answer(
            "Выбери вариант кнопками 👇",
            reply_markup=make_keyboard(options),
        )
        return

    user_data[user_id][key] = text
    user_data[user_id]["step_index"] += 1

    next_step = get_current_step(user_id)

    if next_step is None:
        user_data[user_id]["in_game"] = True
        user_data[user_id]["history"] = ""

        await message.answer(
            format_intro(user_data[user_id]),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await message.answer(
        next_step["question"],
        reply_markup=make_keyboard(next_step["options"]),
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())