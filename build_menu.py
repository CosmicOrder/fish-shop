from typing import Union, List
from telegram import InlineKeyboardButton


def built_menu(
        buttons: List[InlineKeyboardButton],
        n_cols: int,
        footer_buttons: Union[InlineKeyboardButton, List[InlineKeyboardButton]]=None,
):
    menu = [buttons[start_slice:start_slice + n_cols] for start_slice in range(0, len(buttons), n_cols)]
    if footer_buttons:
        menu.append(footer_buttons if isinstance(footer_buttons, list) else [
            footer_buttons])
    return menu
