import sys, tkinter as tk
r = tk.Tk()
r.title('Nástrojový list')
tk.Label(r, text='Nástrojový list' + " (fiktívna aplikácia, v " + '2026.11.19-1' + ")", font=("Segoe UI", 12)).pack(padx=30, pady=15)
tk.Label(r, text="Argumenty:\n" + "\n".join(sys.argv[1:]) if len(sys.argv) > 1 else "Bez argumentov").pack(padx=30, pady=10)
r.mainloop()
