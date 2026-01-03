import os


class Environment:
    def __init__(self) -> None:
        self.api_key = os.getenv("API_KEY", "").strip()
        self.ir_device = os.getenv("IR_DEVICE", "/dev/lirc0").strip()
        self.data_folder = os.getenv("DATA_DIR", "/data").strip()
        self.learn_timeout = int(os.getenv("LEARN_TIMEOUT_S_DEFAULT", "600"))
        