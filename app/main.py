#!/usr/bin/env python3
import subprocess

def main() -> None:
    # irw liefert erst Events, wenn eine Remote-Konfig vorhanden ist.
    # Für reines "kommt irgendwas?" nimm mode2 (siehe unten).
    proc = subprocess.Popen(["irw"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    assert proc.stdout is not None
    print("Warte auf IR-Events via irw ... (Ctrl+C zum Beenden)")
    for line in proc.stdout:
        line = line.strip()
        if line:
            print(line)

if __name__ == "__main__":
    main()