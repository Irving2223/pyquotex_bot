# PCR Trading Bot - Put Call Ratio Strategy
# Estrategia de 1 minuto basada en el Put/Call Ratio

import asyncio
from pyquotex.config import credentials
from pyquotex.stable_api import Quotex

email, password = credentials()
client = Quotex(
    email=email,
    password=password,
    lang="pt",
)

# Configuración del trading (exportable)
TRADING_CONFIG = {
    "amount": 10,
    "duration": 60,
    "asset": "EURUSD_otc",
    "pcr_buy_threshold": 1.3,
    "pcr_sell_threshold": 0.7,
    "wins": 0,
    "losses": 0,
    "dojis": 0,
    "trades": 0,
    "profit": 0.0,
    "balance": 0.0,
}


async def get_pcr(asset_name, samples=10):
    """
    Calcula el Put/Call Ratio promediando múltiples muestras del sentimiento.

    Args:
        asset_name: Nombre del activo
        samples: Número de muestras a promediar

    Returns:
        float: Put/Call Ratio
    """
    sell_values = []
    buy_values = []

    for _ in range(samples):
        market_mood = await client.get_realtime_sentiment(asset_name)
        if market_mood and 'sell' in market_mood and 'buy' in market_mood:
            sell_values.append(market_mood['sell'])
            buy_values.append(market_mood['buy'])
        await asyncio.sleep(0.3)

    if sum(buy_values) > 0:
        pcr = sum(sell_values) / sum(buy_values)
        return pcr
    return 1.0


async def check_result(buy_data, direction):
    """
    Verifica el resultado de la operación.

    Args:
        buy_data: Información de la compra
        direction: Dirección de la operación (call/put)

    Returns:
        str: Resultado (Win/Loss/Doji)
    """
    open_price = buy_data.get('openPrice')

    while True:
        prices = await client.get_realtime_price(buy_data['asset'])

        if not prices:
            continue

        current_price = prices[-1]['price']

        if direction == "call" and current_price > open_price:
            return 'Win'
        elif direction == "put" and current_price < open_price:
            return 'Win'
        elif current_price == open_price:
            return 'Doji'
        else:
            return 'Loss'


