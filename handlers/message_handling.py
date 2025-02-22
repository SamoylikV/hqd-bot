from aiogram import Router
from aiogram.types import Message, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton

import utils
from keyboards.admin_keyboards import get_admin_assortment_keyboard, get_flavor_input_keyboard, \
    get_admin_exit_reply_keyboard, admin_menu_reply
from state import user_data, admin_ids, admin_states, active_orders, active_conversations, assortment, send_or_edit

router = Router(name="message_handling")




@router.message(lambda message: message.text != "Выйти из диалога")
async def handle_messages(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    if str(user_id) in admin_ids and user_id in admin_states:
        state_info = admin_states[user_id]
        state = state_info.get("state")
        if "data" not in state_info:
            state_info["data"] = {}

        if state == "adding_product":
            if state_info.get("step") == "name":
                state_info["data"]["name"] = text
                state_info["step"] = "price"
                await send_or_edit(message.bot,
                    message.chat.id,
                    user_id,
                    "Введите цену продукта:",
                    reply_markup=ForceReply()
                )
                return

            elif state_info.get("step") == "price":
                try:
                    price = int(text)
                    state_info["data"]["price"] = price
                    state_info["step"] = "flavor_input"
                    await send_or_edit(message.bot,
                        message.chat.id,
                        user_id,
                        "Введите первый вкус продукта (оставьте пустым для завершения):",
                        reply_markup=ForceReply()
                    )
                except ValueError:
                    await send_or_edit(message.bot,
                        message.chat.id,
                        user_id,
                        "Цена должна быть числом. Введите цену продукта:",
                        reply_markup=ForceReply()
                    )
                return

            elif state_info.get("step") == "flavor_input":
                if text == "":
                    data = state_info["data"]
                    existing_ids = [int(k) for k in assortment.keys() if k.isdigit()]
                    new_id = str(max(existing_ids) + 1) if existing_ids else "1"
                    assortment[new_id] = {
                        "name": data["name"],
                        "base_price": data["price"],
                        "flavors": data.get("flavors", [])
                    }
                    await send_or_edit(message.bot,
                        message.chat.id,
                        user_id,
                        f"✅ Продукт добавлен:\nID: {new_id}\nНазвание: {data['name']}\n"
                        f"Цена: {data['price']}₽\nВкусы: {', '.join(data['flavors']) or 'нет'}",
                        reply_markup=admin_menu_reply
                    )
                    await message.answer("Обновленный ассортимент:", reply_markup=get_admin_assortment_keyboard())
                    admin_states.pop(user_id, None)
                else:
                    flavor = text.strip()
                    state_info["data"].setdefault("flavors", []).append(flavor)
                    await send_or_edit(message.bot,
                        message.chat.id,
                        user_id,
                        f"Вкус '{flavor}' добавлен. Хотите добавить еще?",
                        reply_markup=get_flavor_input_keyboard()
                    )
                return

        if state == "editing_product":
            if state_info.get("step") == "name_input":
                new_name = text if text else state_info["data"]["old_name"]
                state_info["data"]["new_name"] = new_name
                state_info["step"] = "price_choice"
                old_price = state_info["data"]["old_price"]
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Изменить цену", callback_data="admin_edit_price_yes"),
                     InlineKeyboardButton(text="Оставить без изменений", callback_data="admin_edit_price_no")]
                ])
                await send_or_edit(message.bot,
                    message.chat.id,
                    user_id,
                    f"Текущее значение цены: {old_price}₽\nХотите изменить цену?",
                    reply_markup=kb
                )
                return

            elif state_info.get("step") == "price_input":
                try:
                    price = int(text)
                    if price < 100:
                        raise ValueError("Цена не может быть меньше 100₽")
                except ValueError as e:
                    await send_or_edit(message.bot,
                        message.chat.id,
                        user_id,
                        f"❌ Ошибка: {str(e)}\nВведите цену снова:",
                        reply_markup=ForceReply()
                    )
                    return

                state_info["data"]["new_price"] = price
                prod_id = state_info.get("product_id")
                new_name = state_info["data"].get("new_name", state_info["data"]["old_name"])
                assortment[prod_id].update({"name": new_name, "base_price": price})
                await send_or_edit(message.bot,
                    message.chat.id,
                    user_id,
                    f"✅ Продукт обновлен!\nID: {prod_id}\nНазвание: {new_name}\nЦена: {price}₽",
                    reply_markup=get_admin_assortment_keyboard()
                )
                admin_states.pop(user_id, None)
                return

        elif state == "editing_product_flavors":
            prod_id = state_info.get("product_id")
            new_flavors = [f.strip() for f in text.split(",") if f.strip()]
            if prod_id in assortment:
                assortment[prod_id]["flavors"] = new_flavors
                await send_or_edit(message.bot,
                    message.chat.id,
                    user_id,
                    f"Вкусы для продукта {prod_id} обновлены: {', '.join(new_flavors)}",
                    reply_markup=admin_menu_reply
                )
                await send_or_edit(message.bot,
                    message.chat.id,
                    user_id,
                    "Обновлённый ассортимент:",
                    reply_markup=get_admin_assortment_keyboard()
                )
            else:
                await send_or_edit(message.bot,
                    message.chat.id,
                    user_id,
                    "Продукт не найден.",
                    reply_markup=admin_menu_reply
                )
            admin_states.pop(user_id, None)
            return

        elif state == "editing_global_flavors":
            new_flavors = [f.strip() for f in text.split(",") if f.strip()]
            await send_or_edit(message.bot,
                message.chat.id,
                user_id,
                f"Глобальные вкусы обновлены: {', '.join(new_flavors)}",
                reply_markup=admin_menu_reply
            )
            admin_states.pop(user_id, None)
            return

        elif state == "editing_delivery_fee":
            try:
                global DELIVERY_FEE
                DELIVERY_FEE = int(text)
                await send_or_edit(message.bot,
                    message.chat.id,
                    user_id,
                    f"Цена доставки обновлена: {DELIVERY_FEE}₽",
                    reply_markup=admin_menu_reply
                )
            except ValueError:
                await send_or_edit(message.bot,
                    message.chat.id,
                    user_id,
                    "Ошибка! Введите целое число:",
                    reply_markup=ForceReply()
                )
                return
            admin_states.pop(user_id, None)
            return
    if user_data.get(user_id, {}).get("in_chat"):
        partner_id = active_conversations.get(user_id)
        if partner_id:
            reply_kb = get_admin_exit_reply_keyboard() if partner_id in admin_ids else None
            await message.bot.send_message(partner_id, message.text, reply_markup=reply_kb)
        return

    if user_id in admin_ids:
        if text == "Активные заказы":
            if active_orders:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"{order['product']['name']} от {uid}",
                                          callback_data=f"active_order_{uid}")]
                    for uid, order in active_orders.items()
                ])
                await send_or_edit(message.bot, message.chat.id, user_id, "Список активных заказов:", reply_markup=kb)
            else:
                await send_or_edit(message.bot, message.chat.id, user_id, "Нет активных заказов.")
            return

    if user_data.get(user_id, {}).get("awaiting_address", False):
        address = text.strip()
        location = utils.get_location(address)
        print(location)
        if location is None:
            await send_or_edit(message.bot,
                               message.chat.id,
                               user_id,
                               "❌ Неверный формат адреса. Пожалуйста, введите адрес в формате:\nГ. Санкт-Петербург, Улица Примерная 123",
                               reply_markup=ForceReply()
                               )
            return
        user_data[user_id]["temp_address"] = address
        user_data[user_id]["awaiting_address"] = False
        save_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="save_address_yes"),
             InlineKeyboardButton(text="Нет", callback_data="save_address_no")]
        ])
        await send_or_edit(message.bot,
                           message.chat.id,
                           user_id,
                           f"Вы ввели адрес:\n{address}\nЗапомнить адрес для будущих заказов?",
                           reply_markup=save_keyboard
                           )
        return