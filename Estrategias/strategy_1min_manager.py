"""
Gestión de Operación de 1 Minuto - Quotex Bot
=============================================
Estrategia de trading con gestión de posición de 1 minuto

Características:
- Gestión automática del tamaño de posición
- Sistema de stop loss y take profit diario
- Recuperación de pérdidas (Martingala configurable)
- Notificaciones en tiempo real

"""

import asyncio
from pyquotex.stable_api import Quotex
from pyquotex.config import credentials

# Configuración del bot
CONFIG = {
    "email": "",
    "password": "",
    "amount": 10,              # Monto inicial
    "duration": 60,            # Duración de la operación (60 segundos = 1 minuto)
    "asset": "EURUSD_otc",    # Activo a operar
    
    # Gestión de riesgo
    "stop_loss": 100,          # Stop loss diario ($)
    "take_profit": 200,       # Take profit diario ($)
    "max_trades": 20,         # Máximo de operaciones por sesión
    
    # Martingala (recuperación de pérdidas)
    "martingale": True,       # Usar martingala
    "martingale_multiplier": 2.0,  # Multiplicador de martingala
    "max_martingale": 5,      # Máximo de niveles de martingala
    
    # Otras configuraciones
    "use_demo": True,          # Usar cuenta demo
    "debug": False,            # Modo debug
}

# Variables de estado
state = {
    "balance": 0.0,
    "profit": 0.0,
    "trades": 0,
    "wins": 0,
    "losses": 0,
    "current_amount": CONFIG["amount"],
    "martingale_level": 0,
    "daily_loss": 0.0,
    "daily_gain": 0.0,
    "running": False,
}


def log(message: str):
    """Función de logging."""
    if CONFIG["debug"]:
        print(f"[DEBUG] {message}")


async def setup_client():
    """Configura el cliente de Quotex."""
    email, password = credentials()
    if CONFIG["email"]:
        email = CONFIG["email"]
    if CONFIG["password"]:
        password = CONFIG["password"]
    
    client = Quotex(
        email=email,
        password=password,
        lang="pt",
    )
    return client


async def check_conditions(client, asset: str) -> tuple:
    """
    Verifica las condiciones del mercado para operar.
    
    Returns:
        tuple: (direction: str or None, reason: str)
    """
    try:
        # Obtener velas (últimas 5 para análisis)
        candles = await client.get_candles(asset, 60, 5)
        if not candles or len(candles) < 5:
            return None, "Sin datos de velas"
        
        # Obtener sentimiento del mercado
        sentiment = await client.get_realtime_sentiment(asset)
        
        # Análisis de precio
        prices = [c['price'] for c in candles]
        current_price = prices[-1]
        open_price = candles[-1]['open']
        
        # Calcular tendencia
        ma5 = sum(prices[-5:]) / 5
        ma3 = sum(prices[-3:]) / 3
        
        # Determinar tendencia
        if ma3 > ma5:
            trend = "CALL"
        elif ma3 < ma5:
            trend = "PUT"
        else:
            trend = None
        
        # Momento del precio
        price_change = current_price - open_price
        change_pct = (price_change / open_price) * 100
        
        # Obtener sentimiento del mercado (buy/sell ratio)
        buy_power = 0
        sell_power = 0
        if sentiment:
            buy_power = sentiment.get('buy', 0)
            sell_power = sentiment.get('sell', 0)
        
        # Decisión basada en múltiples factores
        score = 0
        
        # Factor 1: Tendencia
        if trend == "CALL":
            score += 1
        elif trend == "PUT":
            score -= 1
        
        # Factor 2: Momento del precio
        if change_pct > 0.001:
            score += 1
        elif change_pct < -0.001:
            score -= 1
        
        # Factor 3: Sentimiento del mercado
        if buy_power > sell_power:
            score += 1
        elif sell_power > buy_power:
            score -= 1
        
        # Factor 4: Precio vs media móvil
        if current_price > ma5:
            score += 1
        elif current_price < ma5:
            score -= 1
        
        # Determinar dirección (umbral bajo para más operaciones)
        if score >= 1:
            return "call", f"CALL (score: {score}, sentiment: B{buy_power}/S{sell_power})"
        elif score <= -1:
            return "put", f"PUT (score: {score}, sentiment: B{buy_power}/S{sell_power})"
        else:
            return None, f"NEUTRO (score: {score}, sin señal clara)"
            
    except Exception as e:
        log(f"Error verificando condiciones: {e}")
        return None, f"Error: {e}"