async def pcr_trading_strategy(update_callback=None):
    """
    Estrategia principal de PCR.

    Parámetros de la estrategia:
    - PCR < 0.7: Mercado muy bullish -> Esperar corrección o operar PUT
    - PCR > 1.3: Mercado muy bearish -> Esperar corrección o operar CALL
    - PCR 0.7-1.3: Mercado equilibrado -> No operar
    """
    global TRADING_CONFIG

    # Configuración de la estrategia
    AMOUNT = TRADING_CONFIG["amount"]
    DURATION = TRADING_CONFIG["duration"]
    ASSET = TRADING_CONFIG["asset"]
    PCR_BUY_THRESHOLD = TRADING_CONFIG["pcr_buy_threshold"]
    PCR_SELL_THRESHOLD = TRADING_CONFIG["pcr_sell_threshold"]

    # Función helper para callbacks sync/async
    async def _call_callback(msg):
        if update_callback:
            try:
                # Verificar si es una coroutine
                result = update_callback(msg)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass

    await _call_callback("=" * 60)
    await _call_callback("  BOT DE TRADING PCR (Put/Call Ratio)")
    await _call_callback("  Timeframe: 1 minuto")
    await _call_callback(f"  Activo: {ASSET}")
    await _call_callback(f"  Monto inicial: ${AMOUNT}")
    await _call_callback("=" * 60)

    check_connect, message = await client.connect()

    if not check_connect:
        await _call_callback(f"ERROR: No se pudo conectar: {message}")
        return False

    # Cambiar a cuenta demo (PRACTICE) o real (REAL)
    await client.change_account("PRACTICE")
    TRADING_CONFIG["balance"] = await client.get_balance()

    await _call_callback(f"Balance demo: ${TRADING_CONFIG['balance']:.2f}")

    asset_name, asset_data = await client.get_available_asset(ASSET, force_open=True)

    if not asset_data or len(asset_data) < 3 or not asset_data[2]:
        await _call_callback(f"ERROR: El activo {ASSET} está cerrado.")
        return False

    await _call_callback(f"Activo {ASSET} abierto. Iniciando estrategia PCR...")

    trade_count = TRADING_CONFIG["trades"]
    wins = TRADING_CONFIG["wins"]
    losses = TRADING_CONFIG["losses"]
    dojis = TRADING_CONFIG["dojis"]

    try:
        while True:
            # Verificar conexión
            if not await client.check_connect():
                await _call_callback("Conexión perdida. Reconectando...")
                await client.connect()

            # Obtener PCR
            pcr = await get_pcr(asset_name, samples=15)

            await _call_callback(f"\nOperación #{trade_count + 1}")
            await _call_callback(f"PCR: {pcr:.2f}")

            # Lógica de la estrategia PCR
            direction = None

            if pcr > PCR_BUY_THRESHOLD:
                direction = "call"
                signal = "CALL (PCR ALTO - Sobreventa)"
                await _call_callback(f"Señal: {signal}")
            elif pcr < PCR_SELL_THRESHOLD:
                direction = "put"
                signal = "PUT (PCR BAJO - Sobrecompra)"
                await _call_callback(f"Señal: {signal}")
            else:
                await _call_callback(f"Señal: NEUTRO - Sin operar (PCR: {pcr:.2f})")

            if direction:
                # Ejecutar operación
                balance = await client.get_balance()
                balance -= AMOUNT

                await _call_callback(f"Ejecutando: {direction.upper()} ${AMOUNT}")

                status, buy_info = await client.buy(AMOUNT, asset_name, direction, DURATION)

                if not status:
                    await _call_callback("ERROR: No se pudo colocar la apuesta")
                    continue

                result = await check_result(buy_info, direction)

                profit = 0
                if result == "Win":
                    payout = client.get_payout_by_asset(asset_name)
                    profit = (payout / 100) * AMOUNT
                    balance += AMOUNT + profit
                    await _call_callback(f"Resultado: WIN +${profit:.2f}")
                    wins += 1
                elif result == "Doji":
                    balance += AMOUNT
                    await _call_callback("Resultado: DOJI (Reembolso)")
                    dojis += 1
                else:
                    await _call_callback(f"Resultado: LOSS -${AMOUNT:.2f}")
                    losses += 1

                trade_count += 1
                TRADING_CONFIG["balance"] = balance
                TRADING_CONFIG["profit"] += profit

            # Actualizar estadísticas
            TRADING_CONFIG["trades"] = trade_count
            TRADING_CONFIG["wins"] = wins
            TRADING_CONFIG["losses"] = losses
            TRADING_CONFIG["dojis"] = dojis

            await _call_callback(f"Balance: ${TRADING_CONFIG['balance']:.2f}")
            winrate = wins/max(1, trade_count)*100
            await _call_callback(f"Stats: {wins}W/{losses}L/{dojis}D (Winrate: {winrate:.1f}%)")

            await asyncio.sleep(2)

    except asyncio.CancelledError:
        raise
    except Exception as e:
        await _call_callback(f"Error: {e}")
        return False

    return True


async def main():
    """Función principal para ejecutar el bot standalone"""
    print("=" * 60)
    print("  BOT DE TRADING PCR (Put/Call Ratio)")
    print("  Timeframe: 1 minuto")
    print(f"  Activo: {TRADING_CONFIG['asset']}")
    print(f"  Monto inicial: ${TRADING_CONFIG['amount']}")
    print("=" * 60)

    result = await pcr_trading_strategy(print)

    print("\nBot detenido.")
    print(f"Balance final: ${TRADING_CONFIG['balance']:.2f}")
    print(f"Ganancia total: ${TRADING_CONFIG['profit']:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
