# Fases de la Luna Bot - Estrategia de Ciclos Lunares
# Utiliza el calendario lunar como confirmación
# Busca posiciones alcistas durante Luna Nueva y bajistas durante Luna Llena

import asyncio
import math
import time
from datetime import datetime, timezone
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
    "period": 60,
    "lookback_candles": 50,
    "use_moon_confirmation": True,  # Usar fases lunares como filtro
    "wins": 0,
    "losses": 0,
    "trades": 0,
    "profit": 0.0,
    "balance": 0.0,
}


# Constantes para el cálculo de fases lunares
LUNAR_CYCLE = 29.530588853  # Días lunares


def get_moon_phase(date=None):
    """
    Calcula la fase lunar actual.
    
    Returns:
        dict: Fase lunar con nombre, iluminación y días hasta siguiente fase
    """
    if date is None:
        date = datetime.now(timezone.utc)
    
    # Fecha de referencia: Luna nueva conocida (6 de enero de 2000)
    reference_new_moon = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    
    # Calcular días desde la luna nueva de referencia
    days_since_reference = (date - reference_new_moon).total_seconds() / 86400
    
    # Posición en el ciclo lunar
    lunar_age = days_since_reference % LUNAR_CYCLE
    
    # Calcular iluminación (0% = luna nueva, 100% = luna llena)
    illumination = (1 - math.cos(2 * math.pi * lunar_age / LUNAR_CYCLE)) / 2 * 100
    
    # Determinar fase
    if lunar_age < 1.84566:  # Luna nueva
        phase_name = "new_moon"
        signal = "buy"
    elif lunar_age < 5.53699:  # Luna creciente menguante
        phase_name = "waxing_crescent"
        signal = "buy"
    elif lunar_age < 9.22831:  # Cuarto creciente
        phase_name = "first_quarter"
        signal = "buy"
    elif lunar_age < 12.91963:  # Luna gibosa creciente
        phase_name = "waxing_gibbous"
        signal = "buy"
    elif lunar_age < 16.61096:  # Luna llena
        phase_name = "full_moon"
        signal = "sell"
    elif lunar_age < 20.30228:  # Luna gibosa menguante
        phase_name = "waning_gibbous"
        signal = "sell"
    elif lunar_age < 23.99361:  # Cuarto menguante
        phase_name = "last_quarter"
        signal = "sell"
    elif lunar_age < 27.68493:  # Luna menguante
        phase_name = "waning_crescent"
        signal = "sell"
    else:
        phase_name = "new_moon"
        signal = "buy"
    
    # Días hasta siguiente luna nueva
    days_to_new_moon = LUNAR_CYCLE - lunar_age
    
    return {
        "phase_name": phase_name,
        "lunar_age": lunar_age,
        "illumination": illumination,
        "signal": signal,
        "days_to_new_moon": days_to_new_moon,
        "date": date.isoformat()
    }


def get_moon_phase_name(phase):
    """Traduce el nombre de la fase al español."""
    names = {
        "new_moon": "Luna Nueva 🌑",
        "waxing_crescent": "Luna Creciente Menguante 🌒",
        "first_quarter": "Cuarto Creciente 🌓",
        "waxing_gibbous": "Luna Gibosa Creciente 🌔",
        "full_moon": "Luna Llena 🌕",
        "waning_gibbous": "Luna Gibosa Menguante 🌖",
        "last_quarter": "Cuarto Menguante 🌗",
        "waning_crescent": "Luna Menguante 🌘"
    }
    return names.get(phase, phase)


def is_strong_moon_signal(moon_info):
    """
    Determina si la señal lunar es fuerte (cerca de luna nueva o luna llena).
    
    Args:
        moon_info: Información de la fase lunar
    
    Returns:
        bool: True si la señal es fuerte
    """
    lunar_age = moon_info["lunar_age"]
    illumination = moon_info["illumination"]
    
    # Señales fuertes cerca de luna nueva (< 2 días) o luna llena (< 2 días)
    is_near_new_moon = lunar_age < 2 or lunar_age > LUNAR_CYCLE - 2
    is_near_full_moon = 13 < lunar_age < 17
    
    return is_near_new_moon or is_near_full_moon


