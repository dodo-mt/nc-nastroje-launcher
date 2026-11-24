import sys, tkinter as tk
r = tk.Tk()
r.title('Triedič NC')
tk.Label(r, text='Triedič NC' + " (fiktívna aplikácia, v " + '2026.11.19-2' + ")", font=("Segoe UI", 12)).pack(padx=30, pady=15)
tk.Label(r, text="Argumenty:\n" + "\n".join(sys.argv[1:]) if len(sys.argv) > 1 else "Bez argumentov").pack(padx=30, pady=10)
r.mainloop()
