import os
import sys
from pathlib import Path

def main():
    print("🚀 Iniciando BaulSIG...")
    from gui.login import iniciar_login
    iniciar_login()

if __name__ == "__main__":
    main()