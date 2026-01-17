from typing import Dict, Any

from electronics.ir_ctl_engine import IrCtlEngine
from electronics.ir_sender_service import IrSenderService
from electronics.ir_signal_parser import IrSignalParser


class LocalTransport:
    def __init__(self, engine: IrCtlEngine, parser: IrSignalParser) -> None:
        self._engine = engine
        self._sender = IrSenderService(engine=engine, parser=parser)

    def learn_capture(self, timeout_ms: int) -> Dict[str, Any]:
        raw, stdout, stderr = self._engine.receive_one_message(timeout_ms=timeout_ms)
        return {"raw": raw, "stdout": stdout, "stderr": stderr}

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._sender.send(payload)
