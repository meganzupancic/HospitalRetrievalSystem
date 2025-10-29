import tkinter as tk

root = tk.Tk()
root.title("Test GUI")
label = tk.Label(root, text="If you see this, Tkinter works!")
label.pack(padx=20, pady=20)
root.mainloop()
