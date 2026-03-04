# Telegram Bot for PyQuotex PCR Trading Bot
# Vinculado a ID de Telegram: 1796586571

import asyncio
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes


# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Token del bot de Telegram
TELEGRAM_TOKEN = "8534216772:AAHGnwej_UFfPyyqLJ4uIvQHejVuWu2AIlQ"

# ID de Telegram autorizado
AUTHORIZED_USER_ID = 1796586571

# Estados del bot
class TradingBotState:
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"

# Variables globales
bot_state = TradingBotState.IDLE
bot_task = None

# Balance al inicio del dia (para calcular profit diario)
daily_start_balance = 0.0
daily_start_profit = 0.0

# Teclado principal
def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🚀 Iniciar Bot", callback_data="start_bot"),
            InlineKeyboardButton("⏹️ Detener Bot", callback_data="stop_bot"),
        ],
        [
            InlineKeyboardButton("📊 Ver Estado", callback_data="status"),
            InlineKeyboardButton("💰 Balance + Daily", callback_data="balance_daily"),
        ],
        [
            InlineKeyboardButton("📈 Operaciones", callback_data="stats"),
            InlineKeyboardButton("⚙️ Configuración", callback_data="settings"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# Teclado de configuración
def get_settings_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("💵 $10", callback_data="amount_10"),
            InlineKeyboardButton("💵 $20", callback_data="amount_20"),
            InlineKeyboardButton("💵 $50", callback_data="amount_50"),
        ],
        [
            InlineKeyboardButton("⏱️ 30s", callback_data="duration_30"),
            InlineKeyboardButton("⏱️ 60s", callback_data="duration_60"),
            InlineKeyboardButton("⏱️ 120s", callback_data="duration_120"),
        ],
        [
            InlineKeyboardButton("🔙 Volver", callback_data="back"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# Importar funciones del bot PCR
from pyquotex.Estrategias.pcr_bot import (
    client,
    TRADING_CONFIG,
    get_pcr,
    check_result
)


# Función para enviar notificaciones
async def send_notification(context, text, parse_mode="Markdown"):
    """Envía notificación al usuario autorizado"""
    try:
        await context.bot.send_message(
            AUTHORIZED_USER_ID,
            text,
            parse_mode=parse_mode
        )
    except Exception as e:
        logger.error(f"Error enviando notificación: {e}")


# Funciones del bot de Telegram
async def start(update, context):
    """Comando /start"""
    user_id = update.message.from_user.id

    # Verificar si es el usuario autorizado
    if user_id != AUTHORIZED_USER_ID:
        await update.message.reply_text(
            "❌ *Acceso Denegado*\n\n"
            "No tienes autorización para usar este bot.",
            parse_mode="Markdown"
        )
        return

    welcome_text = (
        "🤖 *Bot de Trading PCR* (Put/Call Ratio)\n\n"
        "Este bot automatiza operaciones en Quotex usando la estrategia PCR.\n\n"
        "📊 *Estrategia PCR:*\n"
        "• PCR > 1.3 -> CALL (Sobreventa)\n"
        "• PCR < 0.7 -> PUT (Sobrecompra)\n\n"
        "🕐 *Timeframe:* 1 minuto\n\n"
        "Presiona el botón de abajo para comenzar."
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )


async def help_command(update, context):
    """Comando /help"""
    user_id = update.message.from_user.id

    if user_id != AUTHORIZED_USER_ID:
        return

    help_text = (
        "📚 *Ayuda del Bot de Trading*\n\n"
        "🎯 *Comandos disponibles:*\n"
        "/start - Iniciar el bot\n"
        "/stop - Detener el bot\n"
        "/status - Ver estado actual\n"
        "/balance - Ver balance de la cuenta\n"
        "/daily - Ver profit diario de estrategias\n"
        "/stats - Ver estadísticas de operaciones\n\n"
        "🔘 *Botones:*\n"
        "Usa los botones inline para controlar el bot."
    )

    await update.message.reply_text(
        help_text,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )


async def daily_command(update, context):
    """Comando /daily - Muestra balance y profit diario"""
    global daily_start_balance, daily_start_profit
    
    user_id = update.message.from_user.id
    
    if user_id != AUTHORIZED_USER_ID:
        return
    
    try:
        # Conectar con Quotex
        check_connect, _ = await client.connect()
        if not check_connect:
            await update.message.reply_text(
                "❌ No se pudo conectar con Quotex"
            )
            return
        
        await client.change_account("PRACTICE")
        current_balance = await client.get_balance()
        
        # Si es la primera vez, inicializar
        if daily_start_balance == 0.0:
            daily_start_balance = current_balance
            daily_start_profit = TRADING_CONFIG['profit']
        
        # Si es la primera vez, inicializar
        if daily_start_balance == 0.0:
            daily_start_balance = current_balance
            daily_start_profit = TRADING_CONFIG['profit']
        
        # Calcular profit diario
        daily_profit = current_balance - daily_start_balance
        total_strategy_profit = TRADING_CONFIG['profit']
        
        daily_text = (
            f"💰 *Balance y Profit Diario:*\n\n"
            f"📊 *Cuenta:*\n"
            f"• Balance actual: ${current_balance:.2f}\n"
            f"• Balance inicio del dia: ${daily_start_balance:.2f}\n\n"
            f"📈 *Profit:*\n"
            f"• Daily Profit: ${daily_profit:+.2f}\n"
            f"• Profit estrategias: ${total_strategy_profit:+.2f}\n\n"
            f"📋 *Operaciones hoy:*\n"
            f"• Wins: {TRADING_CONFIG['wins']}\n"
            f"• Losses: {TRADING_CONFIG['losses']}\n"
            f"• Total: {TRADING_CONFIG['trades']}"
        )
        
        # Agregar emoji segun profit
        if daily_profit > 0:
            daily_text += "\n\n🟢 Dia rentable!"
        elif daily_profit < 0:
            daily_text += "\n\n🔴 Dia con perdidas"
        else:
            daily_text += "\n\n⚪ Sin cambios"
        
        await update.message.reply_text(
            daily_text,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error al obtener datos: {e}"
        )


async def button_handler(update, context):
    """Manejador de botones inline"""
    query = update.callback_query
    user_id = query.from_user.id

    # Verificar si es el usuario autorizado
    if user_id != AUTHORIZED_USER_ID:
        await query.answer()
        await query.edit_message_text(
            "❌ *Acceso Denegado*\n\n"
            "No tienes autorización para usar este bot.",
            parse_mode="Markdown"
        )
        return

    await query.answer()

    global bot_state, bot_task

    if query.data == "start_bot":
        if bot_state == TradingBotState.RUNNING:
            await query.edit_message_text(
                "⚠️ El bot ya está ejecutándose.",
                reply_markup=get_main_keyboard()
            )
            return

        bot_state = TradingBotState.RUNNING
        
        # Inicializar balance diario si es la primera vez
        global daily_start_balance, daily_start_profit
        if daily_start_balance == 0.0:
            await client.connect()
            await client.change_account("PRACTICE")
            daily_start_balance = await client.get_balance()
            daily_start_profit = TRADING_CONFIG['profit']

        status_text = (
            "🚀 *Iniciando Bot de Trading PCR...*\n\n"
            f"📊 *Configuración:*\n"
            f"• Activo: {TRADING_CONFIG['asset']}\n"
            f"• Monto: ${TRADING_CONFIG['amount']}\n"
            f"• Duración: {TRADING_CONFIG['duration']}s\n"
            f"• PCR Buy: {TRADING_CONFIG['pcr_buy_threshold']}\n"
            f"• PCR Sell: {TRADING_CONFIG['pcr_sell_threshold']}\n\n"
            "⏳ Conectando con Quotex..."
        )

        await query.edit_message_text(
            status_text,
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

        # Iniciar el bot de trading
        bot_task = asyncio.create_task(run_trading_bot(query, context))

    elif query.data == "stop_bot":
        if bot_state != TradingBotState.RUNNING:
            await query.edit_message_text(
                "⚠️ El bot no está ejecutándose.",
                reply_markup=get_main_keyboard()
            )
            return

        bot_state = TradingBotState.STOPPED
        if bot_task:
            bot_task.cancel()

        stats_text = (
            f"⏹️ *Bot Detenido*\n\n"
            f"📊 *Estadísticas finales:*\n"
            f"• Operaciones: {TRADING_CONFIG['trades']}\n"
            f"• Wins: {TRADING_CONFIG['wins']}\n"
            f"• Losses: {TRADING_CONFIG['losses']}\n"
            f"• Dojis: {TRADING_CONFIG['dojis']}\n"
            f"• Ganancia total: ${TRADING_CONFIG['profit']:.2f}\n"
            f"• Balance final: ${TRADING_CONFIG['balance']:.2f}"
        )

        await query.edit_message_text(
            stats_text,
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

        # Notificar cierre
        await send_notification(
            context,
            "🔴 *BOT DE TRADING CERRADO*\n\n"
            f"📊 *Resumen:*\n"
            f"• Total operaciones: {TRADING_CONFIG['trades']}\n"
            f"• Wins: {TRADING_CONFIG['wins']}\n"
            f"• Losses: {TRADING_CONFIG['losses']}\n"
            f"• Dojis: {TRADING_CONFIG['dojis']}\n"
            f"• Ganancia total: ${TRADING_CONFIG['profit']:.2f}\n"
            f"• Balance final: ${TRADING_CONFIG['balance']:.2f}"
        )

    elif query.data == "status":
        status_emoji = "🟢" if bot_state == TradingBotState.RUNNING else "🔴"
        winrate = TRADING_CONFIG['wins']/max(1, TRADING_CONFIG['trades'])*100

        status_msg = (
            f"📊 *Estado del Bot:* {status_emoji}\n\n"
            f"📈 *Configuración actual:*\n"
            f"• Activo: {TRADING_CONFIG['asset']}\n"
            f"• Monto: ${TRADING_CONFIG['amount']}\n"
            f"• Duración: {TRADING_CONFIG['duration']}s\n"
            f"• PCR Buy: {TRADING_CONFIG['pcr_buy_threshold']}\n"
            f"• PCR Sell: {TRADING_CONFIG['pcr_sell_threshold']}\n\n"
            f"📊 *Estadísticas:*\n"
            f"• Operaciones: {TRADING_CONFIG['trades']}\n"
            f"• Wins: {TRADING_CONFIG['wins']}\n"
            f"• Losses: {TRADING_CONFIG['losses']}\n"
            f"• Winrate: {winrate:.1f}%"
        )

        await query.edit_message_text(
            status_msg,
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

    elif query.data == "balance":
        try:
            check_connect, _ = await client.connect()
            if check_connect:
                await client.change_account("PRACTICE")
                balance = await client.get_balance()
                balance_text = (
                    f"💰 *Balance de la Cuenta:*\n\n"
                    f"• Demo Balance: ${balance:.2f}\n\n"
                    f"💡 Usa /balance para actualizar"
                )
                await query.edit_message_text(
                    balance_text,
                    reply_markup=get_main_keyboard(),
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(
                    "❌ No se pudo conectar con Quotex",
                    reply_markup=get_main_keyboard()
                )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Error al obtener balance: {e}",
                reply_markup=get_main_keyboard()
            )

    elif query.data == "balance_daily":
        try:
            check_connect, _ = await client.connect()
            if check_connect:
                await client.change_account("PRACTICE")
                current_balance = await client.get_balance()
                
                # Si es la primera vez del dia, inicializar
                if daily_start_balance == 0.0:
                    daily_start_balance = current_balance
                    daily_start_profit = TRADING_CONFIG['profit']
                
                # Calcular profit diario
                daily_profit = current_balance - daily_start_balance
                total_strategy_profit = TRADING_CONFIG['profit']
                
                balance_text = (
                    f"💰 *Balance y Profit Diario:*\n\n"
                    f"📊 *Cuenta:*\n"
                    f"• Balance actual: ${current_balance:.2f}\n"
                    f"• Balance inicio del dia: ${daily_start_balance:.2f}\n\n"
                    f"📈 *Profit:*\n"
                    f"• Daily Profit: ${daily_profit:+.2f}\n"
                    f"• Profit estrategias: ${total_strategy_profit:+.2f}\n\n"
                    f"📋 *Operaciones hoy:*\n"
                    f"• Wins: {TRADING_CONFIG['wins']}\n"
                    f"• Losses: {TRADING_CONFIG['losses']}\n"
                    f"• Total: {TRADING_CONFIG['trades']}"
                )
                
                # Agregar emoji segun profit
                if daily_profit > 0:
                    balance_text += "\n\n🟢 Dia rentable!"
                elif daily_profit < 0:
                    balance_text += "\n\n🔴 Dia con perdidas"
                else:
                    balance_text += "\n\n⚪ Sin cambios"
                
                await query.edit_message_text(
                    balance_text,
                    reply_markup=get_main_keyboard(),
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(
                    "❌ No se pudo conectar con Quotex",
                    reply_markup=get_main_keyboard()
                )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Error al obtener balance: {e}",
                reply_markup=get_main_keyboard()
            )

    elif query.data == "stats":
        winrate = TRADING_CONFIG['wins']/max(1, TRADING_CONFIG['trades'])*100
        stats_msg = (
            f"📈 *Estadísticas de Trading:*\n\n"
            f"🔢 *Generales:*\n"
            f"• Total operaciones: {TRADING_CONFIG['trades']}\n"
            f"• Wins: {TRADING_CONFIG['wins']}\n"
            f"• Losses: {TRADING_CONFIG['losses']}\n"
            f"• Dojis: {TRADING_CONFIG['dojis']}\n"
            f"• Winrate: {winrate:.1f}%\n\n"
            f"💰 *Financieras:*\n"
            f"• Ganancia total: ${TRADING_CONFIG['profit']:.2f}\n"
            f"• Balance actual: ${TRADING_CONFIG['balance']:.2f}"
        )

        await query.edit_message_text(
            stats_msg,
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

    elif query.data == "settings":
        await query.edit_message_text(
            "⚙️ *Configuración del Bot*\n\n"
            "Selecciona qué parámetro deseas cambiar:",
            reply_markup=get_settings_keyboard(),
            parse_mode="Markdown"
        )

    elif query.data.startswith("amount_"):
        new_amount = float(query.data.split("_")[1])
        TRADING_CONFIG["amount"] = new_amount
        await query.edit_message_text(
            f"✅ *Monto actualizado:* ${new_amount}",
            reply_markup=get_settings_keyboard(),
            parse_mode="Markdown"
        )

    elif query.data.startswith("duration_"):
        new_duration = int(query.data.split("_")[1])
        TRADING_CONFIG["duration"] = new_duration
        await query.edit_message_text(
            f"✅ *Duración actualizada:* {new_duration}s",
            reply_markup=get_settings_keyboard(),
            parse_mode="Markdown"
        )

    elif query.data == "back":
        await query.edit_message_text(
            "🤖 *Menú Principal*\n\n"
            "Usa los botones para controlar el bot de trading.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )


async def run_trading_bot(query, context):
    """Función principal del bot de trading PCR"""
    try:
        # Conectar con Quotex
        check_connect, message = await client.connect()

        if not check_connect:
            await query.edit_message_text(
                f"❌ *Error de conexión:* {message}",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
            return

        # Obtener balance
        await client.change_account("PRACTICE")
        TRADING_CONFIG["balance"] = await client.get_balance()

        await query.edit_message_text(
            "✅ *Conectado a Quotex*\n\n"
            f"💰 Balance: ${TRADING_CONFIG['balance']:.2f}\n\n"
            "📊 Iniciando análisis PCR...",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

        asset_name, asset_data = await client.get_available_asset(
            TRADING_CONFIG['asset'], force_open=True
        )

        if not asset_data or len(asset_data) < 3 or not asset_data[2]:
            await query.edit_message_text(
                f"❌ El activo {TRADING_CONFIG['asset']} está cerrado.",
                reply_markup=get_main_keyboard()
            )
            return

        # Notificar inicio
        await send_notification(
            context,
            "🚀 *BOT DE TRADING ARRANCADO*\n\n"
            f"📊 Estrategia: PCR (Put/Call Ratio)\n"
            f"⏱️ Timeframe: 1 minuto\n"
            f"💰 Balance inicial: ${TRADING_CONFIG['balance']:.2f}\n\n"
            "🔔 Recibirás notificaciones de cada operación."
        )

        # Loop principal de trading
        while bot_state == TradingBotState.RUNNING:
            try:
                # Obtener PCR
                pcr = await get_pcr(asset_name, samples=15)

                # Mostrar estado actual
                await query.edit_message_text(
                    f"🔄 *Bot Ejecutándose*\n\n"
                    f"📊 PCR Actual: {pcr:.2f}\n"
                    f"📈 Operaciones: {TRADING_CONFIG['trades']}\n"
                    f"💰 Balance: ${TRADING_CONFIG['balance']:.2f}\n\n"
                    f"⏳ Analizando mercado...",
                    reply_markup=get_main_keyboard(),
                    parse_mode="Markdown"
                )

                # Decidir dirección basada en PCR
                direction = None
                signal = ""

                if pcr > TRADING_CONFIG['pcr_buy_threshold']:
                    direction = "call"
                    signal = f"📈 CALL (PCR: {pcr:.2f} - Sobreventa)"
                elif pcr < TRADING_CONFIG['pcr_sell_threshold']:
                    direction = "put"
                    signal = f"📉 PUT (PCR: {pcr:.2f} - Sobrecompra)"

                if direction:
                    # Notificar señal
                    await send_notification(
                        context,
                        f"🎯 *SEÑAL DE TRADING*\n\n"
                        f"{signal}\n"
                        f"💵 Monto: ${TRADING_CONFIG['amount']}\n"
                        f"⏱️ Duración: {TRADING_CONFIG['duration']}s"
                    )

                    # Ejecutar operación
                    balance = await client.get_balance()
                    balance -= TRADING_CONFIG['amount']

                    await query.edit_message_text(
                        f"🔄 Ejecutando {direction.upper()} ${TRADING_CONFIG['amount']}...",
                        reply_markup=get_main_keyboard()
                    )

                    status, buy_info = await client.buy(
                        TRADING_CONFIG['amount'], asset_name, direction, TRADING_CONFIG['duration']
                    )

                    if not status:
                        await query.edit_message_text(
                            "❌ Error al colocar la apuesta",
                            reply_markup=get_main_keyboard()
                        )
                        continue

                    await query.edit_message_text(
                        "✅ Apuesta colocada. Esperando resultado...",
                        reply_markup=get_main_keyboard()
                    )

                    result = await check_result(buy_info, direction)

                    profit = 0
                    if result == "Win":
                        payout = client.get_payout_by_asset(asset_name)
                        profit = (payout / 100) * TRADING_CONFIG['amount']
                        balance += TRADING_CONFIG['amount'] + profit
                        result_msg = f"🎉 WIN! +${profit:.2f}"
                        TRADING_CONFIG["wins"] += 1
                    elif result == "Doji":
                        balance += TRADING_CONFIG['amount']
                        result_msg = "⚪ DOJI (Reembolso)"
                        TRADING_CONFIG["dojis"] += 1
                    else:
                        result_msg = f"💔 LOSS -${TRADING_CONFIG['amount']:.2f}"
                        TRADING_CONFIG["losses"] += 1

                    TRADING_CONFIG["trades"] += 1
                    TRADING_CONFIG["profit"] += profit
                    TRADING_CONFIG["balance"] = balance

                    # Notificar resultado
                    winrate = TRADING_CONFIG['wins']/TRADING_CONFIG['trades']*100
                    await send_notification(
                        context,
                        f"📊 *RESULTADO DE OPERACIÓN*\n\n"
                        f"{result_msg}\n"
                        f"📈 PCR: {pcr:.2f}\n"
                        f"💰 Balance: ${TRADING_CONFIG['balance']:.2f}\n"
                        f"📊 Winrate: {winrate:.1f}%"
                    )

                await asyncio.sleep(3)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error en trading loop: {e}")
                await asyncio.sleep(5)

    except asyncio.CancelledError:
        logger.info("Trading bot cancelled")
    except Exception as e:
        logger.error(f"Error en trading bot: {e}")
    finally:
        TRADING_CONFIG["balance"] = await client.get_balance()
        await send_notification(
            context,
            "🔴 *BOT DE TRADING CERRADO*\n\n"
            f"📊 *Resumen:*\n"
            f"• Total operaciones: {TRADING_CONFIG['trades']}\n"
            f"• Wins: {TRADING_CONFIG['wins']}\n"
            f"• Losses: {TRADING_CONFIG['losses']}\n"
            f"• Dojis: {TRADING_CONFIG['dojis']}\n"
            f"• Ganancia total: ${TRADING_CONFIG['profit']:.2f}\n"
            f"• Balance final: ${TRADING_CONFIG['balance']:.2f}"
        )
        client.close()


# Variable global para la aplicación
application = None


def main():
    """Función principal del bot de Telegram"""
    global application

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("daily", daily_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Iniciar bot
    print("🤖 Bot de Telegram iniciado...")
    print(f"🔐 Vinculado a ID: {AUTHORIZED_USER_ID}")
    print("Usa /start en Telegram para comenzar")
    application.run_polling()


if __name__ == "__main__":
    main()
