class GlobalState:
    """
    Holds global state variables, meaning variables not tied to an individual game instance
    """
    __stopped: bool = False
    __halted: bool = False

    def set_stopped(self, stopped: bool) -> None:
        self.__stopped = stopped

    def stopped(self) -> bool:
        return self.__stopped

    def set_halted(self, halted: bool) -> None:
        self.__halted = halted

    def halted(self) -> bool:
        return self.__halted
