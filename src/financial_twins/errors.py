class ClientInputError(ValueError):
    """The caller supplied an invalid simulation request."""


class SimulationConfigurationError(RuntimeError):
    """The service is not configured for the requested simulation engine."""


class FoundryProviderError(RuntimeError):
    """Microsoft Foundry could not complete a model invocation."""


class FoundryResponseError(RuntimeError):
    """Microsoft Foundry returned output that violated the response contract."""


class PersistenceError(RuntimeError):
    """The simulation result could not be persisted."""