async def execute_trade(client, asset: str, direction: str, amount: float, duration: int) -> dict:
    """
    Ejecuta una operación.
    
    Returns:
        dict: Resultado de la operación
    """
    log(f"Ejecutando {direction.upper()} ${amount} en {asset}")
    
    status, buy_info = await client.buy(amount, asset, direction, duration)
    
    if not status:
        return {"success": False, "error": "No se pudo ejecutar la operación"}
    
    # Esperar resultado
    result = await check_trade_result(client, buy_info, direction)
    
    return {
        "success": True,
        "result": result,
        "amount": amount,
        "direction": direction,
        "profit": buy_info.get('profit', 0),
    }


async def check_trade_result(client, buy_info, direction: str) -> str:
    """
    Verifica el resultado de la operación.
    """
    open_price = buy_info.get('openPrice')
    asset = buy_info.get('asset')
    
    max_wait = 90  # segundos
    check_interval = 1  # segundos
    
    for _ in range(max_wait // check_interval):
        await asyncio.sleep(check_interval)
        
        prices = await client.get_realtime_price(asset)
        if not prices:
            continue
        
        current_price = prices[-1]['price']
        
        if direction == "call" and current_price > open_price:
            return "WIN"
        elif direction == "put" and current_price < open_price:
            return "WIN"
        elif current_price == open_price:
            return "DOJI"
        else:
            return "LOSS"
    
    return "UNKNOWN"


async def calculate_martingale(current_amount: float, result: str) -> float:
    """
    Calcula el siguiente monto según el sistema de martingala.
    
    Args:
        current_amount: Monto de la operación actual
        result: Resultado de la operación (WIN/LOSS)
    
    Returns:
        float: Siguiente monto
    """
    if result == "WIN":
        state["martingale_level"] = 0
        return CONFIG["amount"]
    
    if not CONFIG["martingale"]:
        return CONFIG["amount"]
    
    state["martingale_level"] += 1
    
    if state["martingale_level"] > CONFIG["max_martingale"]:
        log("Máximo nivel de martingala alcanzado")
        state["martingale_level"] = 0
        return CONFIG["amount"]
    
    new_amount = current_amount * CONFIG["martingale_multiplier"]
    
    # Redondear a 2 decimales
    return round(new_amount, 2)


async def check_daily_limits() -> tuple:
    """
    Verifica los límites diarios.
    
    Returns:
        tuple: (can_continue: bool, reason: str)
    """
    # Check stop loss
    if state["daily_loss"] >= CONFIG["stop_loss"]:
        return False, f"Stop loss diario alcanzado (${state['daily_loss']:.2f})"
    
    # Check take profit
    if state["daily_gain"] >= CONFIG["take_profit"]:
        return False, f"Take profit diario alcanzado (${state['daily_gain']:.2f})"
    
    # Check máximo de operaciones
    if state["trades"] >= CONFIG["max_trades"]:
        return False, f"Máximo de operaciones alcanzado ({state['trades']})"
    
    return True, "OK"


async def print_status():
    """Imprime el estado actual."""
    print("\n" + "=" * 50)
    print(f"  ESTADO DEL BOT - 1 MINUTO")
    print("=" * 50)
    print(f"  Balance:      ${state['balance']:.2f}")
    print(f"  Profit:       ${state['profit']:.2f}")
    print(f"  Operaciones:  {state['trades']}/{CONFIG['max_trades']}")
    print(f"  Wins:         {state['wins']}")
    print(f"  Losses:       {state['losses']}")
    print(f"  W/L Ratio:    {state['wins']/max(1, state['losses']):.2f}")
    print(f"  Martingala:   Nivel {state['martingale_level']}/{CONFIG['max_martingale']}")
    print(f"  Monto actual: ${state['current_amount']:.2f}")
    print("=" * 50 + "\n")


async def trading_strategy_1min(update_callback=None):
    """
    Estrategia principal de trading de 1 minuto.
    
    Args:
        update_callback: Función de callback para actualizaciones (opcional)
    """
    global state
    
    # Función helper para callbacks
    async def _call(msg):
        print(msg)
        if update_callback:
            try:
                result = update_callback(msg)
                if asyncio.iscoroutine(result):
                    await result
            except:
                pass
    
    await _call("=" * 60)
    await _call("  BOT DE TRADING - GESTIÓN 1 MINUTO")
    await _call("=" * 60)
    await _call(f"  Activo:      {CONFIG['asset']}")
    await _call(f"  Duración:    {CONFIG['duration']}s")
    await _call(f"  Monto inicio:${CONFIG['amount']}")
    await _call(f"  Stop Loss:   ${CONFIG['stop_loss']}")
    await _call(f"  Take Profit: ${CONFIG['take_profit']}")
    await _call(f"  Martingala:  {'Sí' if CONFIG['martingale'] else 'No'}")
    await _call("=" * 60)
    
    # Conectar
    client = await setup_client()
    check_connect, message = await client.connect()
    
    if not check_connect:
        await _call(f"ERROR de conexión: {message}")
        return False
    
    await _call("Conectado exitosamente")
    
    # Cambiar a demo o real
    account_type = "DEMO" if CONFIG["use_demo"] else "REAL"
    await client.change_account("PRACTICE" if CONFIG["use_demo"] else "REAL")
    
    # Obtener balance inicial
    state["balance"] = await client.get_balance()
    await _call(f"Balance {account_type}: ${state['balance']:.2f}")
    
    state["running"] = True
    state["trades"] = 0
    state["wins"] = 0
    state["losses"] = 0
    state["profit"] = 0.0
    state["current_amount"] = CONFIG["amount"]
    state["martingale_level"] = 0
    state["daily_loss"] = 0.0
    state["daily_gain"] = 0.0
    
    try:
        while state["running"]:
            # Verificar límites diarios
            can_continue, reason = await check_daily_limits()
            if not can_continue:
                await _call(f"\n⚠️ Límite alcanzado: {reason}")
                break
            
            # Verificar conexión
            if not await client.check_connect():
                await _call("⚠️ Conexión perdida. Reconectando...")
                await client.connect()
                await asyncio.sleep(5)
                continue
            
            # Verificar condiciones del mercado
            direction, reason = await check_conditions(client, CONFIG["asset"])
            
            if not direction:
                log(f"Sin señal: {reason}")
                await asyncio.sleep(5)
                continue
            
            await _call(f"\n📊 Operación #{state['trades'] + 1}")
            await _call(f"   Señal: {direction.upper()} ({reason})")
            await _call(f"   Monto: ${state['current_amount']:.2f}")
            
            # Ejecutar operación
            trade_result = await execute_trade(
                client,
                CONFIG["asset"],
                direction,
                state["current_amount"],
                CONFIG["duration"]
            )
            
            if not trade_result["success"]:
                await _call(f"   ❌ Error: {trade_result['error']}")
                continue
            
            # Procesar resultado
            result = trade_result["result"]
            profit = trade_result.get("profit", 0)
            
            state["trades"] += 1
            state["profit"] += profit
            
            if profit > 0:
                state["wins"] += 1
                state["daily_gain"] += profit
                await _call(f"   ✅ WIN +${profit:.2f}")
            elif profit < 0:
                state["losses"] += 1
                state["daily_loss"] += abs(profit)
                await _call(f"   ❌ LOSS -${abs(profit):.2f}")
            else:
                await _call(f"   ➡️ DOJI (Reembolso)")
            
            # Calcular siguiente monto (martingala)
            state["current_amount"] = await calculate_martingale(
                state["current_amount"], 
                result
            )
            
            # Mostrar estado
            await print_status()
            
            # Pausa entre operaciones
            await asyncio.sleep(2)
    
    except asyncio.CancelledError:
        await _call("\n⏹️ Bot detenido por el usuario")
    except Exception as e:
        await _call(f"\n❌ Error: {e}")
    finally:
        state["running"] = False
        await client.close()
        
        await _call("\n" + "=" * 60)
        await _call("  RESUMEN DE SESIÓN")
        await _call("=" * 60)
        await _call(f"  Total operaciones: {state['trades']}")
        await _call(f"  Wins: {state['wins']} | Losses: {state['losses']}")
        await _call(f"  Winrate: {state['wins']/max(1, state['trades'])*100:.1f}%")
        await _call(f"  Profit total: ${state['profit']:.2f}")
        await _call("=" * 60)


async def main():
    """Función principal."""
    await trading_strategy_1min()


if __name__ == "__main__":
    asyncio.run(main())
