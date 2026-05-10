from aiogram.fsm.state import State, StatesGroup


class AddClientStates(StatesGroup):
    name = State()
    phone = State()
    aliases = State()


class RegisterPaymentStates(StatesGroup):
    select_client = State()
    enter_amount = State()
    choose_date = State()
    enter_date = State()


class MarkSessionStates(StatesGroup):
    marking = State()
    choosing_date = State()
    enter_date = State()


class QuickMarkStates(StatesGroup):
    disambiguating = State()
    confirming = State()
    choosing_date = State()
    enter_date = State()


class SessionsByDateStates(StatesGroup):
    choosing = State()
    enter_date = State()


class PaymentDetailsStates(StatesGroup):
    entering = State()


class ScheduleStates(StatesGroup):
    select_client = State()
    viewing = State()
    add_weekday = State()
    add_time = State()
    remove_slot = State()


class CancelTrainingStates(StatesGroup):
    choosing_date = State()
    enter_date = State()
    confirming = State()
