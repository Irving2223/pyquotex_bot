# Soporte y Resistencia Bot - Estrategia de Soportes y Resistencias
# Identifica niveles horizontales donde el precio ha rebotado antes
# Compra si el nivel está por debajo (soporte), Vende si está por encima (resistencia)
# clave de luisa chavez 

import asyncio
import time
from collections import defaultdict
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
    "lookback_candles": 100,  # número de velas para buscar niveles
    "tolerance": 0.0002,  # tolerancia para considerar un nivel como soporte/resistencia
    "min_touches": 2,  # mínimo de toques para confirmar un nivel
    "wins": 0,
    "losses": 0,
    "trades": 0,
    "profit": 0.0,
    "balance": 0.0,
}


def find_support_resistance_levels(candles):
    """
    Encuentra niveles de soporte y resistencia en datos históricos de velas.
    
    Un soporte se identifica cuando el precio baja pero no supera un nivel anterior.
    Una resistencia se identifica cuando el precio sube pero no supera un nivel Args:
        candles anterior.
    
   : Lista de diccionarios con datos de velas (open, close, high, low)
    
    Returns:
        tuple: (soportes, resistencias) - listas de niveles de precio
    """
    if len(candles) < TRADING_CONFIG["min_touches"]:
        return [], []
    
    highs = [candle['high'] for candle in candles]
    lows = [candle['low'] for candle in candles]
    closes = [candle['close'] for candle in candles]
    
    # Encontrar picos locales (potenciales resistencias)
    resistance_levels = []
    for i in range(1, len(candles) - 1):
        # Es resistencia si el alto es mayor que los vecinos
        if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
            resistance_levels.append(highs[i])
    
    # Encontrar valles locales (potenciales soportes)
    support_levels = []
    for i in range(1, len(candles) - 1):
        # Es soporte si el bajo es menor que los vecinos
        if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
            support_levels.append(lows[i])
    
    # Agrupar niveles similares (dentro de la tolerancia)
    tolerance = TRADING_CONFIG["tolerance"]
    
    def cluster_levels(levels):
        """Agrupa niveles similares en clusters."""
        if not levels:
            return []
        
        levels = sorted(levels)
        clusters = []
        current_cluster = [levels[0]]
        
        for i in range(1, len(levels)):
            # Si el nivel actual está dentro de la tolerancia del anterior
            if abs(levels[i] - current_cluster[-1]) / current_cluster[-1] < tolerance:
                current_cluster.append(levels[i])
            else:
                # Cerrar cluster actual y empezar uno nuevo
                clusters.append(current_cluster)
                current_cluster = [levels[i]]
        
        clusters.append(current_cluster)
        
        # Filtrar clusters que tienen el mínimo de toques
        valid_levels = []
        for cluster in clusters:
            if len(cluster) >= TRADING_CONFIG["min_touches"]:
                # Usar el promedio del cluster como nivel
                valid_levels.append(sum(cluster) / len(cluster))
        
        return valid_levels
    
    support_levels = cluster_levels(support_levels)
    resistance_levels = cluster_levels(resistance_levels)
    
    return support_levels, resistance_levels


def get_current_signal(current_price, supports, resistances):
    """
    Determina la señal de trading basada en niveles de soporte y resistencia.
    
    Args:
        current_price: Precio actual
        supports: Lista de niveles de soporte
        resistances: Lista de niveles de resistencia
    
    Returns:
        str: 'buy', 'sell' o 'none'
    """
    if not supports and not resistances:
        return 'none'
    
    tolerance = TRADING_CONFIG["tolerance"]
    
    # Buscar si el precio está cerca de un soporte (para comprar)
    for support in supports:
        # Si el precio está ligeramente por encima del soporte (dentro de tolerancia)
        if 0 <= (current_price - support) / support <= tolerance * 2:
            return 'buy'
    
    # Buscar si el precio está cerca de una resistencia (para vender)
    for resistance in resistances:
        # Si el precio está ligeramente por debajo de la resistencia
        if 0 <= (resistance - current_price) / resistance <= tolerance * 2:
            return 'sell'
    
    return 'none'


async def get_historical_candles(asset, count=100):
    """
    Obtiene datos históricos de velas.
    
    Args:
        asset: Nombre del activo
        count: Número de velas a obtener
    
    Returns:
        list: Lista de diccionarios con datos de velas
    """
    try:
        # Usar get_candles para obtener datos históricos
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
            # Tomar las últimas 'count' velas
            return candles_data[-count:]
        
        return []
    except Exception as e:
        print(f"Error al obtener velas: {e}")
        return []


async def execute_trade(direction, asset, amount, duration):
    """
    Ejecuta una operación de trading.
    
    Args:
        direction: 'buy' o 'sell'
        asset: Nombre del activo
        amount: Cantidad a invertir
        duration: Duración de la opción en segundos
    
    Returns:
        dict: Resultado de la operación
    """
    try:
        if direction == 'buy':
            # Compra = opción CALL (subida)
            check, balance = await client.buy(
                amount=amount,
                asset=asset,
                duration=duration,
                mode="manual"
            )
        else:
            # Venta = opción PUT (bajada)
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
    Ejecuta la estrategia de Soportes y Resistencias.
    """
    asset = TRADING_CONFIG["asset"]
    amount = TRADING_CONFIG["amount"]
    duration = TRADING_CONFIG["duration"]
    period = TRADING_CONFIG["period"]
    lookback = TRADING_CONFIG["lookback_candles"]
    
    print(f"Iniciando estrategia de Soportes y Resistencias")
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
    
    # Variables para control de operaciones
    last_trade_time = 0
    cooldown = 30  # segundos entre operaciones
    
    try:
        while True:
            current_time = time.time()
            
            # Verificar si podemos operar (cooldown)
            if current_time - last_trade_time < cooldown:
                await asyncio.sleep(5)
                continue
            
            # Obtener datos históricos
            candles = await get_historical_candles(asset, lookback)
            
            if len(candles) < 20:
                print("No hay suficientes datos de velas")
                await asyncio.sleep(10)
                continue
            
            # Convertir formato de velas si es necesario
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
                    # Es un objeto de vela
                    formatted_candles.append({
                        'open': candle.candle_open,
                        'close': candle.candle_close,
                        'high': candle.candle_high,
                        'low': candle.candle_low,
                    })
            
            if not formatted_candles:
                await asyncio.sleep(5)
                continue
            
            # Encontrar niveles de soporte y resistencia
            supports, resistances = find_support_resistance_levels(formatted_candles)
            
            # Obtener precio actual
            current_price = formatted_candles[-1]['close']
            
            print(f"\nPrecio actual: {current_price:.5f}")
            print(f"Soportes encontrados: {len(supports)} - {supports[:3] if supports else 'None'}")
            print(f"Resistencias encontradas: {len(resistances)} - {resistences[:3] if resistances else 'None'}")
            
            # Obtener señal
            signal = get_current_signal(current_price, supports, resistances)
            
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
                        print(f"❌ Operacion PERDEDORA! ${profit:.2f}")
                    
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
        # Desconectar
        await client.disconnect()
        print("\nDesconectado")


async def main():
    """Función principal."""
    await run_strategy()


if __name__ == "__main__":
    asyncio.run(main())
