# Ondas de Elliot Bot - Estrategia de Ondas de Elliot
# Etiqueta una secuencia de cinco ondas de impulso (1-2-3-4-5)
# seguida de una correccion A-B-C para predecir el siguiente movimiento

import asyncio
import time
from enum import Enum
from pyquotex.config import credentials
from pyquotex.stable_api import Quotex

email, password = credentials()
client = Quotex(
    email=email,
    password=password,
    lang="es",
)

# Configuracion del trading
TRADING_CONFIG = {
    "amount": 10,
    "duration": 60,
    "asset": "EURUSD_otc",
    "period": 60,
    "lookback_candles": 200,
    "min_wave_size": 0.002,
    "wins": 0,
    "losses": 0,
    "trades": 0,
    "profit": 0.0,
    "balance": 0.0,
}


class WaveType(Enum):
    IMPULSE_1 = "1"
    IMPULSE_2 = "2"
    IMPULSE_3 = "3"
    IMPULSE_4 = "4"
    IMPULSE_5 = "5"
    CORRECTION_A = "A"
    CORRECTION_B = "B"
    CORRECTION_C = "C"
    NONE = "none"


class Wave:
    def __init__(self, wave_type, start_price, end_price, start_idx, end_idx):
        self.wave_type = wave_type
        self.start_price = start_price
        self.end_price = end_price
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.magnitude = abs(end_price - start_price)
        self.is_impulse = wave_type in [WaveType.IMPULSE_1, WaveType.IMPULSE_3, WaveType.IMPULSE_5]
        self.is_corrective = wave_type in [WaveType.CORRECTION_A, WaveType.CORRECTION_B, WaveType.CORRECTION_C]
    
    def __repr__(self):
        return f"Wave({self.wave_type.value}: {self.start_price:.5f} -> {self.end_price:.5f})"