def calculate_price_direction(candles):
    """
    Calcula la dirección general del precio.
    
    Args:
        candles: Lista de velas
    
    Returns:
        str: 'up', 'down' o 'neutral'
    """
    if len(candles) < 2:
        return "neutral"
    
    # Usar los últimos precios de cierre
    closes = [c['close'] for c in candles]
    
    # Calcular tendencia simple
    first_half_avg = sum(closes[:len(closes)//2]) / (len(closes)//2)
    second_half_avg = sum(closes[len(closes)//2:]) / (len(closes) - len(closes)//2)
    
    diff_percent = (second_half_avg - first_half_avg) / first_half_avg * 100
    
    if diff_percent > 0.5:
        return "up"
    elif diff_percent < -0.5:
        return "down"
    else:
        return "neutral"


def get_signal(moon_info, price_direction):
    """
    Genera señal de trading combinada (fase lunar + dirección del precio).
    
    Args:
        moon_info: Información de la fase lunar
        price_direction: Dirección del precio
    
    Returns:
        str: 'buy', 'sell' o 'none'
    """
    moon_signal = moon_info["signal"]
    strong_signal = is_strong_moon_signal(moon_info)
    
    # Si la señal lunar es fuerte, usarla
    if strong_signal:
        return moon_signal
    
    # Si no es señal fuerte, combinar con dirección del precio
    # Solo operar si hay confirmación
    if not TRADING_CONFIG["use_moon_confirmation"]:
        return price_direction
    
    # Luna nueva o cuarto creciente + precio subiendo = compra
    if moon_signal == "buy" and price_direction == "up":
        return "buy"
    
    # Luna llena o cuarto menguante + precio bajando = venta
    if moon_signal == "sell" and price_direction == "down":
        return "sell"
    
    # En caso contrario, no operar
    return "none"


async def get_historical_candles(asset, count=50):
    """Obtiene datos históricos de velas."""
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
    """Ejecuta una operación de trading."""
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
    """Ejecuta la estrategia de Fases de la Luna."""
    asset = TRADING_CONFIG["asset"]
    amount = TRADING_CONFIG["amount"]
    duration = TRADING_CONFIG["duration"]
    period = TRADING_CONFIG["period"]
    lookback = TRADING_CONFIG["lookback_candles"]
    
    print(f"Iniciando estrategia de Fases de la Luna")
    print(f"Activo: {asset}")
    print(f"Inversión: ${amount}")
    print(f"Duración: {duration}s")
    print(f"Confirmación lunar: {TRADING_CONFIG['use_moon_confirmation']}")
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
            
            # Obtener información lunar actual
            moon_info = get_moon_phase()
            
            # Obtener datos de precios
            candles = await get_historical_candles(asset, lookback)
            
            if len(candles) < 10:
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
            
            # Calcular dirección del precio
            price_direction = calculate_price_direction(formatted_candles)
            
            # Obtener precio actual
            current_price = formatted_candles[-1]['close']
            
            # Obtener señal combinada
            signal = get_signal(moon_info, price_direction)
            
            # Mostrar información
            print(f"\n{'='*50}")
            print(f"Fecha: {moon_info['date']}")
            print(f"Fase Lunar: {get_moon_phase_name(moon_info['phase_name'])}")
            print(f"Iluminación: {moon_info['illumination']:.1f}%")
            print(f"Días hasta Luna Nueva: {moon_info['days_to_new_moon']:.1f}")
            print(f"Señal Lunar: {moon_info['signal'].upper()}")
            print(f"Señal Fuerte: {'SÍ' if is_strong_moon_signal(moon_info) else 'NO'}")
            print(f"{'='*50}")
            print(f"Precio actual: {current_price:.5f}")
            print(f"Dirección del precio: {price_direction.upper()}")
            print(f"Señal combinada: {signal.upper()}")
            
            # Ejecutar operación si hay señal
            if signal != 'none':
                print(f"\nEjecutando operación {signal.upper()}...")
                
                result_trade = await execute_trade(signal, asset, amount, duration)
                
                if result_trade["success"]:
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
