from aiogram import Router, types
from aiogram.types import ForceReply, InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.admin_keyboards import get_admin_assortment_keyboard, admin_menu_reply
from state import admin_ids, admin_states, assortment, send_or_edit

router = Router(name="admin_assortment")



@router.callback_query(lambda c: c.data == "admin_add_product")
async def admin_add_product(callback: types.CallbackQuery):
    admin_states[callback.from_user.id] = {
        "state": "adding_product",
        "step": "name",
        "data": {"flavors": []}
    }
    await send_or_edit(callback.bot, callback.message.chat.id, callback.from_user.id,
                       "Введите название продукта:",
                       reply_markup=ForceReply())
    await callback.answer()


@router.callback_query(lambda c: c.data in ["flavor_add_more", "flavor_save"])
async def flavor_input_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in admin_states or admin_states[user_id].get("state") != "adding_product":
        await callback.answer("Нет активного процесса добавления продукта.", show_alert=True)
        return
    if callback.data == "flavor_add_more":
        await send_or_edit(callback.bot, callback.message.chat.id, user_id,
                           "Введите следующий вкус продукта:",
                           reply_markup=ForceReply())
        await callback.answer()
    elif callback.data == "flavor_save":
        data = admin_states[user_id]["data"]
        new_id = str(max([int(k) for k in assortment.keys()] + [0]) + 1)
        assortment[new_id] = {
            "name": data.get("name"),
            "base_price": data.get("price"),
            "flavors": data.get("flavors", [])
        }
        await send_or_edit(callback.bot, callback.message.chat.id, user_id,
                           f"Продукт добавлен: {new_id}. {data.get('name')} ({data.get('price')}₽)\n"
                           f"Вкусы: {', '.join(data.get('flavors', [])) if data.get('flavors') else 'нет'}",
                           reply_markup=admin_menu_reply)
        admin_states.pop(user_id, None)
        await send_or_edit(callback.bot, callback.message.chat.id, user_id,
                           "Обновлённый ассортимент:",
                           reply_markup=get_admin_assortment_keyboard())
        await callback.answer()


@router.callback_query(lambda c: c.data.startswith("admin_product_"))
async def admin_product_options(callback: types.CallbackQuery):
    product_id = callback.data.split("_")[-1]
    product = assortment.get(product_id)
    if product:
        text = f"Продукт {product_id}: {product['name']} ({product['base_price']}₽)"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Редактировать", callback_data=f"admin_edit_product_{product_id}"),
                InlineKeyboardButton(text="Редактировать вкусы", callback_data=f"admin_edit_flavors_{product_id}")
            ],
            [
                InlineKeyboardButton(text="Удалить", callback_data=f"admin_del_{product_id}")
            ]
        ])
        await send_or_edit(callback.bot, callback.message.chat.id, callback.from_user.id, text, reply_markup=kb)
    else:
        await send_or_edit(callback.bot, callback.message.chat.id, callback.from_user.id, "Продукт не найден.")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("admin_edit_product_"))
async def admin_edit_product(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    product_id = str(callback.data).split("_")[-1]

    if str(user_id) not in admin_ids:
        await callback.answer("Доступ запрещен!")
        return
    if product_id not in assortment:
        await callback.answer("Продукт не найден!")
        return
    old_product = assortment[product_id]
    admin_states[user_id] = {
        "state": "editing_product",
        "product_id": product_id,
        "step": "name_choice",
        "data": {
            "old_name": old_product.get("name"),
            "old_price": old_product.get("base_price")
        }
    }
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить название", callback_data="admin_edit_name_yes"),
         InlineKeyboardButton(text="Оставить текущее", callback_data="admin_edit_name_no")]
    ])
    await send_or_edit(callback.bot,
        callback.message.chat.id,
        user_id,
        f"Редактирование продукта {product_id}\nТекущее название: {old_product.get('name')}\nХотите изменить название?",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(lambda c: c.data in ["admin_edit_name_yes", "admin_edit_name_no"])
async def handle_edit_product_name(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in admin_states or admin_states[user_id].get("state") != "editing_product":
        await callback.answer("Нет активного процесса редактирования продукта.", show_alert=True)
        return
    state_info = admin_states[user_id]
    old_name = state_info["data"]["old_name"]
    if callback.data == "admin_edit_name_yes":
        state_info["step"] = "name_input"
        await send_or_edit(callback.bot,
            callback.message.chat.id,
            user_id,
            f"Введите новое название продукта (текущее: {old_name}):",
            reply_markup=ForceReply()
        )
    else:
        state_info["data"]["new_name"] = old_name
        state_info["step"] = "price_choice"
        old_price = state_info["data"]["old_price"]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить цену", callback_data="admin_edit_price_yes"),
             InlineKeyboardButton(text="Оставить без изменений", callback_data="admin_edit_price_no")]
        ])
        await send_or_edit(callback.bot,
            callback.message.chat.id,
            user_id,
            f"Текущая цена: {old_price}₽\nХотите изменить цену?",
            reply_markup=kb
        )
    await callback.answer()