class ElliottWaveAnalyzer:
    def __init__(self, min_wave_size):
        self.min_wave_size = min_wave_size
        self.waves = []
        self.prices = []
        self.indices = []
    
    def load_data(self, candles):
        self.prices = [c['close'] for c in candles]
        self.indices = list(range(len(candles)))
        self.waves = []
    
    def find_local_extrema(self, window=5):
        maxima = []
        minima = []
        
        for i in range(window, len(self.prices) - window):
            is_max = all(self.prices[i] > self.prices[i-j] for j in range(1, window+1)) and \
                     all(self.prices[i] > self.prices[i+j] for j in range(1, window+1))
            is_min = all(self.prices[i] < self.prices[i-j] for j in range(1, window+1)) and \
                     all(self.prices[i] < self.prices[i+j] for j in range(1, window+1))
            
            if is_max:
                maxima.append((i, self.prices[i]))
            elif is_min:
                minima.append((i, self.prices[i]))
        
        return maxima, minima
    
    def identify_waves(self):
        maxima, minima = self.find_local_extrema()
        
        if len(maxima) < 3 and len(minima) < 3:
            return []
        
        all_points = []
        for idx, price in maxima:
            all_points.append((idx, price, 'max'))
        for idx, price in minima:
            all_points.append((idx, price, 'min'))
        
        all_points.sort(key=lambda x: x[0])
        
        if len(all_points) < 5:
            return []
        
        waves = []
        
        # Onda 1
        for i in range(1, len(all_points)):
            diff = abs(all_points[i][1] - all_points[0][1])
            if diff >= self.min_wave_size:
                wave1 = Wave(WaveType.IMPULSE_1, all_points[0][1], all_points[i][1], 
                           all_points[0][0], all_points[i][0])
                waves.append(wave1)
                current_idx = i
                break
        
        if len(waves) == 0:
            return []
        
        # Onda 2
        wave1 = waves[0]
        for i in range(current_idx + 1, len(all_points)):
            if wave1.end_price > wave1.start_price:
                diff = wave1.end_price - all_points[i][1]
            else:
                diff = all_points[i][1] - wave1.end_price
            
            if diff >= self.min_wave_size * 0.5:
                wave2 = Wave(WaveType.IMPULSE_2, wave1.end_price, all_points[i][1],
                           wave1.end_idx, all_points[i][0])
                waves.append(wave2)
                current_idx = i
                break
        
        if len(waves) < 2:
            return []
        
        # Onda 3
        wave2 = waves[1]
        max_magnitude = 0
        max_idx = current_idx
        
        for i in range(current_idx + 1, len(all_points)):
            if wave1.end_price > wave1.start_price:
                diff = all_points[i][1] - wave2.end_price
            else:
                diff = wave2.end_price - all_points[i][1]
            
            if diff > max_magnitude:
                max_magnitude = diff
                max_idx = i
        
        if max_magnitude >= self.min_wave_size:
            wave3 = Wave(WaveType.IMPULSE_3, wave2.end_price, all_points[max_idx][1],
                        wave2.end_idx, all_points[max_idx][0])
            waves.append(wave3)
            current_idx = max_idx
        
        if len(waves) < 3:
            return []
        
        # Onda 4
        wave3 = waves[2]
        for i in range(current_idx + 1, len(all_points)):
            diff = abs(wave3.end_price - all_points[i][1])
            if diff >= self.min_wave_size * 0.382:
                wave4 = Wave(WaveType.IMPULSE_4, wave3.end_price, all_points[i][1],
                            wave3.end_idx, all_points[i][0])
                waves.append(wave4)
                current_idx = i
                break
        
        if len(waves) < 4:
            return []
        
        # Onda 5
        wave4 = waves[3]
        for i in range(current_idx + 1, len(all_points)):
            diff = abs(all_points[i][1] - wave4.end_price)
            if diff >= self.min_wave_size:
                wave5 = Wave(WaveType.IMPULSE_5, wave4.end_price, all_points[i][1],
                            wave4.end_idx, all_points[i][0])
                waves.append(wave5)
                current_idx = i
                break
        
        if len(waves) < 5:
            return []
        
        # Onda A
        wave5 = waves[4]
        for i in range(current_idx + 1, len(all_points)):
            diff = abs(wave5.end_price - all_points[i][1])
            if diff >= self.min_wave_size:
                waveA = Wave(WaveType.CORRECTION_A, wave5.end_price, all_points[i][1],
                            wave5.end_idx, all_points[i][0])
                waves.append(waveA)
                current_idx = i
                break
        
        if len(waves) < 6:
            return []
        
        # Onda B
        waveA = waves[5]
        for i in range(current_idx + 1, len(all_points)):
            diff = abs(waveA.end_price - all_points[i][1])
            if diff >= self.min_wave_size * 0.5:
                waveB = Wave(WaveType.CORRECTION_B, waveA.end_price, all_points[i][1],
                            waveA.end_idx, all_points[i][0])
                waves.append(waveB)
                current_idx = i
                break
        
        if len(waves) < 7:
            return []
        
        # Onda C
        waveB = waves[6]
        for i in range(current_idx + 1, len(all_points)):
            diff = abs(waveB.end_price - all_points[i][1])
            if diff >= self.min_wave_size:
                waveC = Wave(WaveType.CORRECTION_C, waveB.end_price, all_points[i][1],
                            waveB.end_idx, all_points[i][0])
                waves.append(waveC)
                break
        
        self.waves = waves
        return waves
    
    def get_current_phase(self):
        if not self.waves:
            return "unknown"
        return self.waves[-1].wave_type.value
    
    def predict_next_move(self):
        if len(self.waves) < 5:
            return "none"
        
        last_wave = self.waves[-1]
        
        # Onda 5 -> probabilidad de reversal
        if last_wave.wave_type == WaveType.IMPULSE_5:
            return "sell"
        
        # Onda 3 -> tendencia fuerte
        if last_wave.wave_type == WaveType.IMPULSE_3:
            wave1 = self.waves[0]
            return "buy" if wave1.end_price > wave1.start_price else "sell"
        
        # Onda 1 -> inicio de tendencia
        if last_wave.wave_type == WaveType.IMPULSE_1:
            return "buy" if last_wave.end_price > last_wave.start_price else "sell"
        
        # Onda 2 -> preparando para onda 3
        if last_wave.wave_type == WaveType.IMPULSE_2:
            wave1 = self.waves[0]
            return "buy" if wave1.end_price > wave1.start_price else "sell"
        
        # Onda 4 -> preparando para onda 5
        if last_wave.wave_type == WaveType.IMPULSE_4:
            wave3 = self.waves[2]
            return "buy" if wave3.end_price > wave3.start_price else "sell"
        
        # Correccion C -> nuevo ciclo
        if last_wave.wave_type == WaveType.CORRECTION_C:
            if len(self.waves) >= 5:
                wave1 = self.waves[0]
                return "buy" if wave1.end_price > wave1.start_price else "sell"
        
        return "none"
    
    def get_summary(self):
        if not self.waves:
            return "No se identificaron ondas"
        
        summary = "Ondas identificadas:\n"
        for wave in self.waves:
            summary += f"  Onda {wave.wave_type.value}: {wave.start_price:.5f} -> {wave.end_price:.5f}\n"
        return summary


