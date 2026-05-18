import tkinter as tk

from gui import theme


class AppContext:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.menu: tk.Frame | None = None
        self.content: tk.Frame | None = None
        self.filtro_tipo = tk.StringVar(value="TODAS")
        self._boton_activo: tk.Frame | None = None
        self._botones_menu: dict[str, tk.Frame] = {}

    def set_frames(self, menu: tk.Frame, content: tk.Frame) -> None:
        self.menu = menu
        self.content = content

    def limpiar(self) -> None:
        for w in self.content.winfo_children():
            w.destroy()

    def marcar_nav_activo(self, clave: str) -> None:
        if self._boton_activo is not None:
            self._restaurar_nav(self._boton_activo)
        frame = self._botones_menu.get(clave)
        if frame is None:
            return
        self._boton_activo = frame
        self._aplicar_nav(frame, activo=True)

    def registrar_nav(self, clave: str, frame: tk.Frame) -> None:
        self._botones_menu[clave] = frame

    @staticmethod
    def _aplicar_nav(frame: tk.Frame, activo: bool) -> None:
        bg = theme.PRIMARY if activo else theme.BG_MENU
        fg = "white" if activo else "#cbd5e1"
        frame.configure(bg=bg)
        for child in frame.winfo_children():
            child.configure(bg=bg)
            if isinstance(child, tk.Label):
                child.configure(bg=bg, fg=fg)
            else:
                for sub in child.winfo_children():
                    if isinstance(sub, tk.Label):
                        sub.configure(bg=bg, fg=fg)

    @classmethod
    def _restaurar_nav(cls, frame: tk.Frame) -> None:
        cls._aplicar_nav(frame, activo=False)