@router.callback_query(lambda c: c.data in ["admin_edit_price_yes", "admin_edit_price_no"])
async def handle_edit_product_price(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in admin_states or admin_states[user_id].get("state") != "editing_product":
        await callback.answer("Нет активного процесса редактирования продукта.", show_alert=True)
        return
    state_info = admin_states[user_id]
    old_price = state_info["data"]["old_price"]
    if callback.data == "admin_edit_price_yes":
        state_info["step"] = "price_input"
        await send_or_edit(callback.bot,
            callback.message.chat.id,
            user_id,
            f"Введите новую цену продукта (текущая: {old_price}₽):",
            reply_markup=ForceReply()
        )
    else:
        state_info["data"]["new_price"] = old_price
        prod_id = state_info.get("product_id")
        new_name = state_info["data"].get("new_name", state_info["data"]["old_name"])
        new_price = state_info["data"]["new_price"]
        assortment[prod_id].update({"name": new_name, "base_price": new_price})
        await send_or_edit(callback.bot,
            callback.message.chat.id,
            user_id,
            f"✅ Продукт обновлен!\nID: {prod_id}\nНазвание: {new_name}\nЦена: {new_price}₽",
            reply_markup=get_admin_assortment_keyboard()
        )
        admin_states.pop(user_id, None)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("admin_edit_flavors_"))
async def admin_edit_product_flavors(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    product_id = callback.data.split("_")[-1]
    if product_id not in assortment:
        await callback.answer("Продукт не найден!", show_alert=True)
        return
    admin_states[user_id] = {
        "state": "editing_product_flavors",
        "product_id": product_id
    }
    await send_or_edit(callback.bot, callback.message.chat.id, user_id,
                       f"Введите новые вкусы для продукта {product_id} через запятую:",
                       reply_markup=ForceReply())
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("admin_del_"))
async def admin_del_product(callback: types.CallbackQuery):
    product_id = callback.data.split("_")[-1]
    product = assortment.get(product_id)
    if not product:
        await send_or_edit(callback.bot, callback.message.chat.id, callback.from_user.id,
                           "Продукт не найден.",
                           reply_markup=get_admin_assortment_keyboard())
        await callback.answer()
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить удаление", callback_data=f"admin_confirm_del_{product_id}")],
        [InlineKeyboardButton(text="Отмена", callback_data="admin_cancel_del")]
    ])
    await send_or_edit(callback.bot, callback.message.chat.id, callback.from_user.id,
                       f"Вы уверены, что хотите удалить продукт {product_id}: {product['name']} ({product['base_price']}₽)?",
                       reply_markup=kb)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("admin_confirm_del_"))
async def admin_confirm_del(callback: types.CallbackQuery):
    product_id = callback.data.split("_")[-1]
    if product_id in assortment:
        del assortment[product_id]
        await send_or_edit(callback.bot, callback.message.chat.id, callback.from_user.id,
                           f"Продукт {product_id} удалён.")
    else:
        await send_or_edit(callback.bot, callback.message.chat.id, callback.from_user.id,
                           "Продукт не найден.")
    await callback.bot.send_message(callback.from_user.id, "Обновлённый ассортимент:",
                                    reply_markup=get_admin_assortment_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_cancel_del")
async def admin_cancel_del(callback: types.CallbackQuery):
    await send_or_edit(callback.bot, callback.message.chat.id, callback.from_user.id,
                       "Операция отменена.",
                       reply_markup=get_admin_assortment_keyboard())
    await callback.answer()
