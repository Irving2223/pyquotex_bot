# Patrones de Velas Bot - Estrategia de Patrones Candlestick
# Analiza formas específicas como velas envolventes, martillos o morning stars
# para determinar la probabilidad de dirección del precio basándose en el impulso

import asyncio
import time
from pyquotex.config import credentials
from pyquotex.stable_api import Quotex


email, password = credentials()
client = Quotex(
    email=email,
    password=password,
    lang="es",
)


# Configuración del trading
TRADING_CONFIG = {
    "amount": 10,
    "duration": 60,
    "asset": "EURUSD_otc",
    "period": 60,  # período de la vela en segundos
    "lookback_candles": 10,  # número de velas para analizar patrones
    "wins": 0,
    "losses": 0,
    "trades": 0,
    "profit": 0.0,
    "balance": 0.0,
}


def is_bullish_candle(candle):
    """Determina si una vela es alcista (cierre > apertura)."""
    return candle['close'] > candle['open']


def is_bearish_candle(candle):
    """Determina si una vela es bajista (cierre < apertura)."""
    return candle['close'] < candle['open']


def get_body_size(candle):
    """Calcula el tamaño del cuerpo de la vela."""
    return abs(candle['close'] - candle['open'])


def get_full_range(candle):
    """Calcula el rango completo de la vela (mecha a mecha)."""
    return candle['high'] - candle['low']


def get_upper_shadow(candle):
    """Calcula la sombra superior."""
    body_top = max(candle['open'], candle['close'])
    return candle['high'] - body_top


def get_lower_shadow(candle):
    """Calcula la sombra inferior."""
    body_bottom = min(candle['open'], candle['close'])
    return body_bottom - candle['low']


def is_hammer(candle, prev_candles=None):
    """
    Patrón Martillo (Hammer): Vela pequeña en la parte superior con mecha inferior larga.
    Indica potencial reversión alcista.
    """
    body_size = get_body_size(candle)
    full_range = get_full_range(candle)
    
    # El cuerpo debe ser pequeño respecto al rango
    if full_range == 0:
        return False
    
    body_ratio = body_size / full_range
    
    lower_shadow = get_lower_shadow(candle)
    upper_shadow = get_upper_shadow(candle)
    
    # Martillo: mecha inferior >= 2x el cuerpo, mecha superior pequeña
    is_hammer_shape = (
        lower_shadow >= body_size * 2 and  # mecha inferior larga
        upper_shadow <= body_size * 0.5 and  # mecha superior pequeña
        body_ratio <= 0.4  # cuerpo pequeño
    )
    
    # Confirmación: vela hammer debe ser alcista o coincide con tendencia
    if is_hammer_shape and is_bullish_candle(candle):
        return True
    
    return False


def is_inverted_hammer(candle):
    """
    Patrón Martillo Invertido (Inverted Hammer): Vela pequeña en la parte inferior
    con mecha superior larga. Indica potencial reversión alcista.
    """
    body_size = get_body_size(candle)
    full_range = get_full_range(candle)
    
    if full_range == 0:
        return False
    
    body_ratio = body_size / full_range
    
    lower_shadow = get_lower_shadow(candle)
    upper_shadow = get_upper_shadow(candle)
    
    # Martillo invertido: mecha superior >= 2x el cuerpo, mecha inferior pequeña
    return (
        upper_shadow >= body_size * 2 and
        lower_shadow <= body_size * 0.5 and
        body_ratio <= 0.4
    )


def is_shooting_star(candle):
    """
    Patrón Estrella Fugaz (Shooting Star): Vela pequeña en la parte inferior
    con mecha superior larga. Indica potencial reversión bajista.
    """
    body_size = get_body_size(candle)
    full_range = get_full_range(candle)
    
    if full_range == 0:
        return False
    
    body_ratio = body_size / full_range
    
    lower_shadow = get_lower_shadow(candle)
    upper_shadow = get_upper_shadow(candle)
    
    # Estrella fugaz: mecha superior >= 2x el cuerpo, mecha inferior pequeña
    return (
        upper_shadow >= body_size * 2 and
        lower_shadow <= body_size * 0.5 and
        body_ratio <= 0.4 and
        is_bearish_candle(candle)
    )


def is_bullish_engulfing(candle1, candle2):
    """
    Patrón Envolvente Alcista (Bullish Engulfing):
    Una vela bajista pequeña seguida por una vela alcista grande que la envuelve.
    Indica potencial reversión alcista.
    """
    # Primera vela: bajista
    if not is_bearish_candle(candle1):
        return False
    
    # Segunda vela: alcista
    if not is_bullish_candle(candle2):
        return False
    
    # La segunda vela debe envollar completamente a la primera
    return (
        candle2['open'] < candle1['close'] and  # abre por debajo del cierre anterior
        candle2['close'] > candle1['open']     # cierra por encima de la apertura anterior
    )


