"""Allocation and optimization algorithms for capacity-constrained matching."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.algorithms.base import AlgorithmOutput, IAllocator


@dataclass(slots=True)
class AllocationInput:
    students: pd.DataFrame
    courses: pd.DataFrame
    preferences: pd.DataFrame


class BaseAllocator(IAllocator):
    def __init__(self, name: str, parameters: dict[str, Any] | None = None) -> None:
        super().__init__(name=name, task_type="allocation", parameters=parameters)
        self.last_assignments: list[dict[str, Any]] = []

    def fit(self, X: Any, y: Any | None = None) -> "BaseAllocator":
        return self

    def predict(self, X: Any) -> AlgorithmOutput:
        if not isinstance(X, AllocationInput):
            raise TypeError("Allocation models expect AllocationInput in predict().")
        return self.allocate(X.students, X.courses, X.preferences)

    def recommend(self, X: Any, top_k: int = 5) -> AlgorithmOutput:
        return self.predict(X)

    def score(self, X: Any, y: Any | None = None) -> float:
        if not self.last_assignments:
            return 0.0
        assigned = sum(1 for a in self.last_assignments if a["course_id"] is not None)
        return float(assigned / max(len(self.last_assignments), 1))

    def explain(self, X: Any | None = None) -> str:
        if not self.last_assignments:
            return f"{self.name} not run yet."
        assigned = sum(1 for a in self.last_assignments if a["course_id"] is not None)
        return f"{self.name} assigned {assigned}/{len(self.last_assignments)} students."

    def _prepare(self, students: pd.DataFrame, courses: pd.DataFrame, preferences: pd.DataFrame) -> tuple[list[int], dict[int, int], dict[int, list[tuple[int, int]]]]:
        students_df = students.copy()
        courses_df = courses.copy()
        prefs_df = preferences.copy()

        students_df["student_id"] = pd.to_numeric(students_df["student_id"], errors="coerce").astype("Int64")
        courses_df["course_id"] = pd.to_numeric(courses_df["course_id"], errors="coerce").astype("Int64")
        courses_df["capacity"] = pd.to_numeric(courses_df.get("capacity", 0), errors="coerce").fillna(0).astype(int)

        prefs_df["student_id"] = pd.to_numeric(prefs_df["student_id"], errors="coerce").astype("Int64")
        prefs_df["course_id"] = pd.to_numeric(prefs_df["course_id"], errors="coerce").astype("Int64")
        prefs_df["rank"] = pd.to_numeric(prefs_df.get("rank", 999), errors="coerce").fillna(999).astype(int)

        student_ids = students_df["student_id"].dropna().astype(int).tolist()
        capacities = {
            int(row["course_id"]): max(0, int(row["capacity"]))
            for _, row in courses_df[["course_id", "capacity"]].dropna().iterrows()
        }
        preference_map: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for _, row in prefs_df[["student_id", "course_id", "rank"]].dropna().iterrows():
            preference_map[int(row["student_id"])].append((int(row["course_id"]), int(row["rank"])))
        for sid in preference_map:
            preference_map[sid].sort(key=lambda t: t[1])
        return student_ids, capacities, preference_map

    def _format_assignments(self, student_ids: list[int], assigned_course: dict[int, int | None], received_rank: dict[int, int | None]) -> list[dict[str, Any]]:
        rows = []
        for sid in student_ids:
            rows.append(
                {
                    "student_id": sid,
                    "course_id": assigned_course.get(sid),
                    "rank_received": received_rank.get(sid),
                    "allocated": assigned_course.get(sid) is not None,
                    "algorithm": self.name,
                }
            )
        return rows

    def _output(self, started: float, assignments: list[dict[str, Any]], explanation: str, artifacts: dict[str, Any] | None = None) -> AlgorithmOutput:
        self.last_assignments = assignments
        confidence = float(sum(1 for a in assignments if a["allocated"]) / max(len(assignments), 1))
        return self._build_output(
            started,
            assignments=assignments,
            confidence=confidence,
            explanation=explanation,
            artifacts=artifacts or {},
        )


class RandomAllocator(BaseAllocator):
    def __init__(self, random_seed: int = 42) -> None:
        super().__init__(name="RandomAllocation", parameters={"random_seed": random_seed})
        self.rng = np.random.default_rng(random_seed)

    def allocate(self, students: pd.DataFrame, courses: pd.DataFrame, preferences: pd.DataFrame) -> AlgorithmOutput:
        started = self._start_timer()
        student_ids, capacities, pref_map = self._prepare(students, courses, preferences)
        assigned: dict[int, int | None] = {sid: None for sid in student_ids}
        rank_received: dict[int, int | None] = {sid: None for sid in student_ids}

        order = student_ids[:]
        self.rng.shuffle(order)
        for sid in order:
            options = [(cid, r) for cid, r in pref_map.get(sid, []) if capacities.get(cid, 0) > 0]
            if not options:
                continue
            cid, rank = options[self.rng.integers(0, len(options))]
            assigned[sid] = cid
            rank_received[sid] = rank
            capacities[cid] -= 1

        assignments = self._format_assignments(student_ids, assigned, rank_received)
        return self._output(started, assignments, explanation="Random capacity-constrained allocation baseline.")


class FCFSAllocator(BaseAllocator):
    def __init__(self) -> None:
        super().__init__(name="FirstComeFirstServed")

    def allocate(self, students: pd.DataFrame, courses: pd.DataFrame, preferences: pd.DataFrame) -> AlgorithmOutput:
        started = self._start_timer()
        student_ids, capacities, pref_map = self._prepare(students, courses, preferences)
        assigned = {sid: None for sid in student_ids}
        rank_received = {sid: None for sid in student_ids}

        for sid in student_ids:
            for cid, rank in pref_map.get(sid, []):
                if capacities.get(cid, 0) > 0:
                    assigned[sid] = cid
                    rank_received[sid] = rank
                    capacities[cid] -= 1
                    break

        assignments = self._format_assignments(student_ids, assigned, rank_received)
        return self._output(started, assignments, explanation="FCFS allocation in student iteration order.")


class GreedyAllocator(BaseAllocator):
    def __init__(self) -> None:
        super().__init__(name="GreedyAllocation")

    def allocate(self, students: pd.DataFrame, courses: pd.DataFrame, preferences: pd.DataFrame) -> AlgorithmOutput:
        started = self._start_timer()
        student_ids, capacities, pref_map = self._prepare(students, courses, preferences)
        assigned = {sid: None for sid in student_ids}
        rank_received = {sid: None for sid in student_ids}

        for sid in student_ids:
            candidates = [(cid, rank, 1.0 / max(rank, 1)) for cid, rank in pref_map.get(sid, []) if capacities.get(cid, 0) > 0]
            if not candidates:
                continue
            cid, rank, _ = max(candidates, key=lambda t: t[2])
            assigned[sid] = cid
            rank_received[sid] = rank
            capacities[cid] -= 1

        assignments = self._format_assignments(student_ids, assigned, rank_received)
        return self._output(started, assignments, explanation="Greedy utility maximization using inverse rank utility.")


class MinimumRegretAllocator(BaseAllocator):
    def __init__(self) -> None:
        super().__init__(name="MinimumRegretAllocation")

    def allocate(self, students: pd.DataFrame, courses: pd.DataFrame, preferences: pd.DataFrame) -> AlgorithmOutput:
        started = self._start_timer()
        student_ids, capacities, pref_map = self._prepare(students, courses, preferences)
        assigned = {sid: None for sid in student_ids}
        rank_received = {sid: None for sid in student_ids}

        all_pairs = []
        for sid, pref_list in pref_map.items():
            for cid, rank in pref_list:
                all_pairs.append((rank, sid, cid))
        all_pairs.sort(key=lambda t: t[0])  # lower rank means lower regret

        for rank, sid, cid in all_pairs:
            if assigned[sid] is not None:
                continue
            if capacities.get(cid, 0) <= 0:
                continue
            assigned[sid] = cid
            rank_received[sid] = rank
            capacities[cid] -= 1

        assignments = self._format_assignments(student_ids, assigned, rank_received)
        mean_regret = float(np.mean([r for r in rank_received.values() if r is not None])) if any(rank_received.values()) else 0.0
        return self._output(
            started,
            assignments,
            explanation=f"Minimum-regret assignment via global low-rank matching (mean rank={mean_regret:.2f}).",
            artifacts={"mean_rank_regret": mean_regret},
        )


class GaleShapleyAllocator(BaseAllocator):
    def __init__(self) -> None:
        super().__init__(name="GaleShapley")

    def allocate(self, students: pd.DataFrame, courses: pd.DataFrame, preferences: pd.DataFrame) -> AlgorithmOutput:
        started = self._start_timer()
        student_ids, capacities, pref_map = self._prepare(students, courses, preferences)
        gpa_map = (
            students.set_index("student_id")["gpa"].to_dict() if "gpa" in students.columns else {sid: 0.0 for sid in student_ids}
        )

        unmatched = set(student_ids)
        proposal_idx = {sid: 0 for sid in student_ids}
        course_matches: dict[int, list[int]] = {cid: [] for cid in capacities.keys()}
        assigned_course: dict[int, int | None] = {sid: None for sid in student_ids}
        rank_received: dict[int, int | None] = {sid: None for sid in student_ids}

        def student_priority(student_id: int) -> float:
            value = gpa_map.get(student_id)
            if value is None or (isinstance(value, float) and np.isnan(value)):
                return 0.0
            return float(value)

        while unmatched:
            sid = unmatched.pop()
            prefs = pref_map.get(sid, [])
            if proposal_idx[sid] >= len(prefs):
                continue
            cid, rank = prefs[proposal_idx[sid]]
            proposal_idx[sid] += 1
            current = course_matches.setdefault(cid, [])
            cap = capacities.get(cid, 0)
            if cap <= 0:
                unmatched.add(sid)
                continue

            if len(current) < cap:
                current.append(sid)
                assigned_course[sid] = cid
                rank_received[sid] = rank
            else:
                worst_current = min(current, key=student_priority)
                if student_priority(sid) > student_priority(worst_current):
                    current.remove(worst_current)
                    assigned_course[worst_current] = None
                    rank_received[worst_current] = None
                    if proposal_idx[worst_current] < len(pref_map.get(worst_current, [])):
                        unmatched.add(worst_current)

                    current.append(sid)
                    assigned_course[sid] = cid
                    rank_received[sid] = rank
                else:
                    if proposal_idx[sid] < len(prefs):
                        unmatched.add(sid)

        assignments = self._format_assignments(student_ids, assigned_course, rank_received)
        return self._output(
            started,
            assignments,
            explanation="Gale-Shapley many-to-one stable matching using student GPA as course-side priority.",
        )

