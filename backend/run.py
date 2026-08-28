#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Entry Point do Backend.
Inicia o servidor uvicorn com configuração via argumentos de linha de comando.
"""

import argparse
import sys

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Revsist Backend Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host do servidor")
    parser.add_argument("--port", type=int, default=8000, help="Porta do servidor")
    parser.add_argument("--reload", action="store_true", help="Hot-reload em desenvolvimento")
    parser.add_argument("--debug", action="store_true", help="Modo debug")

    args = parser.parse_args()

    # Configurar variáveis de ambiente antes do import do app
    if args.debug:
        import os
        os.environ["RSAC_DEBUG"] = "true"

    if args.reload:
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=True,
            log_level="debug" if args.debug else "info",
        )
    else:
        from app.main import app
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=False,
            log_level="debug" if args.debug else "info",
        )


if __name__ == "__main__":
    main()