def is_bearish_engulfing(candle1, candle2):
    """
    Patrón Envolvente Bajista (Bearish Engulfing):
    Una vela alcista pequeña seguida por una vela bajista grande que la envuelve.
    Indica potencial reversión bajista.
    """
    # Primera vela: alcista
    if not is_bullish_candle(candle1):
        return False
    
    # Segunda vela: bajista
    if not is_bearish_candle(candle2):
        return False
    
    # La segunda vela debe envollar completamente a la primera
    return (
        candle2['open'] > candle1['close'] and  # abre por encima del cierre anterior
        candle2['close'] < candle1['open']       # cierra por debajo de la apertura anterior
    )


def is_morning_star(candles):
    """
    Patrón Estrella de la Mañana (Morning Star):
    3 velas: una vela bajista, una vela pequeña (doji/estrella), una vela alcista.
    Indica reversión alcista fuerte.
    """
    if len(candles) < 3:
        return False
    
    candle1, candle2, candle3 = candles[-3], candles[-2], candles[-1]
    
    # Primera vela: bajista grande
    if not is_bearish_candle(candle1):
        return False
    
    # Segunda vela: cuerpo pequeño (doji o estrella)
    body2 = get_body_size(candle2)
    range2 = get_full_range(candle2)
    if range2 == 0:
        return False
    
    body_ratio2 = body2 / range2
    if body_ratio2 > 0.5:  # cuerpo no es pequeño
        return False
    
    # Tercera vela: alcista grande que cierra dentro de la primera
    if not is_bullish_candle(candle3):
        return False
    
    # La tercera vela debe cerrar al menos a la mitad de la primera
    return candle3['close'] > (candle1['open'] + candle1['close']) / 2


def is_evening_star(candles):
    """
    Patrón Estrella de la Tarde (Evening Star):
    3 velas: una vela alcista, una vela pequeña (doji/estrella), una vela bajista.
    Indica reversión bajista fuerte.
    """
    if len(candles) < 3:
        return False
    
    candle1, candle2, candle3 = candles[-3], candles[-2], candles[-1]
    
    # Primera vela: alcista grande
    if not is_bullish_candle(candle1):
        return False
    
    # Segunda vela: cuerpo pequeño
    body2 = get_body_size(candle2)
    range2 = get_full_range(candle2)
    if range2 == 0:
        return False
    
    body_ratio2 = body2 / range2
    if body_ratio2 > 0.5:
        return False
    
    # Tercera vela: bajista grande
    if not is_bearish_candle(candle3):
        return False
    
    # La tercera vela debe cerrar al menos a la mitad de la primera
    return candle3['close'] < (candle1['open'] + candle1['close']) / 2


def is_doji(candle):
    """
    Patrón Doji: Vela donde apertura y cierre son casi iguales.
    Indica indecisión en el mercado.
    """
    body_size = get_body_size(candle)
    full_range = get_full_range(candle)
    
    if full_range == 0:
        return False
    
    # El cuerpo es muy pequeño respecto al rango
    return body_size / full_range <= 0.1


def is_three_white_soldiers(candles):
    """
    Patrón Tres Soldados Blancos (Three White Soldiers):
    3 velas alcistas consecutivas con cuerpos grandes y sombras pequeñas.
    Indica continuación alcista.
    """
    if len(candles) < 3:
        return False
    
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    
    # Todas deben ser alcistas
    if not (is_bullish_candle(c1) and is_bullish_candle(c2) and is_bullish_candle(c3)):
        return False
    
    # Cada cierre debe ser mayor que el anterior
    if not (c2['close'] > c1['close'] and c3['close'] > c2['close']):
        return False
    
    # Cuerpos grandes (al menos 70% del rango)
    for c in [c1, c2, c3]:
        body_size = get_body_size(c)
        full_range = get_full_range(c)
        if full_range > 0 and body_size / full_range < 0.7:
            return False
    
    return True


