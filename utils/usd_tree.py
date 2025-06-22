from copy import deepcopy
from typing import Optional

from pxr import Sdf, Usd


class PrimNode:
    def __init__(
        self,
        stage: Usd.Stage,
        prim: Usd.Prim,
        type_name: str,
        children: Optional[list] = None,
    ) -> None:
        self.stage: Usd.Stage = stage
        self.prim: Usd.Prim = prim
        # store type name for easy look-up during debugging
        self.type_name: str = type_name
        self.children: list[PrimNode] = children or []

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        return f"{self.type_name}: {repr(self.prim.GetName())} ({len(self.children)} {'child' if len(self.children) == 1 else 'children'})"

    def __getstate__(self) -> dict:
        # Make class picklable
        state = self.__dict__.copy()
        state["stage"] = self.stage.GetRootLayer().realPath
        state["prim"] = self.prim.GetPrimPath().pathString
        return state

    def __setstate__(self, state) -> None:
        # Recreate after pickling
        self.__dict__.update(state)
        self.stage = Usd.Stage.Open(self.stage)  # type: ignore
        self.prim = self.stage.GetPrimAtPath(Sdf.Path(self.prim))

    def add_child(self, child):
        if type(child) is not PrimNode:
            raise TypeError(f"Children must be of type 'PrimNode'!")
        self.children.append(child)

    def copy(self):
        return deepcopy(self)


def parse_usd(stage: Usd.Stage) -> PrimNode:
    """Recursively traverses the stage and adds all children to an n-ary tree.

    Args:
        stage (Usd.Stage): Stage which holds our assets

    Returns:
        PrimNode: _description_
    """

    def parse_prim(prim: Usd.Prim) -> PrimNode:
        node = PrimNode(stage=stage, prim=prim, type_name=prim.GetTypeName())
        for child in prim.GetAllChildren():
            node.add_child(parse_prim(child))
        return node

    return parse_prim(stage.GetDefaultPrim())
