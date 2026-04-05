import os
import sys

if __name__ == "__main__":
    profile = os.getenv("ENV_FOR_DYNACONF", "").lower()

    if profile == "send":
        from src.send.main import main
        main()
    elif profile == "receive":
        from src.receive.main import main
        main()
    else:
        print(f"CRITICAL: Unknown profile '{profile}'. Exiting.")
        sys.exit(1)