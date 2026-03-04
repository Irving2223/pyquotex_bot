import asyncio
import random
from pyquotex.stable_api import Quotex
from pyquotex.config import credentials

CONFIG = {
    "amount": 10,
    "duration": 60,
    "asset": "EURUSD_otc",
    "use_demo": True,
    "max_trades": 50,
    "debug": False,
}

state = {
    "balance": 0,
    "profit": 0,
    "trades": 0,
    "wins": 0,
    "losses": 0,
}


def log(msg):
    if CONFIG["debug"]:
        print(f"[DEBUG] {msg}")


async def setup_client():
    email, password = credentials()
    client = Quotex(email=email, password=password, lang="pt")
    return client


async def check_trade_result(client, buy_info, direction):
    open_price = buy_info.get('openPrice')
    asset = buy_info.get('asset')
    
    for _ in range(90):
        await asyncio.sleep(1)
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


async def strange_strategy(update_callback=None):
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
    await _call("  STRANGE STRATEGY - TRADING ALEATORIO")
    await _call("=" * 60)
    await _call(f"  Activo:      {CONFIG['asset']}")
    await _call(f"  Monto:       ${CONFIG['amount']}")
    await _call(f"  Duración:    {CONFIG['duration']}s")
    await _call(f"  Max Trades:  {CONFIG['max_trades']}")
    await _call("=" * 60)
    await _call("  ⚠️ ADVERTENCIA: Estrategia aleatoria")
    await _call("  ⚠️ Solo para pruebas en demo")
    await _call("=" * 60)
    
    client = await setup_client()
    check_connect, message = await client.connect()
    
    if not check_connect:
        await _call(f"❌ Error de conexión: {message}")
        return False
    
    await _call("✅ Conectado exitosamente")
    
    await client.change_account("PRACTICE" if CONFIG["use_demo"] else "REAL")
    state["balance"] = await client.get_balance()
    account_type = "DEMO" if CONFIG["use_demo"] else "REAL"
    await _call(f"💰 Balance {account_type}: ${state['balance']:.2f}")
    
    state["trades"] = 0
    state["wins"] = 0
    state["losses"] = 0
    state["profit"] = 0
    
    try:
        while state["trades"] < CONFIG["max_trades"]:
            if not await client.check_connect():
                await _call("🔄 Reconectando...")
                await client.connect()
                await asyncio.sleep(5)
                continue
            
            direction = random.choice(["call", "put"])
            emojis = {"call": "📈", "put": "📉"}
            
            await _call(f"\n🔄 Operación #{state['trades'] + 1}")
            await _call(f"   Decisión ALEATORIA: {emojis[direction]} {direction.upper()}")
            await _call(f"   Monto: ${CONFIG['amount']}")
            
            status, buy_info = await client.buy(
                CONFIG["amount"],
                CONFIG["asset"],
                direction,
                CONFIG["duration"]
            )
            
            if not status:
                await _call("   ❌ Error al ejecutar operación")
                await asyncio.sleep(5)
                continue
            
            await _call(f"   ⏳ Esperando resultado ({CONFIG['duration']}s)...")
            
            result = await check_trade_result(client, buy_info, direction)
            
            state["trades"] += 1
            
            if result == "WIN":
                state["wins"] += 1
                profit = buy_info.get('profit', CONFIG["amount"] * 0.8)
                state["profit"] += profit
                await _call(f"   ✅ WIN +${profit:.2f}")
            elif result == "LOSS":
                state["losses"] += 1
                state["profit"] -= CONFIG["amount"]
                await _call(f"   ❌ LOSS -${CONFIG['amount']:.2f}")
            elif result == "DOJI":
                await _call(f"   ➡️ DOJI (Reembolso)")
            else:
                await _call(f"   ❓ Resultado desconocido: {result}")
            
            winrate = state["wins"] / state["trades"] * 100
            await _call(f"   📊 Stats: {state['wins']}W/{state['losses']}L | Winrate: {winrate:.1f}%")
            await _call(f"   💵 Profit acumulado: ${state['profit']:.2f}")
            
            await _call(f"\n   ⏰ Esperando 60s para siguiente operación...")
            await asyncio.sleep(60)
    
    except asyncio.CancelledError:
        await _call("\n⏹️ Bot detenido")
    except Exception as e:
        await _call(f"\n❌ Error: {e}")
    finally:
        await client.close()
        
        await _call("\n" + "=" * 60)
        await _call("  RESUMEN FINAL")
        await _call("=" * 60)
        await _call(f"  Total operaciones: {state['trades']}")
        await _call(f"  Wins: {state['wins']} | Losses: {state['losses']}")
        await _call(f"  Winrate: {state['wins']/max(1, state['trades'])*100:.1f}%")
        await _call(f"  Profit total: ${state['profit']:.2f}")
        await _call("=" * 60)


async def main():
    await strange_strategy()


if __name__ == "__main__":
    asyncio.run(main())
