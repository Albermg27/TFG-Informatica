from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulacion.estrategias_asignacion import etiqueta_estrategia
from simulacion.metricas import ejecutar_bateria_casos_prueba

CAMPOS = (
    "resoluciones_asignacion",
    "tiempo_asignacion_total_s",
    "tiempo_asignacion_medio_ms",
)


def main() -> None:
    total_pasos = 0

    def on_progreso(ejecutadas: int, total: int, instancia_id: int, rep: int) -> None:
        nonlocal total_pasos
        if total != total_pasos:
            total_pasos = total
            print(f"Total pasos: {total}", flush=True)
        if ejecutadas % 20 == 0 or ejecutadas == total:
            print(
                f"Progreso: {ejecutadas}/{total} (inst {instancia_id}, rep {rep})",
                flush=True,
            )

    datos = ejecutar_bateria_casos_prueba(on_progreso=on_progreso)
    medias = datos["media_global_por_estrategia"]
    out: dict = {}
    for estrategia, bloque in medias.items():
        out[estrategia] = {
            "etiqueta": etiqueta_estrategia(estrategia),
            "estatico": {k: bloque["estatico"].get(k) for k in CAMPOS},
            "dinamico": {k: bloque["dinamico"].get(k) for k in CAMPOS},
        }

    ruta = ROOT / "benchmark_tiempos_resultados.json"
    ruta.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("DONE", flush=True)
    for estrategia, valores in out.items():
        est = valores["estatico"]
        dyn = valores["dinamico"]
        print(
            f"{valores['etiqueta']}: "
            f"estatico medio {est['tiempo_asignacion_medio_ms']} ms "
            f"({est['resoluciones_asignacion']} res/jornada), "
            f"dinamico medio {dyn['tiempo_asignacion_medio_ms']} ms "
            f"({dyn['resoluciones_asignacion']} res/jornada, "
            f"total {dyn['tiempo_asignacion_total_s']} s/jornada)",
            flush=True,
        )


if __name__ == "__main__":
    main()
