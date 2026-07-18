import { useSearchParams } from "react-router-dom";

export interface SelectedSystem {
  id: number;
  name: string;
}

export interface SelectionState {
  powerName: string | null;
  centerSystem: SelectedSystem | null;
  setPower: (name: string | null) => void;
  setCenter: (system: SelectedSystem | null) => void;
}

export function useSelectionState(): SelectionState {
  const [params, setParams] = useSearchParams();

  const powerName = params.get("power");
  const centerId = params.get("center_id");
  const centerName = params.get("center_name");
  const centerSystem: SelectedSystem | null =
    centerId && centerName ? { id: Number(centerId), name: centerName } : null;

  function setPower(name: string | null) {
    setParams((prev) => {
      const next = new URLSearchParams(prev);
      if (name) next.set("power", name);
      else next.delete("power");
      return next;
    });
  }

  function setCenter(system: SelectedSystem | null) {
    setParams((prev) => {
      const next = new URLSearchParams(prev);
      if (system) {
        next.set("center_id", String(system.id));
        next.set("center_name", system.name);
      } else {
        next.delete("center_id");
        next.delete("center_name");
      }
      return next;
    });
  }

  return { powerName, centerSystem, setPower, setCenter };
}