def is_three_black_crows(candles):
    """
    Patrón Tres Cuervos Negros (Three Black Crows):
    3 velas bajistas consecutivas con cuerpos grandes y sombras pequeñas.
    Indica continuación bajista.
    """
    if len(candles) < 3:
        return False
    
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    
    # Todas deben ser bajistas
    if not (is_bearish_candle(c1) and is_bearish_candle(c2) and is_bearish_candle(c3)):
        return False
    
    # Cada cierre debe ser menor que el anterior
    if not (c2['close'] < c1['close'] and c3['close'] < c2['close']):
        return False
    
    # Cuerpos grandes
    for c in [c1, c2, c3]:
        body_size = get_body_size(c)
        full_range = get_full_range(c)
        if full_range > 0 and body_size / full_range < 0.7:
            return False
    
    return True


def analyze_patterns(candles):
    """
    Analiza los últimos patrones de velas y devuelve señales.
    
    Args:
        candles: Lista de diccionarios con datos de velas
    
    Returns:
        dict: Señales de compra y venta con nivel de confianza
    """
    if len(candles) < 3:
        return {"buy": 0, "sell": 0, "pattern": "insufficient_data"}
    
    buy_signals = 0
    sell_signals = 0
    patterns_found = []
    
    current = candles[-1]
    prev = candles[-2]
    
    # Patrones de reversión alcista
    if is_hammer(current):
        buy_signals += 2
        patterns_found.append("hammer")
    
    if is_inverted_hammer(current):
        buy_signals += 1
        patterns_found.append("inverted_hammer")
    
    if is_bullish_engulfing(prev, current):
        buy_signals += 3
        patterns_found.append("bullish_engulfing")
    
    if is_morning_star(candles):
        buy_signals += 4
        patterns_found.append("morning_star")
    
    # Patrones de continuación alcista
    if is_three_white_soldiers(candles):
        buy_signals += 3
        patterns_found.append("three_white_soldiers")
    
    # Patrones de reversión bajista
    if is_shooting_star(current):
        sell_signals += 2
        patterns_found.append("shooting_star")
    
    if is_bearish_engulfing(prev, current):
        sell_signals += 3
        patterns_found.append("bearish_engulfing")
    
    if is_evening_star(candles):
        sell_signals += 4
        patterns_found.append("evening_star")
    
    # Patrones de continuación bajista
    if is_three_black_crows(candles):
        sell_signals += 3
        patterns_found.append("three_black_crows")
    
    # Análisis de momentum reciente
    recent_bullish = sum(1 for c in candles[-3:] if is_bullish_candle(c))
    recent_bearish = sum(1 for c in candles[-3:] if is_bearish_candle(c))
    
    if recent_bullish >= 3:
        buy_signals += 1
        patterns_found.append("recent_uptrend")
    
    if recent_bearish >= 3:
        sell_signals += 1
        patterns_found.append("recent_downtrend")
    
    pattern_name = ", ".join(patterns_found) if patterns_found else "no_pattern"
    
    return {
        "buy": buy_signals,
        "sell": sell_signals,
        "pattern": pattern_name,
        "current_type": "bullish" if is_bullish_candle(current) else "bearish"
    }


def get_signal(analysis, threshold=2):
    """
    Determina la señal de trading basada en el análisis de patrones.
    
    Args:
        analysis: Resultado de analyze_patterns
        threshold: Umbral mínimo de señales para ejecutar
    
    Returns:
        str: 'buy', 'sell' o 'none'
    """
    if analysis["pattern"] == "insufficient_data":
        return "none"
    
    # Si hay más señales de compra que de venta y supera el umbral
    if analysis["buy"] >= threshold and analysis["buy"] > analysis["sell"]:
        return "buy"
    
    # Si hay más señales de venta que de compra y supera el umbral
    if analysis["sell"] >= threshold and analysis["sell"] > analysis["buy"]:
        return "sell"
    
    return "none"


async def get_historical_candles(asset, count=20):
    """
    Obtiene datos históricos de velas.
    """
    try:
        end_time = time.time()
        period = TRADING_CONFIG["period"]
        
        candles_data = await client.get_candles(
            asset=asset,
            end_from_time=end_time,
            offset=0,
            period=period,
            progressive=False
        )
        
        if candles_data and len(candles_data) > 0:
            return candles_data[-count:]
        
        return []
    except Exception as e:
        print(f"Error al obtener velas: {e}")
        return []


async def execute_trade(direction, asset, amount, duration):
    """
    Ejecuta una operación de trading.
    """
    try:
        if direction == 'buy':
            check, balance = await client.buy(
                amount=amount,
                asset=asset,
                duration=duration,
                mode="manual"
            )
        else:
            check, balance = await client.sell(
                amount=amount,
                asset=asset,
                duration=duration,
                mode="manual"
            )
        
        return {"success": check, "balance": balance}
    except Exception as e:
        print(f"Error al ejecutar operación: {e}")
        return {"success": False, "balance": 0}


