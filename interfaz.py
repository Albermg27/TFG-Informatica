import tkinter as tk
from tkinter import scrolledtext
from sistema_estatico import ejecutar_sistema_estatico

def ejecutar():
    output_text.delete(1.0, tk.END)
    output_text.insert(tk.END, "Ejecutando sistema...\n\n")
    ventana.update()

    resultado = ejecutar_sistema_estatico()
    output_text.insert(tk.END, resultado)

ventana = tk.Tk()
ventana.title("Planificador de Cuadrillas")
ventana.geometry("700x500")

titulo = tk.Label(
    ventana,
    text="Sistema de planificación - Modo Estático",
    font=("Arial", 16, "bold")
)
titulo.pack(pady=10)

btn_ejecutar = tk.Button(
    ventana,
    text="Ejecutar sistema estático",
    font=("Arial", 12),
    bg="#4CAF50",
    fg="white",
    command=ejecutar
)
btn_ejecutar.pack(pady=10)

output_text = scrolledtext.ScrolledText(
    ventana,
    width=80,
    height=20,
    font=("Consolas", 10)
)
output_text.pack(pady=10)

btn_salir = tk.Button(
    ventana,
    text="Salir",
    command=ventana.quit
)
btn_salir.pack(pady=5)

ventana.mainloop()