from typing import Any, Callable, Dict

from ianchor import Tasktype


class Sampler:
    """
    Abstract Sampler that is used as a factory for its
    subclasses. Use create(Tasktype) to initialise sub-
    classes for each task.
    """

    subclasses = {}

    def __init_subclass__(cls, **kwargs):
        """
        Registers every subclass in the subclass-dict.
        """
        super().__init_subclass__(**kwargs)
        cls.subclasses[cls.type] = cls

    @classmethod
    def create(
        cls, type: Tasktype, input: Any, predict_fn: Callable, task_specific: Dict, **kwargs
    ):
        """
        Creates subclass depending on typ.

        Args:
            typ: Tasktype
        Returns:
            Subclass that is used for the given Tasktype.
        """
        if type not in cls.subclasses:
            raise ValueError("Bad message type {}".format(type))

        return cls.subclasses[type](
            input, predict_fn, **task_specific
        )  # every sampler needs input and predict function
