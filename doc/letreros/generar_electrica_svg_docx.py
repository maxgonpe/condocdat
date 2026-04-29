#!/usr/bin/env python3
"""Wrapper: usa el generador unificado con prefijo electrica."""
import sys
from pathlib import Path

# Permitir ejecutar desde cualquier cwd
sys.path.insert(0, str(Path(__file__).resolve().parent))

from generar_letrero_2_profesionales_docx import main as main_unificado  # noqa: E402


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.argv = [sys.argv[0], "--prefijo", "electrica"]
    elif args[0] in ("-h", "--help"):
        pass
    elif "--prefijo" not in sys.argv:
        sys.argv = [sys.argv[0], "--prefijo", "electrica"] + args
    main_unificado()


if __name__ == "__main__":
    main()
