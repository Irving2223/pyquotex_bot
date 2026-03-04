# Gráficos Renko Bot - Estrategia Renko
# Configura bloques basados en el cambio porcentual del precio
# Filtra el ruido del mercado
# Opera al alza con bloques verdes y a la baja con rojos

import asyncio
import time
from collections import deque
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
    "period": 60,  # período de la vela en segundos (para obtener datos)
    "brick_size_percent": 0.5,  # tamaño del ladrillo en porcentaje (0.5% = 0.005)
    "lookback_candles": 100,  # número de velas para construir el gráfico Renko
    "trend_lookback": 5,  # número de ladrillos para determinar tendencia
    "wins": 0,
    "losses": 0,
    "trades": 0,
    "profit": 0.0,
    "balance": 0.0,
}


class RenkoBrick:
    """
    Representa un ladrillo (bloque) Renko.
    """
    def __init__(self, open_price, close_price, timestamp=None):
        self.open = open_price
        self.close = close_price
        self.timestamp = timestamp or time.time()
        self.is_bullish = close_price > open_price
    
    @property
    def color(self):
        return "green" if self.is_bullish else "red"
    
    def __repr__(self):
        return f"Renko({self.color}: {self.open:.5f} -> {self.close:.5f})"


class RenkoChart:
    """
    Gestor del gráfico Renko.
    """
    def __init__(self, brick_size_percent):
        self.brick_size_percent = brick_size_percent
        self.bricks = []
        self.current_price = None
        self.last_brick = None
    
    def calculate_brick_size(self, price):
        """Calcula el tamaño del ladrillo basado en el precio actual."""
        return price * (self.brick_size_percent / 100)
    
    def add_price(self, price, timestamp=None):
        """
        Agrega un nuevo precio y genera nuevos ladrillos si es necesario.
        
        Returns:
            list: Nuevos ladrillos generados
        """
        self.current_price = price
        new_bricks = []
        
        if not self.last_brick:
            # Primer ladrillo
            brick_size = self.calculate_brick_size(price)
            new_brick = RenkoBrick(price - brick_size/2, price + brick_size/2, timestamp)
            self.bricks.append(new_brick)
            self.last_brick = new_brick
            return new_bricks
        
        brick_size = self.calculate_brick_size(self.last_brick.close)
        
        # Determinar dirección del movimiento
        if price >= self.last_brick.close + brick_size:
            # Precio sube - generar ladrillo verde
            new_brick = RenkoBrick(
                self.last_brick.close,
                self.last_brick.close + brick_size,
                timestamp
            )
            self.bricks.append(new_brick)
            self.last_brick = new_brick
            new_bricks.append(new_brick)
            
            # Posibles ladrillos adicionales si el movimiento es muy grande
            while self.current_price >= self.last_brick.close + brick_size:
                new_brick = RenkoBrick(
                    self.last_brick.close,
                    self.last_brick.close + brick_size,
                    timestamp
                )
                self.bricks.append(new_brick)
                self.last_brick = new_brick
                new_bricks.append(new_brick)
        
        elif price <= self.last_brick.close - brick_size:
            # Precio baja - generar ladrillo rojo
            new_brick = RenkoBrick(
                self.last_brick.close,
                self.last_brick.close - brick_size,
                timestamp
            )
            self.bricks.append(new_brick)
            self.last_brick = new_brick
            new_bricks.append(new_brick)
            
            # Posibles ladrillos adicionales
            while self.current_price <= self.last_brick.close - brick_size:
                new_brick = RenkoBrick(
                    self.last_brick.close,
                    self.last_brick.close - brick_size,
                    timestamp
                )
                self.bricks.append(new_brick)
                self.last_brick = new_brick
                new_bricks.append(new_brick)
        
        return new_bricks
    
    def get_trend(self, lookback=5):
        """
        Determina la tendencia basada en los últimos ladrillos.
        
        Returns:
            str: 'up', 'down' o 'neutral'
        """
        if len(self.bricks) < lookback:
            return "neutral"
        
        recent_bricks = self.bricks[-lookback:]
        
        # Contar bricks verdes y rojos
        green = sum(1 for b in recent_bricks if b.is_bullish)
        red = sum(1 for b in recent_bricks if not b.is_bullish)
        
        if green > red * 2:
            return "up"
        elif red > green * 2:
            return "down"
        else:
            return "neutral"
    
    def get_last_bricks(self, count=3):
        """Obtiene los últimos N ladrillos."""
        return self.bricks[-count:] if len(self.bricks) >= count else self.bricks
    
    def detect_reversal(self):
        """
        Detecta reversión de tendencia.
        
        Returns:
            str: 'buy', 'sell' o 'none'
        """
        if len(self.bricks) < 3:
            return "none"
        
        last_3 = self.bricks[-3:]
        
        # Reversión alcista: rojo -> rojo -> verde
        if (not last_3[0].is_bullish and 
            not last_3[1].is_bullish and 
            last_3[2].is_bullish):
            return "buy"
        
        # Reversión bajista: verde -> verde -> rojo
        if (last_3[0].is_bullish and 
            last_3[1].is_bullish and 
            not last_3[2].is_bullish):
            return "sell"
        
        return "none"


