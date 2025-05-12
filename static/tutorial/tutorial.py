import sys       # Para impresión sin salto de línea
import time      # Para medir y controlar los tiempos
import random    # Para elegir colores y símbolos al azar

# Lista de colores ANSI para la terminal
# los colores solo son compatibles copn algunas terminales
colores = [
    '\033[1;91m',  # Rojo claro
    '\033[1;92m',  # Verde claro
    '\033[1;93m',  # Amarillo claro
    '\033[1;94m',  # Azul claro
    '\033[1;95m',  # Magenta claro
    '\033[1;96m',  # Cian claro
    '\033[1;97m'   # Blanco brillante
]

# Código para reiniciar el color deespues de cada linea
reiniciar_color = '\033[0m'

# Símbolos decorativos musicales
simbolos_musicales = ['♬', '♪', '♫', '𝄞']

# Letra y tiempos en segundos desde el inicio
letra_con_tiempos = [
    (0.0,   "HOLA"),
    (2.0,   "SIGUEME"),
    (4.0,   "SE IRA ESCRIBIENDO"),
    (7.0,   "LETRA POR LETRA")
]

# Función que imprime las líneas sincronizadas
def imprimir_letra_sincronizada():
    
    tiempo_inicio = time.time()  # Marca el inicio 

    for indice, (tiempo_objetivo, linea) in enumerate(letra_con_tiempos):
        # Espera hasta que se cumpla el tiempo para esta línea
        while time.time() - tiempo_inicio < tiempo_objetivo:
            time.sleep(0.01)

        # Selección de color y símbolo decorativo
        color = colores[indice % len(colores)]
        simbolo = random.choice(simbolos_musicales)

        # Imprime la línea con efecto de máquina de escribir
        print(color, end='')
        for caracter in linea:
            print(caracter, end='')
            sys.stdout.flush()
            time.sleep(0.04)
        print(f" {simbolo}{reiniciar_color}")

# Ejecutar función directamente sin esperar input
imprimir_letra_sincronizada()
