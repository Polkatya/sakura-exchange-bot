from aiogram.fsm.state import State, StatesGroup


class CreateTrade(StatesGroup):
    offer = State()
    videos = State()
    want = State()


class EditTrade(StatesGroup):
    offer = State()
    want = State()
    videos = State()


class Exchange(StatesGroup):
    videos = State()


class Comment(StatesGroup):
    text = State()


class Report(StatesGroup):
    text = State()