async def run_strategy():
    """
    Ejecuta la estrategia de Patrones de Velas.
    """
    asset = TRADING_CONFIG["asset"]
    amount = TRADING_CONFIG["amount"]
    duration = TRADING_CONFIG["duration"]
    period = TRADING_CONFIG["period"]
    lookback = TRADING_CONFIG["lookback_candles"]
    
    print(f"Iniciando estrategia de Patrones de Velas")
    print(f"Activo: {asset}")
    print(f"Inversión: ${amount}")
    print(f"Duración: {duration}s")
    print("-" * 50)
    
    # Conectar al servidor
    check, reason = await client.connect()
    
    if not check:
        print(f"Error de conexión: {reason}")
        return
    
    print("Conectado exitosamente")
    
    # Obtener balance inicial
    balance = await client.get_balance()
    TRADING_CONFIG["balance"] = balance
    print(f"Balance inicial: ${balance:.2f}")
    print("-" * 50)
    
    last_trade_time = 0
    cooldown = 30  # segundos entre operaciones
    
    try:
        while True:
            current_time = time.time()
            
            # Verificar cooldown
            if current_time - last_trade_time < cooldown:
                await asyncio.sleep(5)
                continue
            
            # Obtener datos históricos
            candles = await get_historical_candles(asset, lookback + 5)
            
            if len(candles) < 5:
                print("No hay suficientes datos de velas")
                await asyncio.sleep(10)
                continue
            
            # Convertir formato de velas
            formatted_candles = []
            for candle in candles:
                if isinstance(candle, dict):
                    formatted_candles.append({
                        'open': candle.get('open', candle.get('open', 0)),
                        'close': candle.get('close', candle.get('close', 0)),
                        'high': candle.get('high', candle.get('max', 0)),
                        'low': candle.get('low', candle.get('min', 0)),
                    })
                elif hasattr(candle, 'candle_close'):
                    formatted_candles.append({
                        'open': candle.candle_open,
                        'close': candle.candle_close,
                        'high': candle.candle_high,
                        'low': candle.candle_low,
                    })
            
            if not formatted_candles:
                await asyncio.sleep(5)
                continue
            
            # Analizar patrones
            analysis = analyze_patterns(formatted_candles)
            
            # Obtener precio actual
            current_price = formatted_candles[-1]['close']
            
            print(f"\nPrecio actual: {current_price:.5f}")
            print(f"Vela actual: {analysis['current_type']}")
            print(f"Patrones detectados: {analysis['pattern']}")
            print(f"Señales - Compra: {analysis['buy']}, Venta: {analysis['sell']}")
            
            # Obtener señal
            signal = get_signal(analysis)
            print(f"Señal: {signal.upper()}")
            
            # Ejecutar operación si hay señal
            if signal != 'none':
                print(f"\nEjecutando operación {signal.upper()}...")
                
                result = await execute_trade(signal, asset, amount, duration)
                
                if result["success"]:
                    last_trade_time = current_time
                    TRADING_CONFIG["trades"] += 1
                    
                    # Actualizar balance
                    new_balance = await client.get_balance()
                    profit = new_balance - TRADING_CONFIG["balance"]
                    
                    if profit > 0:
                        TRADING_CONFIG["wins"] += 1
                        TRADING_CONFIG["profit"] += profit
                        print(f"✅ Operación GANADORA! +${profit:.2f}")
                    else:
                        TRADING_CONFIG["losses"] += 1
                        TRADING_CONFIG["profit"] += profit
                        print(f"❌ Operación PERDEDORA! ${profit:.2f}")
                    
                    TRADING_CONFIG["balance"] = new_balance
                else:
                    print("❌ Error en la operación")
            
            # Mostrar estadísticas
            print(f"\nEstadísticas:")
            print(f"  Operaciones: {TRADING_CONFIG['trades']}")
            print(f"  Ganadas: {TRADING_CONFIG['wins']}")
            print(f"  Perdidas: {TRADING_CONFIG['losses']}")
            print(f"  Balance: ${TRADING_CONFIG['balance']:.2f}")
            print("-" * 50)
            
            # Esperar antes del siguiente análisis
            await asyncio.sleep(period)
            
    except KeyboardInterrupt:
        print("\n\nEstrategia detenida por el usuario")
    except Exception as e:
        print(f"\nError en la estrategia: {e}")
    finally:
        await client.disconnect()
        print("\nDesconectado")


async def main():
    """Función principal."""
    await run_strategy()


if __name__ == "__main__":
    asyncio.run(main())