async def get_historical_candles(asset, count=200):
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
        print(f"Error al ejecutar operacion: {e}")
        return {"success": False, "balance": 0}


async def run_strategy():
    asset = TRADING_CONFIG["asset"]
    amount = TRADING_CONFIG["amount"]
    duration = TRADING_CONFIG["duration"]
    period = TRADING_CONFIG["period"]
    lookback = TRADING_CONFIG["lookback_candles"]
    
    print(f"Iniciando estrategia de Ondas de Elliot")
    print(f"Activo: {asset}")
    print(f"Inversion: ${amount}")
    print(f"Duracion: {duration}s")
    print("-" * 50)
    
    check, reason = await client.connect()
    
    if not check:
        print(f"Error de conexion: {reason}")
        return
    
    print("Conectado exitosamente")
    
    balance = await client.get_balance()
    TRADING_CONFIG["balance"] = balance
    print(f"Balance inicial: ${balance:.2f}")
    print("-" * 50)
    
    last_trade_time = 0
    cooldown = 60
    
    try:
        while True:
            current_time = time.time()
            
            if current_time - last_trade_time < cooldown:
                await asyncio.sleep(10)
                continue
            
            candles = await get_historical_candles(asset, lookback)
            
            if len(candles) < 50:
                print("No hay suficientes datos de velas")
                await asyncio.sleep(20)
                continue
            
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
                await asyncio.sleep(10)
                continue
            
            analyzer = ElliottWaveAnalyzer(TRADING_CONFIG["min_wave_size"])
            analyzer.load_data(formatted_candles)
            waves = analyzer.identify_waves()
            current_phase = analyzer.get_current_phase()
            prediction = analyzer.predict_next_move()
            summary = analyzer.get_summary()
            
            current_price = formatted_candles[-1]['close']
            
            print(f"\nPrecio actual: {current_price:.5f}")
            print(f"Fase actual: {current_phase}")
            print(f"Prediccion: {prediction.upper()}")
            print(summary)
            
            signal = prediction
            
            if signal != 'none':
                print(f"\nEjecutando operacion {signal.upper()}...")
                
                result_trade = await execute_trade(signal, asset, amount, duration)
                
                if result_trade["success"]:
                    last_trade_time = current_time
                    TRADING_CONFIG["trades"] += 1
                    
                    new_balance = await client.get_balance()
                    profit = new_balance - TRADING_CONFIG["balance"]
                    
                    if profit > 0:
                        TRADING_CONFIG["wins"] += 1
                        TRADING_CONFIG["profit"] += profit
                        print(f"✅ Operacion GANADORA! +${profit:.2f}")
                    else:
                        TRADING_CONFIG["losses"] += 1
                        TRADING_CONFIG["profit"] += profit
                        print(f"❌ Operacion PERDEDORA! ${profit:.2f}")
                    
                    TRADING_CONFIG["balance"] = new_balance
                else:
                    print("❌ Error en la operacion")
            
            print(f"\nEstadisticas:")
            print(f"  Operaciones: {TRADING_CONFIG['trades']}")
            print(f"  Ganadas: {TRADING_CONFIG['wins']}")
            print(f"  Perdidas: {TRADING_CONFIG['losses']}")
            print(f"  Balance: ${TRADING_CONFIG['balance']:.2f}")
            print("-" * 50)
            
            await asyncio.sleep(period)
            
    except KeyboardInterrupt:
        print("\n\nEstrategia detenida por el usuario")
    except Exception as e:
        print(f"\nError en la estrategia: {e}")
    finally:
        await client.disconnect()
        print("\nDesconectado")


async def main():
    await run_strategy()


if __name__ == "__main__":
    asyncio.run(main())
