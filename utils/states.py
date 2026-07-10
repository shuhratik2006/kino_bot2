from aiogram.fsm.state import State, StatesGroup


class DeleteMovie(StatesGroup):
    waiting_for_code = State()


class Broadcast(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirm = State()


class FSubAdd(StatesGroup):
    waiting_for_channel = State()


class PremiumManage(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_days = State()


class AdminManage(StatesGroup):
    waiting_for_user_id = State()
