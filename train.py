from database import init_db, get_matches
from model import train_model


print("========================================")
print("🎾 TENNIS EDGE PRO")
print("========================================")
print()
print("📊 Iniciando base de datos...")

init_db()

print("📥 Cargando partidos...")

df = get_matches()

print(f"✅ Partidos cargados: {len(df)}")
print()
print("🤖 ENTRENANDO MODELO...")
print("⏳ Este proceso puede tardar varios minutos.")
print()


resultado = train_model(df)


print()
print("========================================")
print("🏆 ENTRENAMIENTO TERMINADO")
print("========================================")
print(resultado)
print()