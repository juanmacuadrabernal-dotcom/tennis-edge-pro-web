from database import init_db, get_matches
from updater import update_database
from model import train_model


print("===================================")
print("ACTUALIZANDO DATOS DE TENIS")
print("===================================")

init_db()

resultado_actualizacion = update_database()

print(resultado_actualizacion)

print()


# Intentamos obtener el número de partidos nuevos
partidos_nuevos = 0

try:
    texto = str(resultado_actualizacion)

    if "Partidos nuevos añadidos:" in texto:

        parte = texto.split("Partidos nuevos añadidos:")[1]

        partidos_nuevos = int(
            parte.strip().split(".")[0]
        )

except Exception as e:

    print("⚠️ No se pudo detectar automáticamente el número de partidos nuevos.")
    print("Por seguridad, no se entrenará el modelo.")
    print(e)


# Solo entrenamos si hay nuevos partidos
if partidos_nuevos > 0:

    print("===================================")
    print("SE HAN ENCONTRADO PARTIDOS NUEVOS")
    print(f"PARTIDOS NUEVOS: {partidos_nuevos}")
    print("===================================")

    print()
    print("🧠 ENTRENANDO EL MODELO...")
    print("⏳ Este proceso puede tardar varios minutos.")
    print()

    datos = get_matches()

    resultado_modelo = train_model(datos)

    print()
    print(resultado_modelo)

else:

    print("===================================")
    print("NO HAY PARTIDOS NUEVOS")
    print("EL MODELO YA ESTÁ ACTUALIZADO")
    print("NO ES NECESARIO ENTRENAR")
    print("===================================")


print()
print("===================================")
print("PROCESO TERMINADO")
print("===================================")