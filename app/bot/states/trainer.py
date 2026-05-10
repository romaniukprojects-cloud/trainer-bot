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


class QuickMarkStates(StatesGroup):
    disambiguating = State()
    confirming = State()


class SessionsByDateStates(StatesGroup):
    enter_date = State()


class PaymentDetailsStates(StatesGroup):
    entering = State()
