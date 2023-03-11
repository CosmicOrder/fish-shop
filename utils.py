def built_product_list(
        buttons,
        n_cols,
):
    product_list = [buttons[i:i + n_cols] for i in
                    range(0, len(buttons), n_cols)]
    return product_list