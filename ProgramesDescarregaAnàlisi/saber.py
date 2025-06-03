import platform
import psutil

print("Sistema:", platform.system(), platform.release())
print("Processador:", platform.processor())
print("CPU físics:", psutil.cpu_count(logical=False))
print("CPU totals (lògics):", psutil.cpu_count(logical=True))
print("RAM disponible (GB):", round(psutil.virtual_memory().total / 1e9, 2))

# Després de processar cada carpeta:
with open("estat.txt", "w") as f:
    f.write(carpeta)