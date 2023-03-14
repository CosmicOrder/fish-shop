def built_menu(
        buttons,
        n_cols,
        footer_buttons=None,
):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if footer_buttons:
        menu.append(footer_buttons if isinstance(footer_buttons, list) else [
            footer_buttons])
    return menu
