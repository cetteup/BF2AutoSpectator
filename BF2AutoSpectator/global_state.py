class GlobalState:
    """
    Holds global state variables, meaning variables not tied to an individual game instance
    """
    __stopped: bool = False
    __halted: bool = False

    def stopped(self) -> bool:
        return self.__stopped

    def stop(self) -> None:
        self.__stopped = True

    def resume(self) -> None:
        self.__stopped = False

    def halted(self) -> bool:
        return self.__halted

    def halt(self) -> None:
        self.__halted = True

    def release(self) -> None:
        self.__halted = False