def build_renko_from_candles(candles, brick_size_percent):
    """
    Construye un gráfico Renko a partir de datos de velas.
    
    Args:
        candles: Lista de velas con datos de precios
        brick_size_percent: Tamaño del ladrillo en porcentaje
    
    Returns:
        RenkoChart: Gráfico Renko construido
    """
    renko = RenkoChart(brick_size_percent)
    
    for i, candle in enumerate(candles):
        # Usar el precio de cierre de cada vela
        price = candle['close']
        timestamp = candle.get('timestamp', i)
        
        # Para la primera vela, inicializar
        if len(renko.bricks) == 0:
            renko.current_price = price
            brick_size = renko.calculate_brick_size(price)
            # Crear primer ladrillo centrado en el precio
            renko.last_brick = RenkoBrick(price - brick_size/2, price + brick_size/2, timestamp)
            renko.bricks.append(renko.last_brick)
        else:
            renko.add_price(price, timestamp)
    
    return renko


def get_signal(renko):
    """
    Genera señal de trading basada en el gráfico Renko.
    
    Args:
        renko: Gráfico Renko
    
    Returns:
        str: 'buy', 'sell' o 'none'
    """
    if len(renko.bricks) < 3:
        return "none"
    
    trend = renko.get_trend(TRADING_CONFIG["trend_lookback"])
    reversal = renko.detect_reversal()
    
    # Si hay reversión clara, usarla
    if reversal != "none":
        return reversal
    
    # Otherwise, seguir la tendencia
    if trend == "up":
        return "buy"
    elif trend == "down":
        return "sell"
    
    return "none"


async def get_historical_candles(asset, count=200):
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
    Ejecuta la estrategia de Gráficos Renko.
    """
    asset = TRADING_CONFIG["asset"]
    amount = TRADING_CONFIG["amount"]
    duration = TRADING_CONFIG["duration"]
    period = TRADING_CONFIG["period"]
    lookback = TRADING_CONFIG["lookback_candles"]
    brick_percent = TRADING_CONFIG["brick_size_percent"]
    
    print(f"Iniciando estrategia de Gráficos Renko")
    print(f"Activo: {asset}")
    print(f"Inversión: ${amount}")
    print(f"Duración: {duration}s")
    print(f"Tamaño del ladrillo: {brick_percent}%")
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
    
    # Construir gráfico Renko inicial
    candles = await get_historical_candles(asset, lookback)
    
    if not candles:
        print("No se pudieron obtener datos históricos")
        await client.disconnect()
        return
    
    # Convertir formato de velas
    formatted_candles = []
    for i, candle in enumerate(candles):
        if isinstance(candle, dict):
            formatted_candles.append({
                'open': candle.get('open', candle.get('open', 0)),
                'close': candle.get('close', candle.get('close', 0)),
                'high': candle.get('high', candle.get('max', 0)),
                'low': candle.get('low', candle.get('min', 0)),
                'timestamp': i,
            })
        elif hasattr(candle, 'candle_close'):
            formatted_candles.append({
                'open': candle.candle_open,
                'close': candle.candle_close,
                'high': candle.candle_high,
                'low': candle.candle_low,
                'timestamp': i,
            })
    
    renko = build_renko_from_candles(formatted_candles, brick_percent)
    
    print(f"Gráfico Renko construido con {len(renko.bricks)} ladrillos")
    print(f"Tendencia actual: {renko.get_trend(TRADING_CONFIG['trend_lookback'])}")
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
            
            # Obtener última vela
            recent_candles = await get_historical_candles(asset, 2)
            
            if not recent_candles:
                await asyncio.sleep(5)
                continue
            
            # Convertir última vela
            last_candle = recent_candles[-1]
            if isinstance(last_candle, dict):
                current_price = last_candle.get('close', 0)
            else:
                current_price = last_candle.candle_close
            
            # Agregar nuevo precio al gráfico Renko
            renko.add_price(current_price)
            
            # Obtener información
            trend = renko.get_trend(TRADING_CONFIG["trend_lookback"])
            reversal = renko.detect_reversal()
            last_bricks = renko.get_last_bricks(3)
            
            print(f"\nPrecio actual: {current_price:.5f}")
            print(f"Tendencia Renko: {trend.upper()}")
            print(f"Reversión: {reversal if reversal != 'none' else 'ninguna'}")
            print(f"Últimos 3 ladrillos: {[b.color for b in last_bricks]}")
            
            # Generar señal
            signal = get_signal(renko)
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
            print(f"  Ladrillos totales: {len(renko.bricks)}")
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
